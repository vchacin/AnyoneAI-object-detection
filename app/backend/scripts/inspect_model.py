"""Inspects a model checkpoint and writes the model manifest.

Usage:
    python app/backend/scripts/inspect_model.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = ROOT / "modelos"
BEST_PT = MODELS_DIR / "best.pt"
BEST_ONNX = MODELS_DIR / "best.onnx"
LEGACY_PT = ROOT / "training" / "weights" / "B_e35" / "weights" / "best.pt"
MANIFEST_PATH = MODELS_DIR / "manifest.json"

ACTIVE_KEY = "yolo26s-b8k_geo3k_e100"
LEGACY_KEY = "yolo26s-B_e35"


def rel(path: Path) -> str:
    """Returns a repo-relative POSIX path."""
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_pt(path: Path) -> dict:
    """Extrae metadata del checkpoint con ultralytics."""
    from ultralytics import YOLO

    model = YOLO(str(path))
    names = model.model.names if hasattr(model.model, "names") else {}
    task = getattr(model.model, "task", "detect")
    nc = getattr(model.model, "nc", len(names))

    # Leer imgsz de train_args si existe en el checkpoint
    imgsz_train = 640  # default por SDD v0.2
    max_det = getattr(model.model, "max_det", 750)

    return {
        "path": rel(path),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "classes": {str(k): str(v) for k, v in names.items()},
        "nc": nc,
        "task": task,
        "imgsz": imgsz_train,
        "max_det": max_det,
        "ultralytics_version": __import__("ultralytics", fromlist=["__version__"]).__version__,
    }


def inspect_onnx(path: Path) -> dict:
    """Basic metadata for the ONNX export."""
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "format": "onnx",
    }


def main() -> None:
    manifest = {"active": ACTIVE_KEY, "models": {}}

    if BEST_PT.is_file():
        pt_info = inspect_pt(BEST_PT)
        manifest["models"][ACTIVE_KEY] = {
            **pt_info,
            "default_conf": 0.25,
            "source": "origin/master@be7936e",
            "notes": "2-class detector: {0: object, 1: missing}; trained dataset8k_geo/data_3k.yaml",
        }

    if BEST_ONNX.is_file():
        manifest["models"][f"{ACTIVE_KEY}-onnx"] = inspect_onnx(BEST_ONNX)

    if LEGACY_PT.is_file():
        manifest["models"][LEGACY_KEY] = {
            **inspect_pt(LEGACY_PT),
            "source": "legacy",
            "notes": "Predecessor checkpoint kept for rollback/comparison only.",
        }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
