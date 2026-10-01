"""Autenticacion por API key.

Sencillo a proposito: el endpoint de inferencia se protege con `X-API-Key`.
La clave se lee de la variable de entorno `API_KEY`. Sin `API_KEY` definida el
servicio arranca abierto (util para desarrollo local) pero lo avisa por log.

  uvicorn api.main:app --reload
  curl -H "X-API-Key: $API_KEY" -F "file=@foto.jpg" http://localhost:8000/predict
"""
from __future__ import annotations

import hmac
import os
import secrets

from fastapi import Depends, Header, HTTPException, status

API_KEY_ENV = "API_KEY"


def get_api_key() -> str | None:
    return os.environ.get(API_KEY_ENV) or None


def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    """FastAPI dependency. Devuelve la clave si es válida, 401 si no."""
    expected = get_api_key()
    if expected is None:
        return None  # modo abierto (desarrollo)
    if x_api_key is None or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key invalida o ausente",
        )
    return x_api_key


require_auth = Depends(verify_api_key)


def generate_api_key() -> str:
    """Helper para generar una clave nueva: `python -m api.auth`."""
    return secrets.token_urlsafe(32)


if __name__ == "__main__":
    print(generate_api_key())
