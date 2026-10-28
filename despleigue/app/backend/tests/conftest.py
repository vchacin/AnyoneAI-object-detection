"""Hermetic database, storage and synthetic model catalog for backend tests."""
import hashlib
import json
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ENVIRONMENT"] = "development"
os.environ["INFERENCE_BACKEND"] = "local"
os.environ.pop("APP_SECRET_ARN", None)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backend.db import session as db
from app.backend.services import model_registry, storage_service


@pytest.fixture(autouse=True)
def isolated_resources(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(db, "DEFAULT_DB", tmp_path / "test.db")
    monkeypatch.setattr(storage_service, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(storage_service, "STORAGE_BACKEND", "local")
    monkeypatch.setenv("EXPERIMENT_REPORT_DIR", str(tmp_path / "reports"))
    weights = tmp_path / "synthetic.pt"
    weights.write_bytes(b"synthetic test fixture; not a trained model")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"active": "test-model", "models": {"test-model": {
        "path": str(weights), "imgsz": 640, "max_det": 750, "default_conf": 0.25,
        "classes": {"0": "object", "1": "missing"},
        "sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
    }}}), encoding="utf-8")
    monkeypatch.setattr(model_registry, "MANIFEST_PATH", manifest)
    monkeypatch.setenv("SHELFVISION_PRODUCT_WEIGHTS", str(weights))
    monkeypatch.setenv("SHELFVISION_MISSING_WEIGHTS", str(weights))
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    db.init_db()
    yield
    engine.dispose()
