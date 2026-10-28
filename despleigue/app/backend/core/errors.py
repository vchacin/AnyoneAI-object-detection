"""Consistent API error helpers."""
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_payload(detail: str, code: str) -> dict:
    return {"detail": detail, "code": code}


async def validation_exception_handler(_: Request, exc) -> JSONResponse:
    return JSONResponse(status_code=422, content=error_payload("Datos invalidos", "VALIDATION_ERROR"))


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"detail", "code"} <= set(exc.detail):
        content = exc.detail
    else:
        content = error_payload(str(exc.detail), "HTTP_ERROR")
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)
