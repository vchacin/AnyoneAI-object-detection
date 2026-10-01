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

from .gap_heuristic import AUTO_SCORE, OCCLUDERS, score_candidates

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS = ROOT / "training" / "weights" / "best.pt"
DEFAULT_COCO_WEIGHTS = ROOT / "training" / "weights" / "yolo26n.pt"


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


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
            objects = result.boxes.xyxy.cpu().numpy().tolist() if result.boxes is not None else []
            occluders = None
            if self.coco is not None:
                coco = self.coco.predict(image, conf=0.25, verbose=False)[0]
                names = coco.names
                occluders = [[float(v) for v in xy]
                             for xy, c in zip(coco.boxes.xyxy.tolist(),
                                              coco.boxes.cls.tolist())
                             if names[int(c)] in OCCLUDERS]

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        candidates = score_candidates(gray, objects, self.auto_score, occluders)
        return {
            "objects": [[round(v, 2) for v in b] for b in objects],
            "candidates": candidates,
            "missing": [c for c in candidates if c["auto"]],
            "conf": self.conf,
            "auto_score": self.auto_score,
            "used_coco": self.coco is not None,
        }


_detector: Detector | None = None
_detector_lock = threading.Lock()


def get_detector() -> Detector:
    """Singleton perezoso: el modelo se carga en el primer request."""
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                weights = os.environ.get("INFERENCE_WEIGHTS", DEFAULT_WEIGHTS)
                _detector = Detector(Path(weights))
    return _detector


def reset_detector() -> None:
    global _detector
    with _detector_lock:
        _detector = None


def model_loaded() -> bool:
    """True si el modelo ya se cargo (util para /health)."""
    return _detector is not None
