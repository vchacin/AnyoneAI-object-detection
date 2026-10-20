"""Store user management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_role, require_store_access
from ..core.security import hash_password
from ..db import models
from ..db.session import get_session

router = APIRouter(prefix="/stores/{store_id}/users", tags=["users"])


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    role: str


class UserPatch(BaseModel):
    role: str | None = None
    password: str | None = Field(default=None, min_length=8)
    is_active: bool | None = None


ALLOWED_ROLES = {"store_admin", "employee", "viewer"}


def _public(user: models.User) -> dict:
    return {"id": user.id, "store_id": user.store_id, "email": user.email,
            "role": user.role, "is_active": user.is_active}


@router.post("", status_code=201)
def create_user(store_id: str, payload: UserCreate, session: Session = Depends(get_session),
                actor: models.User = Depends(require_role("super_admin", "store_admin"))):
    require_store_access(store_id, actor)
    if payload.role not in ALLOWED_ROLES or (
            actor.role == "store_admin" and payload.role == "store_admin"):
        raise HTTPException(422, detail={"detail": "Rol no permitido", "code": "INVALID_ROLE"})
    if session.query(models.User).filter(models.User.email == payload.email.lower()).first():
        raise HTTPException(409, detail={"detail": "El correo ya existe", "code": "EMAIL_EXISTS"})
    user = models.User(store_id=store_id, email=payload.email.lower(),
                       password_hash=hash_password(payload.password), role=payload.role)
    session.add(user)
    session.commit()
    session.refresh(user)
    return _public(user)


@router.get("")
def list_users(store_id: str, session: Session = Depends(get_session),
               actor: models.User = Depends(get_current_user)):
    require_store_access(store_id, actor)
    return [_public(user) for user in session.query(models.User).filter(
        models.User.store_id == store_id).all()]


@router.patch("/{user_id}")
def update_user(store_id: str, user_id: str, payload: UserPatch,
                session: Session = Depends(get_session),
                actor: models.User = Depends(require_role("super_admin", "store_admin"))):
    require_store_access(store_id, actor)
    user = session.query(models.User).filter(models.User.id == user_id,
                                             models.User.store_id == store_id).first()
    if not user:
        raise HTTPException(404, detail={"detail": "Usuario no encontrado", "code": "NOT_FOUND"})
    values = payload.model_dump(exclude_unset=True)
    if "role" in values and (
            values["role"] not in ALLOWED_ROLES or
            (actor.role == "store_admin" and values["role"] == "store_admin")):
        raise HTTPException(422, detail={"detail": "Rol no permitido", "code": "INVALID_ROLE"})
    if "password" in values:
        user.password_hash = hash_password(values.pop("password"))
    for key, value in values.items():
        setattr(user, key, value)
    session.commit()
    return _public(user)
