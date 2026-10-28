"""Synchronous RunPod Serverless client and adapter for the inference API contract."""
from __future__ import annotations

import base64
import json
import logging
import math

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ..core.config import settings

logger = logging.getLogger(__name__)
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_PAYLOAD_BYTES = 6 * 1024 * 1024
RUNPOD_BASE = "https://api.runpod.ai/v2"


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
    elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1, max_length=128)
    model_sha256: str = ""


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.runpod_api_key}",
    }


def _invoke(payload: dict) -> dict:
    if not settings.runpod_endpoint_id or not settings.runpod_api_key:
        raise HTTPException(503, "Servicio de inferencia RunPod pendiente de configurar")

    import urllib.request
    import urllib.error

    url = f"{RUNPOD_BASE}/{settings.runpod_endpoint_id}/runsync"
    body = json.dumps({"input": payload}, allow_nan=False, separators=(",", ":")).encode()
    if len(body) > MAX_PAYLOAD_BYTES:
        raise HTTPException(413, "La imagen excede el limite de inferencia")

    req = urllib.request.Request(url, data=body, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=settings.runpod_timeout_seconds) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.warning("RunPod HTTP error: %s %s", exc.code, exc.reason)
        raise HTTPException(502, "No se pudo completar la inferencia remota (RunPod)") from None
    except Exception as exc:
        logger.warning("RunPod inference unavailable (%s)", type(exc).__name__)
        raise HTTPException(502, "No se pudo completar la inferencia remota (RunPod)") from None

    if response_data.get("status") != "COMPLETED":
        raise HTTPException(502, "Inferencia RunPod no completada")

    output = response_data.get("output")
    if not isinstance(output, dict):
        raise HTTPException(502, "Respuesta de RunPod invalida")
    return output


def metadata() -> dict:
    """Queries the deployed RunPod endpoint for model metadata."""
    body = _invoke({"action": "metadata"})
    # RunPod metadata may be nested under output; adapt if needed
    if body.get("ok") is not True:
        raise HTTPException(502, "Metadatos de inferencia RunPod invalidos")
    return body


def predict(raw: bytes, *, conf: float | None, model: str | None,
            width: int, height: int) -> dict:
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "RunPod admite imagenes de hasta 4 MiB")

    payload: dict[str, object] = {"image": base64.b64encode(raw).decode("ascii")}
    if conf is not None:
        payload["conf"] = conf
    if model:
        payload["model"] = model

    body = _invoke(payload)

    if body.get("ok") is not True:
        if body.get("code") == "UNKNOWN_MODEL":
            raise HTTPException(400, "Modelo no disponible; selecciona el modelo activo")
        if body.get("code") == "INVALID_INPUT":
            raise HTTPException(422, "Imagen o parametros de inferencia invalidos")
        if body.get("code") == "MODEL_NOT_READY":
            raise HTTPException(503, "Modelo de inferencia pendiente")
        raise HTTPException(502, "No se pudo completar la inferencia remota (RunPod)")

    try:
        result = Prediction.model_validate(body)
        if result.image_size != (width, height):
            raise ValueError("Image dimensions do not match")
        detections = []
        for item in result.detections:
            label = "missing" if item.label.lower() == "missing1" else item.label.lower()
            if label not in {"object", "missing"} or item.box[2] > width or item.box[3] > height:
                raise ValueError("Unsupported detection")
            detections.append({
                "box": list(item.box), "confidence": item.conf,
                "class": label, "source": "model",
                "confidence_type": "model_confidence",
            })
    except (ValidationError, ValueError):
        raise HTTPException(502, "Respuesta de inferencia RunPod incompatible") from None

    return {
        "objects": [item for item in detections if item["class"] == "object"],
        "missing": [item for item in detections if item["class"] == "missing"],
        "candidates": [], "detections": detections,
        "conf": result.conf_threshold, "confidence_threshold": result.conf_threshold,
        "auto_score": 0.0, "used_coco": False, "gap_mode": "model",
        "model_name": result.model_name, "model_version": result.model_version,
        "model_sha256": result.model_sha256, "latency_ms": result.elapsed_ms,
    }
