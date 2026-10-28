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


def test_s3_storage_uses_private_objects_and_signed_urls(monkeypatch):
    import boto3
    from botocore.stub import Stubber
    client = boto3.client("s3", region_name="us-east-1", aws_access_key_id="testing",
                          aws_secret_access_key="testing")
    monkeypatch.setattr(storage_service, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(storage_service, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(storage_service, "_key", lambda *args: "stores/a/inspections/test.png")
    monkeypatch.setattr(storage_service, "_s3_client", lambda: client)
    with Stubber(client) as stub:
        stub.add_response("put_object", {}, {"Bucket": "test-bucket", "Key": "stores/a/inspections/test.png", "Body": b"image"})
        key = storage_service.put(b"image", store_id="a", extension=".png")
        assert key == "stores/a/inspections/test.png"
        assert storage_service.path_for(key) is None
        url = storage_service.presign(key)
        assert "test-bucket" in url and "Signature=" in url
        stub.assert_no_pending_responses()
