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
import time
import json
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .core.security import get_api_key, require_auth
from .db import session as db
from .services.inference_service import get_detector, model_loaded, preload_active_model
from .services.experiment_logger import write_inference_report
from .services.model_registry import (active_model_name, default_model_name,
                                       public_catalog, resolve_model)

logger = logging.getLogger("app.backend.main")

STATIC_DIR = Path(__file__).resolve().parent / "static"
COMPARISON_DIR = Path(__file__).resolve().parents[2] / "app" / "data" / "comparisons"
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "15"))

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialises the database and warms up the active model."""
    db.init_db()
    if get_api_key() is None:
        logger.warning("API_KEY no definida: /predict responde sin autenticacion.")
    preload_active_model()
    yield


app = FastAPI(
    title="AnyoneAI Object Detection",
    description="Deteccion de producto faltante en estanteria de retail.",
    version="1.0.0",
    lifespan=lifespan,
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if COMPARISON_DIR.is_dir():
    app.mount("/comparison-data", StaticFiles(directory=COMPARISON_DIR), name="comparison-data")


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
    confidence_threshold: float
    confidence_summary: dict
    auto_score: float
    used_coco: bool
    model_name: str
    model_version: str
    timings: dict = {}
    detections: list
    camera_id: str | None = None
    shelf_id: str | None = None
    gap_mode: str | None = None
    latency_ms: float | None = None
    experiment_id: str | None = None
    experiment_report: str | None = None
    detection_id: int | None = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    auth_required: bool
    database: str
    model_version: str | None = None
    model_sha256: str | None = None
    device: str | None = None
    imgsz: int | None = None


class ReviewPayload(BaseModel):
    index: int
    verdict: str
    note: str = ""


@app.get("/", include_in_schema=False)
def index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.is_file():
        return {"docs": "/docs", "health": "/health"}
    return FileResponse(index_file)


@app.get("/comparison", include_in_schema=False)
def comparison():
    return FileResponse(STATIC_DIR / "comparison.html")


@app.get("/api/v1/comparisons")
def comparisons():
    runs = []
    if COMPARISON_DIR.is_dir():
        for manifest_path in sorted(COMPARISON_DIR.glob("*/manifest.json"), reverse=True):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            runs.append({key: manifest[key] for key in ("run_id", "created_at", "processed_count", "seed")})
    return {"runs": runs}


@app.get("/api/v1/comparisons/{run_id}/manifest")
def comparison_manifest(run_id: str):
    manifest_path = COMPARISON_DIR / run_id / "manifest.json"
    if not manifest_path.is_file():
        raise HTTPException(status_code=404, detail="Comparacion no encontrada")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@app.post("/api/v1/comparisons/{run_id}/review")
def comparison_review(run_id: str, payload: ReviewPayload):
    if payload.verdict not in {"official", "shelfvision", "tie", "unclear"}:
        raise HTTPException(status_code=422, detail="Veredicto invalido")
    run_dir = COMPARISON_DIR / run_id
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise HTTPException(status_code=404, detail="Comparacion no encontrada")
    review_path = run_dir / "reviews.jsonl"
    with review_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"index": payload.index, "verdict": payload.verdict,
                                 "note": payload.note, "created_at": time.time()}, ensure_ascii=False) + "\n")
    return {"ok": True, "index": payload.index, "verdict": payload.verdict}


@app.get("/api/v1/health", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse, include_in_schema=False)
def health() -> HealthResponse:
    from .services.inference_service import model_loaded

    spec = None
    try:
        spec = resolve_model(None)
    except ValueError:
        pass

    return HealthResponse(
        status="ok",
        model_loaded=model_loaded(),
        auth_required=get_api_key() is not None,
        database=db.DATABASE_URL.split("://", 1)[0],
        model_version=spec.version if spec else None,
        model_sha256=(spec.sha256 or "")[:12] or None,
        device=os.environ.get("DEVICE", "cpu"),
        imgsz=spec.imgsz if spec else None,
    )


@app.get("/api/v1/models")
def models():
    """Lists configured models without loading their weights."""
    return {
        "default_model": active_model_name(),
        "models": public_catalog(),
    }


@app.post("/api/v1/inference", response_model=PredictResponse,
          dependencies=[require_auth])
@app.post("/predict", response_model=PredictResponse,
          dependencies=[require_auth], include_in_schema=False)
def predict(
    image: UploadFile | None = File(default=None),
    file: UploadFile | None = File(default=None),
    model: str | None = None,
    camera_id: str | None = Form(default=None),
    shelf_id: str | None = Form(default=None),
    conf: float | None = Form(default=None),
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

    if conf is not None and not 0.0 <= conf <= 1.0:
        raise HTTPException(status_code=422,
                            detail="El valor de conf debe estar entre 0 y 1")

    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=415, detail="No se pudo decodificar la imagen")

    try:
        resolve_model(model)
        detector = get_detector(model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    started = time.perf_counter()
    result = detector.predict(image, conf=conf)
    result.setdefault("timings", {})["total_ms"] = round(
        (time.perf_counter() - started) * 1000.0, 2
    )
    height, width = image.shape[:2]
    confidence_values = [item["confidence"] for item in result["objects"] + result["missing"]
                         if item.get("confidence") is not None]
    result["confidence_summary"] = {
        "objects": {
            "count": len(result["objects"]),
            "min": min((item["confidence"] for item in result["objects"]), default=None),
            "median": float(np.median([item["confidence"] for item in result["objects"]]))
            if result["objects"] else None,
            "max": max((item["confidence"] for item in result["objects"]), default=None),
        },
        "missing": {
            "count": len(result["missing"]),
            "min": min((item["confidence"] for item in result["missing"]), default=None),
            "median": float(np.median([item["confidence"] for item in result["missing"]]))
            if result["missing"] else None,
            "max": max((item["confidence"] for item in result["missing"]), default=None),
            "types": sorted({item.get("confidence_type", "unknown") for item in result["missing"]}),
        },
        "all": {"count": len(confidence_values)},
    }
    experiment_id, experiment_report = write_inference_report(
        image_name=upload.filename or "upload",
        detector=detector,
        result=result,
        width=width,
        height=height,
    )

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
        confidence_threshold=result["confidence_threshold"],
        confidence_summary=result["confidence_summary"],
        auto_score=result["auto_score"],
        used_coco=result["used_coco"],
        model_name=result["model_name"],
        model_version=result["model_version"],
        timings=result.get("timings", {}),
        detections=result["detections"],
        camera_id=camera_id,
        shelf_id=shelf_id,
        gap_mode=result.get("gap_mode"),
        latency_ms=result.get("latency_ms"),
        experiment_id=experiment_id,
        experiment_report=experiment_report,
        detection_id=detection_id,
    )


@app.get("/api/v1/detections", dependencies=[require_auth])
@app.get("/detections", dependencies=[require_auth], include_in_schema=False)
def list_detections(limit: int = 50, session: Session = Depends(db.get_session)):
    rows = session.query(db.Detection).order_by(db.Detection.id.desc()) \
        .limit(min(limit, 500)).all()
    return [row.as_dict() for row in rows]
