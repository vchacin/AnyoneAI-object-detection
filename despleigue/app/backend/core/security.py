"""Password hashing, JWT creation, and legacy API-key compatibility."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status

from .config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$16384$8$1$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_token(*, subject: str, role: str, store_id: str | None, token_type: str, expires_delta: timedelta, jti: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "role": role, "store_id": store_id, "type": token_type,
               "iat": now, "exp": now + expires_delta}
    if jti:
        payload["jti"] = jti
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_api_key() -> str | None:
    return os.environ.get("API_KEY") or None


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def verify_api_key_value(value: str | None) -> bool:
    expected = get_api_key()
    return expected is not None and value is not None and hmac.compare_digest(value, expected)


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str | None:
    """Legacy dependency retained for the unversioned local inference route."""
    expected = get_api_key()
    if expected is None:
        return None
    if not verify_api_key_value(x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"detail": "X-API-Key invalida o ausente", "code": "UNAUTHORIZED"})
    return x_api_key


require_auth = Depends(verify_api_key)
