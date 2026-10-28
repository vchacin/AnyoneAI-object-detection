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
import io
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import jwt
import numpy as np
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from .core.security import get_api_key, decode_token, verify_api_key_value
from .core.deps import get_camera_by_token, get_current_user, require_role
from .db import models
from .services.audit_service import record_action
from .services.storage_service import put as store_image
from .services.alert_service import create_for_inspection
from .core.config import settings
from .core.errors import http_exception_handler, validation_exception_handler
from .routers import auth as auth_router
from .routers import stores as stores_router
from .routers import cameras as cameras_router
from .routers import shelves as shelves_router
from .routers import users as users_router
from .routers import staff as staff_router
from .routers import inspections as inspections_router
from .routers import alerts as alerts_router
from .routers import analytics as analytics_router
from .routers import demo_settings
from .routers.auth import seed_superadmin
from .db import session as db
from .services.inference_service import get_detector, model_loaded, preload_active_model
from .services.experiment_logger import write_inference_report
from .services import lambda_service, runpod_service
from .services.model_registry import (active_model_name, default_model_name,
                                       public_catalog, resolve_model)

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"level": record.levelname, "logger": record.name,
                           "message": record.getMessage()}, ensure_ascii=False)


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())
logger = logging.getLogger("app.backend.main")

STATIC_DIR = Path(__file__).resolve().parent / "static"
COMPARISON_DIR = Path(__file__).resolve().parents[2] / "app" / "data" / "comparisons"
MAX_UPLOAD_MB = settings.max_upload_mb

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialises the database and warms up the active model."""
    if settings.environment != "production":
        db.init_db()
    with db.SessionLocal() as session:
        seed_superadmin(session)
    if settings.inference_backend == "local":
        preload_active_model()
    yield


app = FastAPI(
    title="AnyoneAI Object Detection",
    description="Deteccion de producto faltante en estanteria de retail.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)
app.include_router(demo_settings.router)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
if settings.cors_origin_list:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list,
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(stores_router.router, prefix="/api/v1")
app.include_router(cameras_router.router, prefix="/api/v1")
app.include_router(shelves_router.router, prefix="/api/v1")
app.include_router(users_router.router, prefix="/api/v1")
app.include_router(staff_router.router, prefix="/api/v1")
app.include_router(inspections_router.router, prefix="/api/v1")
app.include_router(alerts_router.router, prefix="/api/v1")
app.include_router(analytics_router.router, prefix="/api/v1")

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if COMPARISON_DIR.is_dir():
    app.mount("/comparison-data", StaticFiles(directory=COMPARISON_DIR), name="comparison-data")


class PredictResponse(BaseModel):
    inspection_id: str | None = None
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
    iou: float | None = None
    sahi: bool = False
    imgsz: int | None = None
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
    inference_backend: str = "local"


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
        raise HTTPException(status_code=404, detail="Comparison not found")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@app.post("/api/v1/comparisons/{run_id}/review")
def comparison_review(run_id: str, payload: ReviewPayload):
    if payload.verdict not in {"official", "shelfvision", "tie", "unclear"}:
        raise HTTPException(status_code=422, detail="Invalid verdict")
    run_dir = COMPARISON_DIR / run_id
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise HTTPException(status_code=404, detail="Comparison not found")
    review_path = run_dir / "reviews.jsonl"
    with review_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"index": payload.index, "verdict": payload.verdict,
                                 "note": payload.note, "created_at": time.time()}, ensure_ascii=False) + "\n")
    return {"ok": True, "index": payload.index, "verdict": payload.verdict}


@app.get("/healthz", include_in_schema=False)
def liveness():
    return {"status": "ok"}


@app.get("/api/v1/health", response_model=HealthResponse, dependencies=[Depends(get_current_user)])
@app.get("/health", response_model=HealthResponse, include_in_schema=False, dependencies=[Depends(get_current_user)])
def health() -> HealthResponse:
    if settings.inference_backend == "lambda":
        try:
            remote = lambda_service.metadata()
        except HTTPException:
            remote = {}
        return HealthResponse(
            status="ok", model_loaded=remote.get("available", False),
            auth_required=True, database=db.DATABASE_URL.split("://", 1)[0],
            model_version=remote.get("model_version"), model_sha256=remote.get("model_sha256"),
            device="lambda", imgsz=remote.get("imgsz"), inference_backend="lambda",
        )
    if settings.inference_backend == "runpod":
        try:
            remote = runpod_service.metadata()
        except HTTPException:
            remote = {}
        return HealthResponse(
            status="ok", model_loaded=remote.get("available", False),
            auth_required=True, database=db.DATABASE_URL.split("://", 1)[0],
            model_version=remote.get("model_version"), model_sha256=remote.get("model_sha256"),
            device="runpod", imgsz=remote.get("imgsz"), inference_backend="runpod",
        )
    from .services.inference_service import model_loaded

    spec = None
    try:
        spec = resolve_model(None)
    except ValueError:
        pass

    return HealthResponse(
        status="ok",
        model_loaded=model_loaded(),
        auth_required=True,
        database=db.DATABASE_URL.split("://", 1)[0],
        model_version=spec.version if spec else None,
        model_sha256=(spec.sha256 or "")[:12] or None,
        device=os.environ.get("DEVICE", "cpu"),
        imgsz=spec.imgsz if spec else None,
    )


@app.get("/api/v1/models", dependencies=[Depends(get_current_user)])
def list_models():
    """Lists configured models without loading their weights."""
    if settings.inference_backend == "lambda":
        try:
            remote = lambda_service.metadata()
        except HTTPException:
            return {"default_model": "", "models": []}
        return {"default_model": remote["model_name"], "models": [{
            "name": remote["model_name"], "version": remote["model_version"],
            "pipeline": "lambda", "imgsz": remote["imgsz"], "max_det": remote["max_det"],
            "default_conf": remote["default_conf"], "classes": remote["classes"],
            "sha256": remote.get("model_sha256", ""), "source": remote.get("source_model") or "lambda",
            "available": remote["available"],
        }]}
    if settings.inference_backend == "runpod":
        try:
            remote = runpod_service.metadata()
        except HTTPException:
            return {"default_model": "", "models": []}
        return {"default_model": remote["model_name"], "models": [{
            "name": remote["model_name"], "version": remote["model_version"],
            "pipeline": "runpod", "imgsz": remote["imgsz"], "max_det": remote["max_det"],
            "default_conf": remote["default_conf"], "classes": remote["classes"],
            "sha256": remote.get("model_sha256", ""), "source": remote.get("source_model") or "runpod",
            "available": remote["available"],
        }]}
    return {
        "default_model": active_model_name(),
        "models": public_catalog(),
    }


@app.post("/api/v1/inference", response_model=PredictResponse)
@app.post("/predict", response_model=PredictResponse,
          include_in_schema=False)
def predict(
    image: UploadFile | None = File(default=None),
    file: UploadFile | None = File(default=None),
    model: str | None = None,
    camera_id: str | None = Form(default=None),
    shelf_id: str | None = Form(default=None),
    store_id: str | None = Form(default=None),
    conf: float | None = Form(default=None),
    iou: float | None = Form(default=None),
    sahi: bool = Form(default=False),
    imgsz: int | None = Form(default=None),
    persist: bool = True,
    provider: str | None = Form(default=None),
    session: Session = Depends(db.get_session),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_camera_token: str | None = Header(default=None, alias="X-Camera-Token"),
) -> PredictResponse:
    principal_user: models.User | None = None
    camera = None
    if x_camera_token:
        camera = get_camera_by_token(x_camera_token, session)
    elif authorization and authorization.lower().startswith("bearer "):
        try:
            claims = decode_token(authorization.split(" ", 1)[1])
            if claims.get("type") != "access":
                raise ValueError
            principal_user = session.get(models.User, claims.get("sub"))
            if not principal_user or not principal_user.is_active:
                raise ValueError
        except (ValueError, jwt.InvalidTokenError) as exc:
            raise HTTPException(401, detail={"detail": "Invalid credentials", "code": "UNAUTHORIZED"}) from exc
    elif get_api_key() is not None and not verify_api_key_value(x_api_key):
        raise HTTPException(401, detail={"detail": "Invalid credentials", "code": "UNAUTHORIZED"})
    elif get_api_key() is not None:
        principal_user = session.query(models.User).filter(models.User.role == "super_admin", models.User.is_active.is_(True)).first()
    if not camera and not principal_user:
        raise HTTPException(401, detail={"detail": "Credentials required", "code": "UNAUTHORIZED"})
    if camera:
        if camera_id and camera_id != camera.id:
            raise HTTPException(404, detail={"detail": "Camera not found", "code": "NOT_FOUND"})
        camera_id = camera.id
        shelf_id = shelf_id or camera.shelf_id
        if shelf_id and not session.query(models.Shelf).filter(
            models.Shelf.id == shelf_id, models.Shelf.store_id == camera.store_id).first():
            raise HTTPException(404, detail={"detail": "Shelf not found", "code": "NOT_FOUND"})
    # Un super_admin no tiene tienda propia: puede indicar en cual guardar la inspeccion.
    scope_store_id = principal_user.store_id if principal_user else None
    if principal_user and principal_user.role == "super_admin" and store_id:
        if not session.get(models.Store, store_id):
            raise HTTPException(404, detail={"detail": "Store not found", "code": "NOT_FOUND"})
        scope_store_id = store_id
    if principal_user and camera_id:
        linked_camera = session.query(models.Camera).filter(
            models.Camera.id == camera_id, models.Camera.store_id == scope_store_id).first()
        if not linked_camera:
            raise HTTPException(404, detail={"detail": "Camera not found", "code": "NOT_FOUND"})
    if principal_user and shelf_id:
        linked_shelf = session.query(models.Shelf).filter(
            models.Shelf.id == shelf_id, models.Shelf.store_id == scope_store_id).first()
        if not linked_shelf:
            raise HTTPException(404, detail={"detail": "Shelf not found", "code": "NOT_FOUND"})
    upload = image or file
    if upload is None:
        raise HTTPException(status_code=422, detail="Missing required field: image")
    upload_limit = MAX_UPLOAD_MB * 1024 * 1024
    if settings.inference_backend == "lambda":
        upload_limit = min(upload_limit, lambda_service.MAX_IMAGE_BYTES)
    raw = upload.file.read(upload_limit + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(raw) > upload_limit:
        raise HTTPException(status_code=413,
                            detail=f"File exceeds {upload_limit // (1024 * 1024)} MiB")

    if conf is not None and not 0.0 <= conf <= 1.0:
        raise HTTPException(status_code=422,
                            detail="Confidence must be between 0 and 1")
    if iou is not None and not 0.0 <= iou <= 1.0:
        raise HTTPException(status_code=422, detail="IoU must be between 0 and 1")
    if imgsz is not None and (imgsz < 320 or imgsz > 1920 or imgsz % 32 != 0):
        raise HTTPException(status_code=422, detail="Image size must be a multiple of 32 between 320 and 1920")

    is_jpeg = raw[:3] == b"\xff\xd8\xff"
    is_png = raw[:8] == b"\x89PNG\r\n\x1a\n"
    if not (is_jpeg or is_png):
        raise HTTPException(status_code=415, detail={"detail": "Only JPG or PNG images are accepted", "code": "UNSUPPORTED_MEDIA_TYPE"})
    try:
        with Image.open(io.BytesIO(raw)) as header:
            if header.width > settings.max_image_width or header.height > settings.max_image_height:
                raise HTTPException(422, "Image resolution is not allowed")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(415, "Could not decode the image") from None
    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=415, detail="Could not decode the image")
    height, width = image.shape[:2]
    if width > settings.max_image_width or height > settings.max_image_height:
        raise HTTPException(status_code=422, detail={"detail": "Image resolution is not allowed", "code": "IMAGE_RESOLUTION_TOO_LARGE"})

    detector = None
    started = time.perf_counter()
    backend = (provider or settings.inference_backend).lower()
    if backend not in {"local", "lambda", "runpod"}:
        raise HTTPException(status_code=422, detail="Invalid provider; use local, lambda, or runpod")
    if iou is not None and backend not in {"local", "lambda"}:
        raise HTTPException(status_code=422, detail="IoU can only be adjusted for the local or Lambda model")
    if sahi and backend != "local":
        raise HTTPException(status_code=422, detail="SAHI is only available for the local model")
    if imgsz is not None and backend not in {"local", "lambda"}:
        raise HTTPException(status_code=422, detail="Processing size can only be adjusted for the local or Lambda model")
    if backend == "lambda" and imgsz is not None and imgsz not in {640, 960, 1280, 1600, 1920}:
        raise HTTPException(status_code=422, detail="Lambda supports processing sizes 640, 960, 1280, 1600, and 1920")
    if backend == "lambda":
        result = lambda_service.predict(raw, conf=conf, iou=iou, imgsz=imgsz,
                                        model=model, width=width, height=height)
    elif backend == "runpod":
        result = runpod_service.predict(raw, conf=conf, model=model, width=width, height=height)
    else:
        try:
            spec = resolve_model(model)
            if (iou is not None or sahi or imgsz is not None) and spec.pipeline != "official":
                raise HTTPException(status_code=422, detail="This model does not support these inference settings")
            detector = get_detector(model)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if sahi:
            try:
                kwargs = {"iou": iou, "sahi": True}
                if imgsz is not None:
                    kwargs["imgsz"] = imgsz
                result = detector.predict(image, conf=conf, **kwargs)
            except ModuleNotFoundError as exc:
                if exc.name and (exc.name == "sahi" or exc.name.startswith("sahi.")):
                    raise HTTPException(status_code=503, detail="SAHI is not installed in the local backend") from None
                raise
        else:
            kwargs = {}
            if iou is not None:
                kwargs["iou"] = iou
            if imgsz is not None:
                kwargs["imgsz"] = imgsz
            result = detector.predict(image, conf=conf, **kwargs)
    result.setdefault("timings", {})["total_ms"] = round(
        (time.perf_counter() - started) * 1000.0, 2
    )
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
    inspection_id = None
    if persist:
        try:
            row = db.save_detection(session, image_name=upload.filename or "upload",
                                    result=result, model_weights=str(detector.weights) if detector else result["model_version"])
            detection_id = row.id
        except Exception as exc:  # noqa: BLE001 - persistencia no bloquea la prediccion
            session.rollback()
            logger.warning("No se pudo guardar la deteccion: %s", exc)
        store_id = camera.store_id if camera else scope_store_id
        if store_id:
            extension = ".jpg" if is_jpeg else ".png"
            image_key = store_image(raw, store_id=store_id, extension=extension)
            inspection = models.Inspection(
                store_id=store_id, camera_id=camera_id, shelf_id=shelf_id,
                image_key=image_key,
                image_width=width, image_height=height, image_bytes=len(raw),
                source="camera" if camera else "manual",
                model_version=result["model_version"],
                n_objects=len(result["objects"]), n_missing=len(result["missing"]),
                latency_ms=result.get("latency_ms"), created_by=principal_user.id if principal_user else None,
            )
            session.add(inspection)
            session.flush()
            for item in result["detections"]:
                box = item.get("box", [0, 0, 0, 0])
                session.add(models.DetectionRecord(
                    inspection_id=inspection.id, class_name=item.get("class", "unknown"),
                    x1=box[0], y1=box[1], x2=box[2], y2=box[3],
                    confidence=item.get("confidence", 0), source=item.get("source"),
                ))
            session.commit()
            inspection_id = inspection.id
            create_for_inspection(session, inspection)
            session.commit()
    if camera:
        camera.last_seen = datetime.now(timezone.utc)
        session.commit()
    if principal_user:
        record_action(session, actor_id=principal_user.id, action="inference",
                      entity="inspection", entity_id=inspection_id,
                      store_id=scope_store_id,
                      details={"camera_id": camera_id, "shelf_id": shelf_id})
        session.commit()

    return PredictResponse(
        inspection_id=inspection_id,
        image_name=upload.filename or "upload",
        width=width, height=height,
        n_objects=len(result["objects"]),
        n_missing=len(result["missing"]),
        objects=result["objects"],
        candidates=result["candidates"],
        missing=result["missing"],
        conf=result["conf"],
        confidence_threshold=result["confidence_threshold"],
        iou=result.get("iou"),
        sahi=result.get("sahi", False),
        imgsz=result.get("imgsz"),
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


@app.get("/api/v1/detections")
@app.get("/detections", include_in_schema=False)
def list_detections(limit: int = 50, session: Session = Depends(db.get_session),
                    user: models.User = Depends(require_role("super_admin"))):
    rows = session.query(db.Detection).order_by(db.Detection.id.desc()) \
        .limit(min(limit, 500)).all()
    return [row.as_dict() for row in rows]


DEMO_REPORT_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Reporte Walmart - ShelfVision</title>
<style>
body{font-family:Arial,sans-serif;padding:24px;max-width:720px;margin:auto;color:#333}
h1{color:#1565C0;font-size:20px;margin:0 0 4px}
.sub{color:#616161;margin:0 0 16px}
h2{font-size:16px;margin-top:20px}
table{width:100%;border-collapse:collapse;margin-bottom:16px}
th,td{border:1px solid #E0E0E0;padding:8px;text-align:left}
th{background:#F5F7FA}
.ok{color:#2E7D32}
.warn{color:#F9A825}
.crit{color:#C62828;font-weight:bold}
.footer{font-size:12px;color:#616161;margin-top:24px}
</style>
</head>
<body>
<div style="border-bottom:2px solid #1565C0;padding-bottom:12px;margin-bottom:16px">
  <h1>Reporte de disponibilidad en anaquel</h1>
  <p class="sub">Cliente: Walmart México (ficticio) · Marca: Bonafont · Presentación: 600 ml</p>
  <p class="sub">Periodo: 08:00 – 18:00 · Capturas: 6 · Cámara: 01 · Zona: Centro</p>
</div>

<h2>Resumen ejecutivo</h2>
<p>Se monitoreó el anaquel de agua embotellada durante 10 horas. La presentación 600 ml de
Bonafont presentó agotado visible en <strong>4 de las 6 capturas</strong>, con reposición pendiente al
cierre del periodo. Los huecos aparecieron a partir de las 10:00 y se agudizaron en hora pico (12:00 – 14:00).</p>

<h2>Impacto estimado</h2>
<table>
<tbody>
  <tr><td>Oportunidad bruta afectada</td><td style="font-weight:bold">$1,296</td></tr>
  <tr><td>Venta neta perdida estimada (70 %)</td><td class="crit">$907</td></tr>
  <tr><td>Proyección anualizada por tienda</td><td style="font-weight:bold">$331,128</td></tr>
  <tr><td>Tiempo promedio sin producto</td><td>4.2 h / día</td></tr>
</tbody>
</table>

<h2>Evolución por horario</h2>
<table>
<thead><tr><th>Hora</th><th>Estado</th><th>Observación</th></tr></thead>
<tbody>
  <tr><td>08:00</td><td class="ok">Alta disponibilidad</td><td>Anaquel completo al inicio del día</td></tr>
  <tr><td>10:00</td><td class="warn">Primeros faltantes</td><td>Aparecen huecos en 600 ml</td></tr>
  <tr><td>12:00</td><td class="crit">Faltantes en Bonafont</td><td>600 ml agotado en hora pico</td></tr>
  <tr><td>14:00</td><td class="warn">Producto reubicado</td><td>Otros tamaños ocupan el espacio</td></tr>
  <tr><td>16:00</td><td class="crit">600 ml agotado</td><td>Espacio vacío persistente</td></tr>
  <tr><td>18:00</td><td class="crit">Reposición requerida</td><td>Sin reponer al cierre</td></tr>
</tbody>
</table>

<h2>Acciones sugeridas</h2>
<ul>
  <li>Reponer 600 ml antes del horario pico (12:00 – 14:00).</li>
  <li>Revisar capacidad asignada al frente de Bonafont 600 ml.</li>
  <li>Verificar existencias en bodega para distinguir problema de surtido vs. suministro.</li>
  <li>Programar alerta automática cuando 600 ml esté agotado más de 30 minutos.</li>
</ul>

<p class="footer">Nota: las cifras son simuladas con fines de demostración. Un reporte productivo requiere
datos de ventas por SKU/hora y existencias en bodega.<br>Generado por ShelfVision IA.</p>
</body>
</html>"""


@app.post("/api/v1/demo/report", response_class=HTMLResponse)
@app.post("/demo/report", response_class=HTMLResponse, include_in_schema=False)
def demo_report(user: models.User = Depends(get_current_user)):
    """Devuelve un reporte HTML demo ficticio para Walmart (pitch de 10 min)."""
    return HTMLResponse(content=DEMO_REPORT_HTML, status_code=200)
