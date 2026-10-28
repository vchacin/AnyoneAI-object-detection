"""Synchronous Lambda client and adapter for the existing web API contract."""
from __future__ import annotations

import base64
from functools import lru_cache
import json
import logging
import math

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ..core.config import settings

logger = logging.getLogger(__name__)
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_PAYLOAD_BYTES = 6 * 1024 * 1024


class Detection(BaseModel):
    box: tuple[float, float, float, float]
    conf: float = Field(ge=0, le=1, allow_inf_nan=False)
    label: str

    @field_validator("box")
    @classmethod
    def valid_box(cls, box):
        if not all(math.isfinite(value) for value in box) or box[0] < 0 or box[1] < 0 or box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError("Invalid bounding box")
        return box


class Prediction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ok: bool
    detections: list[Detection]
    image_size: tuple[int, int]
    conf_threshold: float = Field(ge=0, le=1, allow_inf_nan=False)
    iou_threshold: float = Field(ge=0, le=1, allow_inf_nan=False)
    imgsz: int = Field(gt=0)
    elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1, max_length=128)
    model_sha256: str = ""


class Metadata(BaseModel):
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1, max_length=128)
    model_sha256: str = ""
    available: bool = Field(strict=True)
    imgsz: int = Field(gt=0)
    dynamic_image_size: bool = False
    supported_imgsz: list[int] = Field(default_factory=list)
    max_det: int = Field(gt=0)
    default_conf: float = Field(ge=0, le=1, allow_inf_nan=False)
    classes: list[str]
    source_model: str | None = None


@lru_cache
def client():
    import boto3
    from botocore.config import Config
    return boto3.client("lambda", region_name=settings.aws_region, config=Config(
        connect_timeout=5, read_timeout=settings.lambda_read_timeout_seconds,
        retries={"total_max_attempts": 1},
    ))


def invoke(event: dict) -> dict:
    if not settings.lambda_function_name:
        raise HTTPException(503, "Servicio de inferencia pendiente de configurar")
    payload = json.dumps(event, allow_nan=False, separators=(",", ":")).encode()
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise HTTPException(413, "La imagen excede el limite de inferencia")
    try:
        response = client().invoke(FunctionName=settings.lambda_function_name,
                                   InvocationType="RequestResponse", Payload=payload)
        stream = response["Payload"]
        try:
            body = json.loads(stream.read(MAX_PAYLOAD_BYTES + 1))
        finally:
            stream.close()
        if response.get("FunctionError") or not isinstance(body, dict):
            raise ValueError("Lambda invocation failed")
    except Exception as exc:
        logger.warning("Inferencia remota no disponible (%s)", type(exc).__name__)
        raise HTTPException(502, "No se pudo completar la inferencia remota") from None
    if body.get("ok") is not True:
        if body.get("code") == "UNKNOWN_MODEL":
            raise HTTPException(400, "Modelo no disponible; selecciona el modelo activo")
        if body.get("code") == "INVALID_INPUT":
            raise HTTPException(422, "Imagen o parametros de inferencia invalidos")
        if body.get("code") == "MODEL_NOT_READY":
            raise HTTPException(503, "Modelo de inferencia pendiente")
        raise HTTPException(502, "No se pudo completar la inferencia remota")
    return body


def metadata() -> dict:
    """Queries the deployed function; no local weights or stale model cache."""
    body = invoke({"action": "metadata"})
    try:
        return Metadata.model_validate(body).model_dump()
    except ValidationError:
        raise HTTPException(502, "Metadatos de inferencia invalidos") from None


def predict(raw: bytes, *, conf: float | None, iou: float | None,
            imgsz: int | None, model: str | None, width: int, height: int) -> dict:
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Lambda admite imagenes de hasta 4 MiB")
    event = {"image": base64.b64encode(raw).decode("ascii")}
    if conf is not None:
        event["conf"] = conf
    if iou is not None:
        event["iou"] = iou
    if imgsz is not None:
        event["imgsz"] = imgsz
    if model:
        event["model"] = model
    body = invoke(event)
    try:
        result = Prediction.model_validate(body)
        if result.image_size != (width, height):
            raise ValueError("Image dimensions do not match")
        detections = []
        for item in result.detections:
            label = "missing" if item.label.lower() == "missing1" else item.label.lower()
            if label not in {"object", "missing"} or item.box[2] > width or item.box[3] > height:
                raise ValueError("Unsupported detection")
            detections.append({"box": list(item.box), "confidence": item.conf,
                               "class": label, "source": "model",
                               "confidence_type": "model_confidence"})
    except (ValidationError, ValueError):
        raise HTTPException(502, "Respuesta de inferencia incompatible") from None
    return {
        "objects": [item for item in detections if item["class"] == "object"],
        "missing": [item for item in detections if item["class"] == "missing"],
        "candidates": [], "detections": detections,
        "conf": result.conf_threshold, "confidence_threshold": result.conf_threshold,
        "iou": result.iou_threshold, "imgsz": result.imgsz,
        "auto_score": 0.0, "used_coco": False, "gap_mode": "model",
        "model_name": result.model_name, "model_version": result.model_version,
        "model_sha256": result.model_sha256, "latency_ms": result.elapsed_ms,
    }
