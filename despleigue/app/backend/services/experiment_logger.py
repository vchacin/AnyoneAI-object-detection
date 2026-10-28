"""Persistencia portable de reportes de inferencia."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_inference_report(*, image_name: str, detector, result: dict,
                           width: int, height: int) -> tuple[str, str]:
    experiment_id = uuid.uuid4().hex[:12]
    report_dir = Path(os.environ.get(
        "EXPERIMENT_REPORT_DIR", str(ROOT / "training" / "reports" / "inference")
    ))
    report_dir.mkdir(parents=True, exist_ok=True)
    weights = Path(detector.weights) if detector is not None else None
    report = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "inference",
        "image": {"name": image_name, "width": width, "height": height},
        "model": {
            "name": detector.model_name if detector else result["model_name"],
            "version": detector.model_version if detector else result["model_version"],
            "pipeline": ("shelfvision" if hasattr(detector, "missing_weights") else "official") if detector else "lambda",
            "weights": str(weights) if weights else None,
            "weights_sha256": _sha256(weights) if weights else result.get("model_sha256"),
            "missing_weights": str(detector.missing_weights) if hasattr(detector, "missing_weights") else None,
            "missing_weights_sha256": _sha256(Path(detector.missing_weights)) if hasattr(detector, "missing_weights") else None,
        },
        "parameters": {
            "confidence": result.get("conf"),
            "auto_score": result.get("auto_score"),
        },
        "results": {
            "objects": len(result.get("objects", [])),
            "missing": len(result.get("missing", [])),
            "timings": result.get("timings", {}),
            "confidence_summary": result.get("confidence_summary"),
        },
    }
    path = report_dir / f"{experiment_id}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return experiment_id, str(path)
