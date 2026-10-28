"""Authentication endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.deps import get_current_user
from ..core.security import create_token, hash_password, verify_password, decode_token
from ..db import models
from ..db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(request: Request, email: str | None = Form(default=None),
                password: str | None = Form(default=None), session: Session = Depends(get_session)):
    if email is None or password is None:
        payload = await request.json()
        email = payload.get("email")
        password = payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        raise HTTPException(status_code=422, detail={"detail": "Correo y contraseña son obligatorios", "code": "VALIDATION_ERROR"})
    user = session.query(models.User).filter(models.User.email == email.lower()).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail={"detail": "Correo o contraseña invalidos", "code": "INVALID_CREDENTIALS"})
    jti = str(uuid4())
    refresh_exp = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    session.add(models.RefreshToken(jti=jti, user_id=user.id, expires_at=refresh_exp))
    session.commit()
    claims = {"subject": user.id, "role": user.role, "store_id": user.store_id}
    return {
        "access_token": create_token(**claims, token_type="access", expires_delta=timedelta(minutes=settings.access_token_minutes)),
        "refresh_token": create_token(**claims, token_type="refresh", expires_delta=timedelta(days=settings.refresh_token_days), jti=jti),
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh(refresh_token: str = Form(...), session: Session = Depends(get_session)):
    try:
        payload = decode_token(refresh_token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail={"detail": "Refresh token invalido", "code": "INVALID_REFRESH_TOKEN"})
    if payload.get("type") != "refresh" or not payload.get("jti"):
        raise HTTPException(status_code=401, detail={"detail": "Refresh token invalido", "code": "INVALID_REFRESH_TOKEN"})
    stored = session.get(models.RefreshToken, payload["jti"])
    if not stored or stored.revoked_at or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail={"detail": "Refresh token revocado o expirado", "code": "INVALID_REFRESH_TOKEN"})
    user = session.get(models.User, stored.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"detail": "Usuario inactivo", "code": "INACTIVE_USER"})
    return {"access_token": create_token(subject=user.id, role=user.role, store_id=user.store_id,
                                         token_type="access", expires_delta=timedelta(minutes=settings.access_token_minutes)),
            "token_type": "bearer"}


@router.post("/logout")
def logout(refresh_token: str = Form(...), session: Session = Depends(get_session), _: models.User = Depends(get_current_user)):
    try:
        payload = decode_token(refresh_token)
    except jwt.InvalidTokenError:
        return {"ok": True}
    stored = session.get(models.RefreshToken, payload.get("jti"))
    if stored and not stored.revoked_at:
        stored.revoked_at = datetime.now(timezone.utc)
        session.commit()
    return {"ok": True}


@router.get("/me")
def me(user: models.User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "role": user.role, "store_id": user.store_id, "is_active": user.is_active}


def seed_superadmin(session: Session) -> models.User | None:
    if not settings.first_superadmin_email or not settings.first_superadmin_password:
        return None
    existing = session.query(models.User).filter(models.User.email == settings.first_superadmin_email.lower()).first()
    if existing:
        return existing
    user = models.User(email=settings.first_superadmin_email.lower(),
                       password_hash=hash_password(settings.first_superadmin_password), role="super_admin")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
