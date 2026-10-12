"""Servicio FastAPI para la deteccion de producto faltante en retail.

Endpoints:
    GET  /            -> interfaz estatica (app/backend/static/index.html)
    GET  /api/v1/health -> estado del servicio y del modelo
    POST /api/v1/inference -> deteccion de productos y huecos en una imagen
    GET  /api/v1/detections -> historico de imagenes procesadas

Arranque:
    uvicorn app.backend.main:app --reload
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

from .core.security import get_api_key, require_auth
from .db import session as db
from .services.inference_service import get_detector

logger = logging.getLogger("app.backend.main")

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
    model_version: str
    detections: list
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


@app.get("/api/v1/health", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse, include_in_schema=False)
def health() -> HealthResponse:
    from .services.inference_service import model_loaded

    return HealthResponse(
        status="ok",
        model_loaded=model_loaded(),
        auth_required=get_api_key() is not None,
        database=db.DATABASE_URL.split("://", 1)[0],
    )


@app.post("/api/v1/inference", response_model=PredictResponse,
          dependencies=[require_auth])
@app.post("/predict", response_model=PredictResponse,
          dependencies=[require_auth], include_in_schema=False)
def predict(
    image: UploadFile | None = File(default=None),
    file: UploadFile | None = File(default=None),
    persist: bool = True,
    session: Session = Depends(db.get_session),
) -> PredictResponse:
    upload = image or file
    if upload is None:
        raise HTTPException(status_code=422, detail="Falta el campo image")
    raw = upload.file.read()
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
            row = db.save_detection(session, image_name=upload.filename or "upload",
                                    result=result, model_weights=str(detector.weights))
            detection_id = row.id
        except Exception as exc:  # noqa: BLE001 - persistencia no bloquea la prediccion
            session.rollback()
            logger.warning("No se pudo guardar la deteccion: %s", exc)

    return PredictResponse(
        image_name=upload.filename or "upload",
        width=width, height=height,
        n_objects=len(result["objects"]),
        n_missing=len(result["missing"]),
        objects=result["objects"],
        candidates=result["candidates"],
        missing=result["missing"],
        conf=result["conf"],
        auto_score=result["auto_score"],
        used_coco=result["used_coco"],
        model_version=result["model_version"],
        detections=result["detections"],
        detection_id=detection_id,
    )


@app.get("/api/v1/detections", dependencies=[require_auth])
@app.get("/detections", dependencies=[require_auth], include_in_schema=False)
def list_detections(limit: int = 50, session: Session = Depends(db.get_session)):
    rows = session.query(db.Detection).order_by(db.Detection.id.desc()) \
        .limit(min(limit, 500)).all()
    return [row.as_dict() for row in rows]
