"""Model loading and missing-product prediction.

Wraps the serving pipeline: loads the YOLO detector from the model registry
(manifest driven), optionally a COCO occluder detector, and applies
`gap_heuristic` over the predicted boxes. The heuristic itself lives in
`gap_heuristic.py` and is the same one used by the offline labeling, so what
was validated in the notebook runs identically in production.

The `GAP_MODE` environment variable selects how `missing` detections are
produced:

    - `model`    (default) only the two-class network output is used.
    - `heuristic` only the geometric heuristic is used.
    - `hybrid`   both are merged, deduplicated by IoU.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from .gap_heuristic import AUTO_SCORE, OCCLUDERS, iou, score_candidates
from .model_registry import ModelSpec, resolve_model, verify_checksum
from .shelfvision_service import ShelfVisionDetector

logger = logging.getLogger("app.backend.inference")

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WEIGHTS = ROOT / "modelos" / "best.pt"
if not DEFAULT_WEIGHTS.is_file():
    DEFAULT_WEIGHTS = ROOT / "training" / "weights" / "B_e35" / "weights" / "best.pt"
DEFAULT_COCO_WEIGHTS = ROOT / "training" / "weights" / "yolo26n.pt"

GAP_MODES = ("model", "heuristic", "hybrid")


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def gap_mode() -> str:
    """Returns the configured gap source mode."""
    mode = os.environ.get("GAP_MODE", "model").strip().lower()
    return mode if mode in GAP_MODES else "model"


def _box_record(box, confidence, class_name, source):
    return {
        "box": [round(float(value), 2) for value in box],
        "confidence": round(float(confidence), 5),
        "confidence_type": "model_confidence",
        "class": class_name,
        "source": source,
    }


def _merge_missing(model_missing, heuristic_missing, iou_threshold=0.3):
    """Prefiere la detección aprendida cuando coincide con un hueco heurístico."""
    merged = list(model_missing)
    for candidate in heuristic_missing:
        if not any(iou(candidate["box"], detected["box"]) >= iou_threshold
                   for detected in model_missing):
            merged.append(candidate)
    return merged


class Detector:
    """Detector de productos + heuristica de huecos, cargado una sola vez.

    Ultralytics no es thread-safe en inferencia concurrente sobre el mismo
    objeto, asi que se serializa con un lock.
    """

    def __init__(self, weights: Path = DEFAULT_WEIGHTS,
                 coco_weights: Path | None = DEFAULT_COCO_WEIGHTS,
                 conf: float | None = None, iou: float = 0.7,
                 auto_score: float | None = None,
                 use_coco: bool = True, model_name: str = "official",
                 model_version: str | None = None,
                 imgsz: int = 640, max_det: int = 750):
        self.weights = Path(weights)
        self.model_name = model_name
        if not self.weights.is_file():
            raise FileNotFoundError(
                f"No se encuentra el modelo {self.weights}. Entrenar con "
                f"training/pipeline_completo.ipynb o establecer INFERENCE_WEIGHTS.")

        from ultralytics import YOLO

        self.model = YOLO(str(self.weights))
        self.model_version = model_version or os.environ.get("MODEL_VERSION", self.weights.stem)
        self.imgsz = int(imgsz)
        self.max_det = int(max_det)
        self.conf = env_float("INFERENCE_CONF", 0.25) if conf is None else conf
        self.iou = iou
        self.auto_score = env_float("GAP_AUTO_SCORE", AUTO_SCORE) \
            if auto_score is None else auto_score
        self.device = os.environ.get("DEVICE", "cpu")
        self.gap_mode = gap_mode()

        self.coco = None
        if use_coco and coco_weights and Path(coco_weights).is_file():
            self.coco = YOLO(str(coco_weights))
        self._lock = threading.Lock()

    def predict(self, image: np.ndarray, conf: float | None = None) -> dict:
        """Detects products and gaps over a BGR image.

        Returns `objects` (product xyxy boxes) and `candidates` (gaps with
        their score and the threshold flag). Boxes are always expressed in
        original image pixels: ultralytics rescales them back after the
        internal letterbox, and the heuristic runs on the original frame.
        """
        started = time.perf_counter()
        threshold = self.conf if conf is None else float(conf)
        with self._lock:
            result = self.model.predict(
                image, conf=threshold, iou=self.iou, imgsz=self.imgsz,
                max_det=self.max_det, device=self.device, verbose=False,
            )[0]
            boxes = result.boxes
            objects = []
            model_missing = []
            if boxes is not None:
                names = result.names
                xyxy = boxes.xyxy.cpu().numpy().tolist()
                classes = boxes.cls.cpu().numpy().tolist()
                confidences = boxes.conf.cpu().numpy().tolist()
                for box, class_id, confidence in zip(xyxy, classes, confidences):
                    class_name = str(names[int(class_id)]).lower()
                    # Normalise alias class names (e.g. "missing1") to the
                    # canonical "missing" label used by the backend and frontend.
                    if class_name == "missing1":
                        class_name = "missing"
                    record = _box_record(box, confidence, class_name, "model")
                    if class_name == "missing":
                        model_missing.append(record)
                    else:
                        objects.append(record)
            occluders = None
            if self.coco is not None:
                coco = self.coco.predict(image, conf=0.25, verbose=False)[0]
                names = coco.names
                occluders = [[float(v) for v in xy]
                             for xy, c in zip(coco.boxes.xyxy.tolist(),
                                              coco.boxes.cls.tolist())
                             if names[int(c)] in OCCLUDERS]

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        object_boxes = [record["box"] for record in objects]
        candidates = score_candidates(gray, object_boxes, self.auto_score, occluders)
        heuristic_missing = [
            {**candidate, "confidence": candidate["score"],
             "confidence_type": "heuristic_score",
             "class": "missing", "source": "heuristic"}
            for candidate in candidates if candidate["auto"]
        ]

        if self.gap_mode == "model":
            missing = list(model_missing)
        elif self.gap_mode == "heuristic":
            missing = list(heuristic_missing)
        else:
            missing = _merge_missing(model_missing, heuristic_missing)

        return {
            "objects": objects,
            "candidates": candidates,
            "missing": missing,
            "detections": objects + missing,
            "conf": threshold,
            "confidence_threshold": threshold,
            "auto_score": self.auto_score,
            "used_coco": self.coco is not None,
            "model_version": self.model_version,
            "model_name": self.model_name,
            "gap_mode": self.gap_mode,
            "imgsz": self.imgsz,
            "max_det": self.max_det,
            "device": self.device,
            "latency_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }


_detectors: dict[str, Detector] = {}
_detector_lock = threading.Lock()


def get_detector(model_name: str | None = None) -> Detector:
    """Loads and caches the selected detector.

    The registry spec drives the inference parameters, so the manifest stays
    the single source of truth for `imgsz`, `max_det` and the default
    confidence threshold.
    """
    spec: ModelSpec = resolve_model(model_name)
    if spec.name not in _detectors:
        with _detector_lock:
            if spec.name not in _detectors:
                if spec.pipeline == "shelfvision":
                    if spec.missing_weights is None:
                        raise FileNotFoundError("Falta configurar el modelo de faltantes de ShelfVision.")
                    _detectors[spec.name] = ShelfVisionDetector(
                        spec.weights, spec.missing_weights,
                        model_name=spec.name, model_version=spec.version,
                    )
                else:
                    _detectors[spec.name] = Detector(
                        spec.weights,
                        model_name=spec.name,
                        model_version=spec.version,
                        imgsz=spec.imgsz,
                        max_det=spec.max_det,
                        conf=spec.default_conf,
                    )
    return _detectors[spec.name]


def preload_active_model() -> Detector | None:
    """Loads the active model at startup to avoid a cold first request."""
    try:
        spec = resolve_model(None)
        verify_checksum(spec)
        return get_detector(spec.name)
    except (ValueError, FileNotFoundError) as exc:
        logger.warning("Active model is not available: %s", exc)
        return None


def reset_detector() -> None:
    with _detector_lock:
        _detectors.clear()


def model_loaded() -> bool:
    """True if the model is already loaded (useful for /health)."""
    return bool(_detectors)
