from datetime import datetime, timezone

import pytest

from app.backend.services import alert_service, storage_service


def test_local_storage_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service, "UPLOAD_ROOT", tmp_path)
    key = storage_service.put(b"image", store_id="store-a", extension=".png")
    assert key.startswith("stores/store-a/inspections/")
    assert storage_service.get(key) == b"image"
    storage_service.delete(key)
    with pytest.raises(FileNotFoundError):
        storage_service.get(key)


def test_storage_rejects_path_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service, "UPLOAD_ROOT", tmp_path)
    with pytest.raises(ValueError):
        storage_service.path_for("../secret.txt")


def test_alert_transition_rejects_closed_alert():
    class Alert:
        status = "closed"

    with pytest.raises(ValueError, match="INVALID_TRANSITION"):
        alert_service.transition(Alert(), "acknowledged", "user-1")
