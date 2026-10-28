"""Tests for the model manifest and the active model contract."""
from __future__ import annotations

import json

import pytest

from app.backend.services import model_registry
from app.backend.services.model_registry import (active_model_name,
                                                 model_catalog,
                                                 public_catalog,
                                                 resolve_model,
                                                 verify_checksum)

ACTIVE_KEY = "yolo26s-b8k_geo3k_e100"


def test_manifest_is_valid_json():
    manifest = json.loads(model_registry.MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["active"] in manifest["models"]
    assert manifest["models"][manifest["active"]]["classes"] == {
        "0": "object",
        "1": "missing",
    }


def test_active_model_is_registered():
    name = active_model_name()
    assert name in model_catalog()
    spec = resolve_model(name)
    assert spec.version == name
    assert spec.imgsz == 640
    assert spec.max_det == 750
    assert 0.0 < spec.default_conf < 1.0


def test_active_model_checksum_matches():
    spec = resolve_model()
    if spec.sha256:
        assert verify_checksum(spec) is True


def test_public_catalog_exposes_metadata():
    catalog = {item["name"]: item for item in public_catalog()}
    active = catalog[active_model_name()]
    assert active["imgsz"] == 640
    assert active["classes"]["1"] == "missing"
    assert len(active["sha256"]) == 12


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        resolve_model("does-not-exist")
