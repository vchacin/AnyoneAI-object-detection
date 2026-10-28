"""Contract tests for POST /api/v1/inference.

The detector is replaced with a fake one so the suite stays fast and does not
depend on the weights being present.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest
from datetime import timedelta
from fastapi.testclient import TestClient

from app.backend import main as main_module
from app.backend.services import inference_service
from app.backend.db import models, session as db
from app.backend.core.security import create_token


class FakeDetector:
    """Minimal detector honouring the production result contract."""

    model_name = "fake"
    model_version = "fake-v1"
    weights = "fake-weights"

    def predict(self, image: np.ndarray, conf: float | None = None, iou: float | None = None, sahi: bool = False, imgsz: int | None = None) -> dict:
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
            "iou": 0.7 if iou is None else iou,
            "sahi": sahi,
            "auto_score": 0.5,
            "used_coco": False,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "gap_mode": "model",
            "imgsz": 640 if imgsz is None else imgsz,
            "max_det": 750,
            "device": "cpu",
            "latency_ms": 1.23,
        }


@pytest.fixture()
def client(monkeypatch):
    """Builds a test client whose detector is the fake one."""
    monkeypatch.setattr(main_module, "get_detector", lambda name=None: FakeDetector())
    monkeypatch.setattr(inference_service, "get_detector", lambda name=None: FakeDetector())
    with db.SessionLocal() as session:
        session.add(models.Store(id="store-1", name="Test"))
        session.flush()
        session.add(models.User(id="user-1", email="test@example.com", password_hash="unused",
                                role="store_admin", store_id="store-1"))
        session.add(models.Shelf(id="shelf-7", name="Test", store_id="store-1"))
        session.flush()
        session.add(models.Camera(id="cam-1", name="Test", store_id="store-1", shelf_id="shelf-7", token_hash="unused"))
        session.commit()
    token = create_token(subject="user-1", role="store_admin", store_id="store-1",
                         token_type="access", expires_delta=timedelta(minutes=5))
    with TestClient(main_module.app, headers={"Authorization": f"Bearer {token}"}) as test_client:
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


def test_requested_local_iou_is_returned(client):
    response = client.post(
        "/api/v1/inference?persist=false",
        files={"image": ("frame.png", _png(), "image/png")},
        data={"provider": "local", "conf": "0.3", "iou": "0.5"},
    )
    assert response.status_code == 200
    assert response.json()["confidence_threshold"] == 0.3
    assert response.json()["iou"] == 0.5


def test_sahi_is_confirmed_only_when_requested(client):
    for value in ("true", "false"):
        response = client.post(
            "/api/v1/inference?persist=false",
            files={"image": ("frame.png", _png(), "image/png")},
            data={"provider": "local", "conf": "0.3", "iou": "0.5", "sahi": value, "imgsz": "960"},
        )
        assert response.status_code == 200
        assert response.json()["sahi"] is (value == "true")
        assert response.json()["imgsz"] == 960


@pytest.mark.parametrize("provider, imgsz", [("local", "319"), ("local", "641"), ("local", "1952"), ("lambda", "1280"), ("runpod", "1280")])
def test_invalid_or_remote_image_size_is_rejected(client, provider, imgsz):
    response = client.post(
        "/api/v1/inference?persist=false",
        files={"image": ("frame.png", _png(), "image/png")},
        data={"provider": provider, "imgsz": imgsz},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("provider", ["lambda", "runpod"])
def test_remote_sahi_is_rejected(client, provider):
    response = client.post(
        "/api/v1/inference?persist=false",
        files={"image": ("frame.png", _png(), "image/png")},
        data={"provider": provider, "sahi": "true"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("provider, iou", [("local", "1.1"), ("lambda", "0.5"), ("runpod", "0.5")])
def test_invalid_or_remote_iou_is_rejected(client, provider, iou):
    response = client.post(
        "/api/v1/inference?persist=false",
        files={"image": ("frame.png", _png(), "image/png")},
        data={"provider": provider, "iou": iou},
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


def test_shared_demo_settings_round_trip(client, tmp_path, monkeypatch):
    from app.backend.routers import demo_settings
    path = tmp_path / "config" / "demo-inference.json"
    monkeypatch.setattr(demo_settings, "CONFIG_PATH", path)
    initial = client.get("/api/v1/demo/settings")
    assert initial.status_code == 200
    assert initial.json()["confidence"] == 0.19
    assert initial.json()["imageSize"] == 640
    profile = {**initial.json(), "confidence": 0.3, "imageSize": 960}
    assert client.put("/api/v1/demo/settings", json=profile).status_code == 200
    assert client.get("/api/v1/demo/settings").json() == profile
    assert demo_settings.DemoSettings.model_validate_json(path.read_text()).model_dump() == profile
    assert list(path.parent.iterdir()) == [path]
    assert client.put("/api/v1/demo/settings", json={**profile, "imageSize": 641}).status_code == 422
    assert client.get("/api/v1/demo/settings").json() == profile
    assert client.get("/api/v1/demo/settings", headers={"Authorization": ""}).status_code == 401


def test_shared_demo_settings_reject_non_admin(client, tmp_path, monkeypatch):
    from app.backend.routers import demo_settings
    from app.backend.core.deps import get_current_user
    from types import SimpleNamespace
    monkeypatch.setattr(demo_settings, "CONFIG_PATH", tmp_path / "demo.json")
    main_module.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="viewer")
    try:
        assert client.put("/api/v1/demo/settings", json={}).status_code == 403
        assert not demo_settings.CONFIG_PATH.exists()
    finally:
        main_module.app.dependency_overrides.pop(get_current_user)
