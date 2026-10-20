"""Camera registration and one-time device token rotation."""
from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_role, require_store_access
from ..db import models
from ..db.session import get_session

router = APIRouter(prefix="/stores/{store_id}/cameras", tags=["cameras"])


class CameraCreate(BaseModel):
    name: str
    location: str | None = None
    shelf_id: str | None = None


class CameraPatch(BaseModel):
    name: str | None = None
    location: str | None = None
    shelf_id: str | None = None
    status: str | None = None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _get_camera(store_id: str, camera_id: str, session: Session) -> models.Camera:
    camera = session.query(models.Camera).filter(models.Camera.id == camera_id,
                                                 models.Camera.store_id == store_id).first()
    if not camera:
        raise HTTPException(404, detail={"detail": "Camara no encontrada", "code": "NOT_FOUND"})
    return camera


def _public(camera: models.Camera) -> dict:
    return {"id": camera.id, "store_id": camera.store_id, "shelf_id": camera.shelf_id,
            "name": camera.name, "location": camera.location, "status": camera.status,
            "last_seen": camera.last_seen}


@router.post("", status_code=201)
def create_camera(store_id: str, payload: CameraCreate, session: Session = Depends(get_session),
                  user: models.User = Depends(require_role("super_admin", "store_admin"))):
    require_store_access(store_id, user)
    if not session.get(models.Store, store_id):
        raise HTTPException(404, detail={"detail": "Tienda no encontrada", "code": "NOT_FOUND"})
    if payload.shelf_id and not session.query(models.Shelf).filter(
            models.Shelf.id == payload.shelf_id, models.Shelf.store_id == store_id).first():
        raise HTTPException(404, detail={"detail": "Estante no encontrado", "code": "NOT_FOUND"})
    token = secrets.token_urlsafe(32)
    camera = models.Camera(store_id=store_id, token_hash=_token_hash(token), **payload.model_dump())
    session.add(camera)
    session.commit()
    session.refresh(camera)
    return {**_public(camera), "token": token}


@router.get("")
def list_cameras(store_id: str, session: Session = Depends(get_session),
                 user: models.User = Depends(get_current_user)):
    require_store_access(store_id, user)
    return [_public(camera) for camera in session.query(models.Camera).filter(
        models.Camera.store_id == store_id).all()]


@router.patch("/{camera_id}")
def update_camera(store_id: str, camera_id: str, payload: CameraPatch,
                  session: Session = Depends(get_session),
                  user: models.User = Depends(require_role("super_admin", "store_admin"))):
    require_store_access(store_id, user)
    camera = _get_camera(store_id, camera_id, session)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, key, value)
    session.commit()
    return _public(camera)


@router.post("/{camera_id}/rotate-token")
def rotate_token(store_id: str, camera_id: str, session: Session = Depends(get_session),
                 user: models.User = Depends(require_role("super_admin", "store_admin"))):
    require_store_access(store_id, user)
    camera = _get_camera(store_id, camera_id, session)
    token = secrets.token_urlsafe(32)
    camera.token_hash = _token_hash(token)
    session.commit()
    return {**_public(camera), "token": token}
