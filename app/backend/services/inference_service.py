"""Carga de modelos y predicción de producto faltante.

Envoltura del serving: mantiene el detector de productos (YOLO), opcionalmente
un detector COCO para oclusores, y aplica `gap_heuristic` sobre las cajas
predichas. La heurística propiamente dicha reside en `gap_heuristic.py` y es la
misma que utiliza el etiquetado offline, de modo que lo validado en el notebook
se ejecuta de forma idéntica en producción.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

import cv2
import numpy as np

from .gap_heuristic import AUTO_SCORE, OCCLUDERS, iou, score_candidates

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WEIGHTS = ROOT / "modelos" / "best.pt"
if not DEFAULT_WEIGHTS.is_file():
    DEFAULT_WEIGHTS = ROOT / "training" / "weights" / "B_e35" / "weights" / "best.pt"
DEFAULT_COCO_WEIGHTS = ROOT / "training" / "weights" / "yolo26n.pt"


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _box_record(box, confidence, class_name, source):
    return {
        "box": [round(float(value), 2) for value in box],
        "confidence": round(float(confidence), 5),
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
                 use_coco: bool = True):
        self.weights = Path(weights)
        if not self.weights.is_file():
            raise FileNotFoundError(
                f"No se encuentra el modelo {self.weights}. Entrenar con "
                f"training/pipeline_completo.ipynb o establecer INFERENCE_WEIGHTS.")

        from ultralytics import YOLO

        self.model = YOLO(str(self.weights))
        self.model_version = os.environ.get("MODEL_VERSION", self.weights.stem)
        self.conf = env_float("INFERENCE_CONF", 0.25) if conf is None else conf
        self.iou = iou
        self.auto_score = env_float("GAP_AUTO_SCORE", AUTO_SCORE) \
            if auto_score is None else auto_score

        self.coco = None
        if use_coco and coco_weights and Path(coco_weights).is_file():
            self.coco = YOLO(str(coco_weights))
        self._lock = threading.Lock()

    def predict(self, image: np.ndarray) -> dict:
        """Detección de productos y huecos sobre una imagen en formato BGR.

        Devuelve `objects` (cajas xyxy de productos) y `candidates` (huecos con
        su score y el flag de umbral superado).
        """
        with self._lock:
            result = self.model.predict(image, conf=self.conf, iou=self.iou,
                                        verbose=False)[0]
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
            {**candidate, "class": "missing", "source": "heuristic"}
            for candidate in candidates if candidate["auto"]
        ]
        missing = _merge_missing(model_missing, heuristic_missing)
        return {
            "objects": objects,
            "candidates": candidates,
            "missing": missing,
            "detections": objects + missing,
            "conf": self.conf,
            "auto_score": self.auto_score,
            "used_coco": self.coco is not None,
            "model_version": self.model_version,
        }


_detector: Detector | None = None
_detector_lock = threading.Lock()


def get_detector() -> Detector:
    """Singleton perezoso: el modelo se carga en el primer request."""
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                weights = os.environ.get(
                    "MODEL_PATH",
                    os.environ.get("INFERENCE_WEIGHTS", str(DEFAULT_WEIGHTS)),
                )
                _detector = Detector(Path(weights))
    return _detector


def reset_detector() -> None:
    global _detector
    with _detector_lock:
        _detector = None


def model_loaded() -> bool:
    """True si el modelo ya se cargo (util para /health)."""
    return _detector is not None
