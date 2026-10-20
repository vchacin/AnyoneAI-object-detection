"""Local image storage for development and tests."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[3]
UPLOAD_ROOT = Path(os.environ.get("UPLOAD_ROOT", ROOT / "app" / "data" / "uploads"))


def put(data: bytes, *, store_id: str, extension: str) -> str:
    suffix = ".jpg" if extension.lower() in {".jpg", ".jpeg"} else ".png"
    relative = Path("stores") / store_id / "inspections" / f"{uuid4()}{suffix}"
    target = UPLOAD_ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return relative.as_posix()


def get(key: str) -> bytes:
    target = _safe_path(key)
    if not target.is_file():
        raise FileNotFoundError(key)
    return target.read_bytes()


def delete(key: str) -> None:
    target = _safe_path(key)
    if target.is_file():
        target.unlink()


def path_for(key: str) -> Path:
    return _safe_path(key)


def _safe_path(key: str) -> Path:
    root = UPLOAD_ROOT.resolve()
    target = (root / key).resolve()
    if root not in target.parents:
        raise ValueError("Invalid storage key")
    return target
