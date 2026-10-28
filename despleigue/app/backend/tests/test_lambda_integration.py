import base64
from datetime import timedelta
import io
import json

import cv2
import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.backend import main
from app.backend.core.config import settings
from app.backend.core.security import create_token
from app.backend.db import models, session as db
from app.backend.services import lambda_service


def png():
    ok, encoded = cv2.imencode(".png", np.zeros((100, 200, 3), dtype=np.uint8))
    assert ok
    return encoded.tobytes()


@pytest.fixture
def remote(monkeypatch):
    calls = []
    body = {
        "ok": True, "model_name": "active", "model_version": "test-v2",
        "model_sha256": "a" * 64, "image_size": [200, 100], "conf_threshold": 0.4,
        "elapsed_ms": 12.5, "detections": [
            {"box": [10, 20, 30, 40], "conf": 0.9, "label": "object"},
            {"box": [50, 20, 70, 40], "conf": 0.8, "label": "missing1"},
        ],
    }

    class Client:
        failure = False
        def invoke(self, **kwargs):
            calls.append(json.loads(kwargs["Payload"]))
            response = {"Payload": io.BytesIO(json.dumps(body).encode())}
            if self.failure:
                response["FunctionError"] = "Unhandled"
            return response

    fake = Client()
    monkeypatch.setattr(lambda_service, "client", lambda: fake)
    monkeypatch.setattr(settings, "inference_backend", "lambda")
    monkeypatch.setattr(settings, "lambda_function_name", "test-function")
    monkeypatch.setattr(main, "get_detector", lambda *args: pytest.fail("Must not load local weights"))
    monkeypatch.setattr(main, "preload_active_model", lambda: pytest.fail("Must not preload local weights"))
    return calls, body, fake


def user_headers(role="store_admin", store_id="store-1"):
    with db.SessionLocal() as session:
        session.add(models.Store(id=store_id, name="Test"))
        session.flush()
        session.add(models.User(id="user-1", email="test@example.com", password_hash="unused",
                                role=role, store_id=store_id))
        session.commit()
    token = create_token(subject="user-1", role=role, store_id=store_id,
                         token_type="access", expires_delta=timedelta(minutes=5))
    return {"Authorization": f"Bearer {token}"}


def test_remote_inference_preserves_ui_and_history_contract(remote):
    calls, body, _ = remote
    raw = png()
    with TestClient(main.app) as client:
        response = client.post("/api/v1/inference?model=active", headers=user_headers(),
                               files={"image": ("test.png", raw, "image/png")}, data={"conf": "0.4"})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["n_objects"] == result["n_missing"] == 1
    assert result["model_version"] == "test-v2"
    assert result["detections"][1]["class"] == "missing"
    assert result["detections"][0]["box"] == [10, 20, 30, 40]
    assert calls == [{"image": base64.b64encode(raw).decode(), "conf": 0.4, "model": "active"}]
    with db.SessionLocal() as session:
        inspection = session.get(models.Inspection, result["inspection_id"])
        assert inspection.model_version == "test-v2"
        assert inspection.store_id == "store-1"
        assert session.query(models.DetectionRecord).count() == 2


@pytest.mark.parametrize("path", ["/api/v1/inference", "/predict"])
def test_anonymous_request_never_invokes_lambda(remote, path):
    calls, _, _ = remote
    with TestClient(main.app) as client:
        response = client.post(path, files={"image": ("test.png", png(), "image/png")})
    assert response.status_code == 401
    assert calls == []


def test_global_legacy_history_is_restricted(remote):
    with TestClient(main.app) as client:
        assert client.get("/api/v1/detections").status_code == 401
        assert client.get("/api/v1/detections", headers=user_headers()).status_code == 403


def test_function_error_does_not_save_prediction(remote):
    _, _, fake = remote
    fake.failure = True
    with TestClient(main.app) as client:
        response = client.post("/api/v1/inference", headers=user_headers(),
                               files={"image": ("test.png", png(), "image/png")})
    assert response.status_code == 502
    with db.SessionLocal() as session:
        assert session.query(models.Inspection).count() == 0
        assert session.query(db.Detection).count() == 0


def test_large_upload_is_rejected_before_lambda(remote):
    calls, _, _ = remote
    with TestClient(main.app) as client:
        response = client.post("/api/v1/inference", headers=user_headers(), files={
            "image": ("large.png", b"x" * (lambda_service.MAX_IMAGE_BYTES + 1), "image/png")})
    assert response.status_code == 413
    assert calls == []


@pytest.mark.parametrize("bad_box", [[0, 0, 999, 20], [20, 0, 10, 20]])
def test_invalid_lambda_boxes_are_rejected(remote, bad_box):
    _, body, _ = remote
    body["detections"][0]["box"] = bad_box
    with pytest.raises(HTTPException) as error:
        lambda_service.predict(png(), conf=None, model=None, width=200, height=100)
    assert error.value.status_code == 502


def test_remote_catalog_does_not_require_local_weights(remote):
    _, body, _ = remote
    body.update(available=True, imgsz=1280, max_det=700, default_conf=0.25,
                source_model="yolo26m-auto-120ep",
                classes=["object", "missing"])
    with TestClient(main.app) as client:
        headers = user_headers()
        catalog = client.get("/api/v1/models", headers=headers).json()
        health = client.get("/api/v1/health", headers=headers).json()
    assert catalog["models"][0]["version"] == "test-v2"
    assert catalog["models"][0]["imgsz"] == 1280
    assert catalog["models"][0]["source"] == "yolo26m-auto-120ep"
    assert health["model_loaded"] is True
    assert health["inference_backend"] == "lambda"


def test_liveness_does_not_invoke_lambda(remote):
    calls, _, _ = remote
    with TestClient(main.app) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/api/v1/health").status_code == 401
        assert client.get("/api/v1/models").status_code == 401
    assert calls == []


def test_camera_cannot_attach_another_stores_shelf(remote):
    import hashlib
    calls, _, _ = remote
    with db.SessionLocal() as session:
        session.add_all([models.Store(id="a", name="A"), models.Store(id="b", name="B")])
        session.flush()
        session.add(models.Shelf(id="shelf-b", store_id="b", name="B"))
        session.add(models.Camera(id="cam-a", store_id="a", name="A", status="active",
                                  token_hash=hashlib.sha256(b"camera-token").hexdigest()))
        session.commit()
    with TestClient(main.app) as client:
        response = client.post("/api/v1/inference", headers={"X-Camera-Token": "camera-token"},
                               data={"shelf_id": "shelf-b"},
                               files={"image": ("test.png", png(), "image/png")})
    assert response.status_code == 404
    assert calls == []
