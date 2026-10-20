"""Reusable authentication, RBAC, and tenant dependencies."""
from __future__ import annotations

from typing import Callable

import jwt
import hashlib
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..db import models
from ..db.session import get_session
from .security import decode_token, verify_api_key_value


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                         detail={"detail": "Credenciales invalidas", "code": "UNAUTHORIZED"})


def get_current_user(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: Session = Depends(get_session),
) -> models.User:
    if verify_api_key_value(x_api_key):
        user = session.query(models.User).filter(models.User.role == "super_admin").first()
        if user:
            return user
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized()
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
    except (jwt.InvalidTokenError, ValueError):
        raise _unauthorized()
    if payload.get("type") != "access" or not payload.get("sub"):
        raise _unauthorized()
    user = session.get(models.User, payload["sub"])
    if not user or not user.is_active:
        raise _unauthorized()
    return user


def require_role(*roles: str) -> Callable:
    def dependency(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status_code=403,
                                detail={"detail": "No tiene permisos para esta operacion", "code": "FORBIDDEN"})
        return user
    return dependency


def require_store_access(store_id: str, user: models.User) -> None:
    if user.role != "super_admin" and user.store_id != store_id:
        raise HTTPException(status_code=404,
                            detail={"detail": "Recurso no encontrado", "code": "NOT_FOUND"})


def get_camera_by_token(token: str, session: Session) -> models.Camera:
    camera = session.query(models.Camera).filter(
        models.Camera.token_hash == hashlib.sha256(token.encode()).hexdigest(),
        models.Camera.status == "active").first()
    if not camera:
        raise _unauthorized()
    return camera
