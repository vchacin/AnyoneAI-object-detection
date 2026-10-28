"""Adaptador del pipeline compuesto de ShelfVision.

Mantiene el pipeline aislado del detector oficial y devuelve el mismo contrato
basico de objetos, faltantes y metadatos de inferencia.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np


def _iou(first: dict, second: dict) -> float:
    x1 = max(first["x1"], second["x1"])
    y1 = max(first["y1"], second["y1"])
    x2 = min(first["x2"], second["x2"])
    y2 = min(first["y2"], second["y2"])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_first = max(0.0, first["x2"] - first["x1"]) * max(0.0, first["y2"] - first["y1"])
    area_second = max(0.0, second["x2"] - second["x1"]) * max(0.0, second["y2"] - second["y1"])
    union = area_first + area_second - intersection
    return intersection / union if union else 0.0


def _rows(objects: list[dict]) -> list[list[dict]]:
    if not objects:
        return []
    median_height = float(np.median([item["y2"] - item["y1"] for item in objects]))
    tolerance = max(20.0, median_height * 0.55)
    rows: list[list[dict]] = []
    for item in sorted(objects, key=lambda value: value["cy"]):
        target = next(
            (row for row in rows if abs(item["cy"] - float(np.median([x["cy"] for x in row]))) <= tolerance),
            None,
        )
        if target is None:
            rows.append([item])
        else:
            target.append(item)
    for row in rows:
        row.sort(key=lambda value: value["cx"])
    return rows


def _candidates(rows: list[list[dict]], gap_factor: float = 1.65) -> list[dict]:
    candidates = []
    for row_index, row in enumerate(rows):
        if len(row) < 4:
            continue
        widths = np.array([item["x2"] - item["x1"] for item in row], dtype=float)
        median_width = float(np.median(widths))
        centers = np.array([item["cx"] for item in row], dtype=float)
        distances = np.diff(centers)
        positive = distances[distances > 1]
        if len(positive) < 2:
            continue
        pitch = float(np.median(positive))
        row_y1 = int(np.median([item["y1"] for item in row]))
        row_y2 = int(np.median([item["y2"] for item in row]))
        for left, right in zip(row, row[1:]):
            center_distance = right["cx"] - left["cx"]
            if center_distance <= gap_factor * pitch or right["x1"] - left["x2"] <= 0.45 * median_width:
                continue
            candidates.append({
                "row": row_index,
                "x1": left["x2"], "y1": row_y1,
                "x2": right["x1"], "y2": row_y2,
                "left": left, "right": right,
                "geometric_score": float(np.clip((center_distance / max(pitch, 1.0) - 1.0) / 1.5, 0.0, 1.0)),
            })
    return candidates


def _opencv_score(image: np.ndarray, candidate: dict) -> tuple[float, bool]:
    x1, y1, x2, y2 = [int(candidate[key]) for key in ("x1", "y1", "x2", "y2")]
    crop = image[max(0, y1):max(y1 + 1, y2), max(0, x1):max(x1 + 1, x2)]
    left = candidate["left"]
    right = candidate["right"]
    neighbor = image[
        max(0, int(min(left["y1"], right["y1"]))):max(y2, int(max(left["y2"], right["y2"]))),
        max(0, int(left["x1"])):min(image.shape[1], int(right["x2"])),
    ]
    if crop.size == 0 or neighbor.size == 0:
        return 0.0, False
    crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    neighbor_gray = cv2.cvtColor(neighbor, cv2.COLOR_BGR2GRAY)
    crop_edges = cv2.Canny(crop_gray, 50, 150)
    neighbor_edges = cv2.Canny(neighbor_gray, 50, 150)
    edge_ratio = np.count_nonzero(crop_edges) / max(1, crop_edges.size)
    reference = np.count_nonzero(neighbor_edges) / max(1, neighbor_edges.size)
    score = float(np.clip(1.0 - edge_ratio / max(reference, 1e-4), 0.0, 1.0))
    return score, bool(edge_ratio < reference * 0.8)


class ShelfVisionDetector:
    """Dos detectores YOLO combinados con geometria y OpenCV."""

    def __init__(self, product_weights: Path, missing_weights: Path,
                 model_name: str = "shelfvision", model_version: str = "v1"):
        self.weights = Path(product_weights)
        self.missing_weights = Path(missing_weights)
        self.model_name = model_name
        self.model_version = model_version
        if not self.weights.is_file():
            raise FileNotFoundError(f"No se encuentra el modelo de productos {self.weights}.")
        if not self.missing_weights.is_file():
            raise FileNotFoundError(f"No se encuentra el modelo de faltantes {self.missing_weights}.")
        from ultralytics import YOLO

        self.product_model = YOLO(str(self.weights))
        self.missing_model = YOLO(str(self.missing_weights))
        self.conf = 0.25
        self.missing_conf = 0.55

    def predict(self, image: np.ndarray) -> dict:
        started = time.perf_counter()
        product_result = self.product_model.predict(image, conf=self.conf, imgsz=768, max_det=1000, verbose=False)[0]
        objects = []
        if product_result.boxes is not None:
            for box, confidence in zip(product_result.boxes.xyxy.cpu().numpy(), product_result.boxes.conf.cpu().numpy()):
                x1, y1, x2, y2 = [float(value) for value in box]
                objects.append({
                    "box": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "cx": (x1 + x2) / 2.0, "cy": (y1 + y2) / 2.0,
                    "confidence": round(float(confidence), 5),
                    "confidence_type": "model_confidence",
                    "class": "object", "source": "shelfvision_product",
                })

        rows = _rows(objects)
        candidates = _candidates(rows)
        missing_result = self.missing_model.predict(image, conf=self.missing_conf, imgsz=768, max_det=300, verbose=False)[0]
        direct_missing = []
        if missing_result.boxes is not None:
            for box, confidence in zip(missing_result.boxes.xyxy.cpu().numpy(), missing_result.boxes.conf.cpu().numpy()):
                x1, y1, x2, y2 = [float(value) for value in box]
                direct_missing.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "confidence": float(confidence)})

        missing = []
        for candidate in candidates:
            opencv_score, opencv_empty = _opencv_score(image, candidate)
            model_score = max((item["confidence"] for item in direct_missing if _iou(candidate, item) >= 0.2), default=0.0)
            components = [(candidate["geometric_score"], 0.25), (opencv_score, 0.40)]
            if model_score:
                components.append((model_score, 0.20))
            score = sum(value * weight for value, weight in components) / sum(weight for _, weight in components)
            if opencv_empty and score >= self.missing_conf:
                missing.append({
                    "box": [round(float(candidate[key]), 2) for key in ("x1", "y1", "x2", "y2")],
                    "confidence": round(float(score), 5), "class": "missing", "source": "shelfvision_hybrid",
                    "confidence_type": "hybrid_score",
                    "row": candidate["row"], "geometric_score": candidate["geometric_score"],
                    "opencv_score": opencv_score, "model_score": model_score or None,
                })
        for item in direct_missing:
            if item["confidence"] >= self.missing_conf and not any(_iou(item, candidate) >= 0.2 for candidate in missing):
                missing.append({
                    "box": [round(item[key], 2) for key in ("x1", "y1", "x2", "y2")],
                    "confidence": round(item["confidence"], 5), "class": "missing", "source": "shelfvision_model",
                    "confidence_type": "model_confidence",
                })

        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return {
            "objects": objects,
            "candidates": candidates,
            "missing": missing,
            "detections": objects + missing,
            "conf": self.conf,
            "confidence_threshold": self.conf,
            "auto_score": self.missing_conf,
            "used_coco": False,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "gap_mode": "hybrid",
            "latency_ms": elapsed_ms,
            "timings": {"total_ms": elapsed_ms},
        }
