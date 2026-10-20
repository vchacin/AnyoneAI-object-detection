"""Store and initial store-admin endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_role, require_store_access
from ..core.security import hash_password
from ..db import models
from ..db.session import get_session

router = APIRouter(prefix="/stores", tags=["stores"])


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None
    admin_email: str | None = None
    admin_password: str | None = Field(default=None, min_length=8)


class StorePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    address: str | None = None
    status: str | None = None


class SettingsPatch(BaseModel):
    timezone: str | None = None
    opening_time: str | None = None
    closing_time: str | None = None
    peak_hours: list | None = None
    default_conf: float | None = Field(default=None, ge=0, le=1)
    alert_cooldown_minutes: int | None = Field(default=None, ge=0)


@router.post("", status_code=201)
def create_store(payload: StoreCreate, session: Session = Depends(get_session),
                 user: models.User = Depends(require_role("super_admin"))):
    store = models.Store(name=payload.name, address=payload.address)
    session.add(store)
    session.flush()
    if payload.admin_email and payload.admin_password:
        session.add(models.User(store_id=store.id, email=payload.admin_email.lower(),
                                 password_hash=hash_password(payload.admin_password), role="store_admin"))
    session.commit()
    session.refresh(store)
    return {"id": store.id, "name": store.name, "address": store.address, "status": store.status}


@router.get("")
def list_stores(session: Session = Depends(get_session),
                _: models.User = Depends(require_role("super_admin"))):
    return [{"id": s.id, "name": s.name, "address": s.address, "status": s.status} for s in session.query(models.Store).order_by(models.Store.created_at.desc()).all()]


@router.get("/{store_id}")
def get_store(store_id: str, session: Session = Depends(get_session), user: models.User = Depends(get_current_user)):
    require_store_access(store_id, user)
    store = session.get(models.Store, store_id)
    if not store:
        raise HTTPException(404, detail={"detail": "Tienda no encontrada", "code": "NOT_FOUND"})
    return {"id": store.id, "name": store.name, "address": store.address, "status": store.status}


@router.patch("/{store_id}")
def update_store(store_id: str, payload: StorePatch, session: Session = Depends(get_session),
                 _: models.User = Depends(require_role("super_admin"))):
    store = session.get(models.Store, store_id)
    if not store:
        raise HTTPException(404, detail={"detail": "Tienda no encontrada", "code": "NOT_FOUND"})
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, key, value)
    session.commit()
    return {"id": store.id, "name": store.name, "address": store.address, "status": store.status}


@router.get("/{store_id}/settings")
def get_settings(store_id: str, session: Session = Depends(get_session),
                 user: models.User = Depends(get_current_user)):
    require_store_access(store_id, user)
    if not session.get(models.Store, store_id):
        raise HTTPException(404, detail={"detail": "Tienda no encontrada", "code": "NOT_FOUND"})
    settings = session.get(models.StoreSetting, store_id)
    if not settings:
        settings = models.StoreSetting(store_id=store_id)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


@router.put("/{store_id}/settings")
def update_settings(store_id: str, payload: SettingsPatch, session: Session = Depends(get_session),
                    user: models.User = Depends(require_role("super_admin", "store_admin"))):
    require_store_access(store_id, user)
    if not session.get(models.Store, store_id):
        raise HTTPException(404, detail={"detail": "Tienda no encontrada", "code": "NOT_FOUND"})
    settings = session.get(models.StoreSetting, store_id)
    if not settings:
        settings = models.StoreSetting(store_id=store_id)
        session.add(settings)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    session.commit()
    session.refresh(settings)
    return settings
