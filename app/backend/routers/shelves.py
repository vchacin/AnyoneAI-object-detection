"""Shelf and zone management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_role, require_store_access
from ..db import models
from ..db.session import get_session

router = APIRouter(prefix="/stores/{store_id}/shelves", tags=["shelves"])


class ShelfCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    zone: str | None = None
    gap_threshold: int = Field(default=0, ge=0)


class ShelfPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    zone: str | None = None
    gap_threshold: int | None = Field(default=None, ge=0)


def _get_shelf(store_id: str, shelf_id: str, session: Session) -> models.Shelf:
    shelf = session.query(models.Shelf).filter(models.Shelf.id == shelf_id,
                                                models.Shelf.store_id == store_id).first()
    if not shelf:
        raise HTTPException(404, detail={"detail": "Estante no encontrada", "code": "NOT_FOUND"})
    return shelf


@router.post("", status_code=201)
def create_shelf(store_id: str, payload: ShelfCreate, session: Session = Depends(get_session),
                 user: models.User = Depends(require_role("super_admin", "store_admin"))):
    require_store_access(store_id, user)
    if not session.get(models.Store, store_id):
        raise HTTPException(404, detail={"detail": "Tienda no encontrada", "code": "NOT_FOUND"})
    shelf = models.Shelf(store_id=store_id, **payload.model_dump())
    session.add(shelf)
    session.commit()
    session.refresh(shelf)
    return shelf


@router.get("")
def list_shelves(store_id: str, session: Session = Depends(get_session),
                 user: models.User = Depends(get_current_user)):
    require_store_access(store_id, user)
    return session.query(models.Shelf).filter(models.Shelf.store_id == store_id).all()


@router.patch("/{shelf_id}")
def update_shelf(store_id: str, shelf_id: str, payload: ShelfPatch,
                 session: Session = Depends(get_session),
                 user: models.User = Depends(require_role("super_admin", "store_admin"))):
    require_store_access(store_id, user)
    shelf = _get_shelf(store_id, shelf_id, session)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(shelf, key, value)
    session.commit()
    session.refresh(shelf)
    return shelf
