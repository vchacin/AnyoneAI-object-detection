"""Contract tests for POST /api/v1/inference.

The detector is replaced with a fake one so the suite stays fast and does not
depend on the weights being present.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.backend import main as main_module
from app.backend.services import inference_service


class FakeDetector:
    """Minimal detector honouring the production result contract."""

    model_name = "fake"
    model_version = "fake-v1"
    weights = "fake-weights"

    def predict(self, image: np.ndarray, conf: float | None = None) -> dict:
        threshold = 0.25 if conf is None else conf
        objects = [{
            "box": [10.0, 20.0, 110.0, 220.0],
            "confidence": 0.9,
            "confidence_type": "model_confidence",
            "class": "object",
            "source": "model",
        }]
        missing = [{
            "box": [200.0, 20.0, 300.0, 220.0],
            "confidence": 0.7,
            "confidence_type": "model_confidence",
            "class": "missing",
            "source": "model",
        }]
        return {
            "objects": objects,
            "candidates": [],
            "missing": missing,
            "detections": objects + missing,
            "conf": threshold,
            "confidence_threshold": threshold,
            "auto_score": 0.5,
            "used_coco": False,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "gap_mode": "model",
            "imgsz": 640,
            "max_det": 750,
            "device": "cpu",
            "latency_ms": 1.23,
        }


@pytest.fixture()
def client(monkeypatch):
    """Builds a test client whose detector is the fake one."""
    monkeypatch.setattr(main_module, "get_detector", lambda name=None: FakeDetector())
    monkeypatch.setattr(inference_service, "get_detector", lambda name=None: FakeDetector())
    with TestClient(main_module.app) as test_client:
        yield test_client


def _png() -> bytes:
    frame = np.zeros((400, 600, 3), dtype=np.uint8)
    ok, buffer = cv2.imencode(".png", frame)
    assert ok
    return buffer.tobytes()


def test_inference_returns_detections(client):
    response = client.post("/api/v1/inference",
                           files={"image": ("frame.png", _png(), "image/png")})

    assert response.status_code == 200
    body = response.json()
    assert body["n_objects"] == 1
    assert body["n_missing"] == 1
    assert body["width"] == 600
    assert body["height"] == 400


def test_detections_keep_original_image_coordinates(client):
    response = client.post("/api/v1/inference",
                           files={"image": ("frame.png", _png(), "image/png")})
    body = response.json()

    box = body["detections"][0]["box"]
    assert box == [10.0, 20.0, 110.0, 220.0]
    assert max(box) <= 600


def test_model_sourced_detections_carry_source_field(client):
    response = client.post("/api/v1/inference",
                           files={"image": ("frame.png", _png(), "image/png")})
    body = response.json()

    assert all(item["source"] == "model" for item in body["detections"])
    assert {item["class"] for item in body["detections"]} == {"object", "missing"}


def test_optional_parameters_are_accepted(client):
    response = client.post(
        "/api/v1/inference",
        files={"image": ("frame.png", _png(), "image/png")},
        data={"camera_id": "cam-1", "shelf_id": "shelf-7", "conf": "0.4"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["camera_id"] == "cam-1"
    assert body["shelf_id"] == "shelf-7"
    assert body["conf"] == 0.4


def test_conf_out_of_range_is_rejected(client):
    response = client.post(
        "/api/v1/inference",
        files={"image": ("frame.png", _png(), "image/png")},
        data={"conf": "1.5"},
    )

    assert response.status_code == 422


def test_empty_upload_is_rejected(client):
    response = client.post("/api/v1/inference",
                           files={"image": ("frame.png", b"", "image/png")})

    assert response.status_code == 400


def test_undecodable_image_is_rejected(client):
    response = client.post("/api/v1/inference",
                           files={"image": ("frame.png", b"not-an-image", "image/png")})

    assert response.status_code == 415


def test_health_reports_the_active_model(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "model_version" in body
    assert body["imgsz"] == 640


def test_models_endpoint_exposes_the_catalog(client):
    response = client.get("/api/v1/models")

    assert response.status_code == 200
    body = response.json()
    assert body["default_model"]
    assert any(item["name"] == body["default_model"] for item in body["models"])
