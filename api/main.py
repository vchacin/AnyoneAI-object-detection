"""Servicio FastAPI para la deteccion de producto faltante en retail.

Endpoints:
  GET  /            -> interfaz estatica (api/static/index.html)
  GET  /health      -> estado del servicio y del modelo
  POST /predict     -> deteccion de productos y huecos en una imagen
  GET  /detections  -> historico de imagenes procesadas

Arranque:
  uvicorn api.main:app --reload
  docker compose up --build
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import db
from .auth import get_api_key, require_auth
from .inference import get_detector

logger = logging.getLogger("api.main")

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "15"))

app = FastAPI(
    title="AnyoneAI Object Detection",
    description="Deteccion de producto faltante en estanteria de retail.",
    version="1.0.0",
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class PredictResponse(BaseModel):
    image_name: str
    width: int
    height: int
    n_objects: int
    n_missing: int
    objects: list
    candidates: list
    missing: list
    conf: float
    auto_score: float
    used_coco: bool
    detection_id: int | None = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    auth_required: bool
    database: str


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()
    if get_api_key() is None:
        logger.warning("API_KEY no definida: /predict responde sin autenticacion.")


@app.get("/", include_in_schema=False)
def index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.is_file():
        return {"docs": "/docs", "health": "/health"}
    return FileResponse(index_file)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    from .inference import model_loaded

    return HealthResponse(
        status="ok",
        model_loaded=model_loaded(),
        auth_required=get_api_key() is not None,
        database=db.DATABASE_URL.split("://", 1)[0],
    )


@app.post("/predict", response_model=PredictResponse, dependencies=[require_auth])
def predict(
    file: UploadFile = File(...),
    persist: bool = True,
    session: Session = Depends(db.get_session),
) -> PredictResponse:
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Archivo vacio")
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413,
                            detail=f"Archivo mayor a {MAX_UPLOAD_MB} MB")

    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=415, detail="No se pudo decodificar la imagen")

    try:
        detector = get_detector()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    result = detector.predict(image)
    height, width = image.shape[:2]

    detection_id = None
    if persist:
        try:
            row = db.save_detection(session, image_name=file.filename or "upload",
                                    result=result, model_weights=str(detector.weights))
            detection_id = row.id
        except Exception as exc:  # noqa: BLE001 - persistencia no bloquea la prediccion
            session.rollback()
            logger.warning("No se pudo guardar la deteccion: %s", exc)

    return PredictResponse(
        image_name=file.filename or "upload",
        width=width, height=height,
        n_objects=len(result["objects"]),
        n_missing=len(result["missing"]),
        objects=result["objects"],
        candidates=result["candidates"],
        missing=result["missing"],
        conf=result["conf"],
        auto_score=result["auto_score"],
        used_coco=result["used_coco"],
        detection_id=detection_id,
    )


@app.get("/detections", dependencies=[require_auth])
def list_detections(limit: int = 50, session: Session = Depends(db.get_session)):
    rows = session.query(db.Detection).order_by(db.Detection.id.desc()) \
        .limit(min(limit, 500)).all()
    return [row.as_dict() for row in rows]
