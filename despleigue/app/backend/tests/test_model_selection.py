import json

from app.backend.services.experiment_logger import write_inference_report
from app.backend.services.model_registry import public_catalog, resolve_model


def test_catalog_exposes_official_and_shelfvision():
    catalog = {item["name"]: item for item in public_catalog()}

    assert catalog["official"]["pipeline"] == "official"
    assert catalog["shelfvision"]["pipeline"] == "shelfvision"
    assert catalog["shelfvision"]["available"] is True


def test_unknown_model_has_actionable_error():
    try:
        resolve_model("does-not-exist")
    except ValueError as exc:
        assert "official" in str(exc)
        assert "shelfvision" in str(exc)
    else:
        raise AssertionError("resolve_model debe rechazar nombres desconocidos")


def test_inference_report_contains_model_hashes(tmp_path):
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"test-model")

    class FakeDetector:
        model_name = "official"
        model_version = "test"

        def __init__(self, model_weights):
            self.weights = model_weights

    experiment_id, report_path = write_inference_report(
        image_name="fixture.jpg",
        detector=FakeDetector(weights),
        result={"objects": [{"box": [0, 0, 1, 1]}], "missing": [], "timings": {"total_ms": 1.0}},
        width=10,
        height=20,
    )

    report = json.loads(open(report_path, encoding="utf-8").read())
    assert report["schema_version"] == "1.0"
    assert report["experiment_id"] == experiment_id
    assert report["model"]["weights_sha256"]