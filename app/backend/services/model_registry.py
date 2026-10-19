"""Model registry backed by `modelos/manifest.json`.

The manifest is the single source of truth for available checkpoints: paths,
SHA256 digests, class maps and inference parameters (`imgsz`, `max_det`,
`default_conf`). `model_version` exposed to clients is the manifest key, so the
API contract stays stable while the underlying weights change.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("app.backend.model_registry")

ROOT = Path(__file__).resolve().parents[3]
# Root used to resolve the weights of the manifest entries. In Docker the
# weights are mounted read-only at /models while the manifest lives in the
# image, so the folder name has to be overridable.
MODEL_ROOT = Path(os.environ.get("MODEL_ROOT") or ROOT)
MANIFEST_PATH = Path(
    os.environ.get("MODEL_MANIFEST") or ROOT / "modelos" / "manifest.json"
)


@dataclass(frozen=True)
class ModelSpec:
    """Immutable description of one registered model."""

    name: str
    weights: Path
    version: str
    pipeline: str = "official"
    missing_weights: Path | None = None
    imgsz: int = 640
    max_det: int = 750
    default_conf: float = 0.25
    classes: dict[str, str] = field(default_factory=dict)
    sha256: str | None = None
    source: str | None = None


def _read_manifest() -> dict:
    """Loads the manifest, returning an empty structure when absent."""
    if not MANIFEST_PATH.is_file():
        logger.warning("Model manifest not found at %s", MANIFEST_PATH)
        return {"active": None, "models": {}}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Model manifest is unreadable: %s", exc)
        return {"active": None, "models": {}}


def _candidate_paths(raw: str | None) -> list[Path]:
    """Returns the ordered candidate locations for a manifest entry.

    The repository layout is the first candidate. `MODEL_ROOT` covers the
    Docker deployment, where the weights are mounted at `/models` but the
    manifest ships inside the image. `MODEL_PATH` is the last resort.
    """
    if not raw:
        return []
    relative = Path(raw)
    candidates = [relative if relative.is_absolute() else ROOT / relative]
    if MODEL_ROOT != ROOT:
        candidates.append(relative if relative.is_absolute() else MODEL_ROOT / relative)
        candidates.append(MODEL_ROOT / relative.name)
    configured = os.environ.get("MODEL_PATH") or os.environ.get("INFERENCE_WEIGHTS")
    if configured:
        candidates.append(Path(configured))
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _resolve_path(raw: str | None) -> Path | None:
    """Resolves a manifest path, preferring the first existing candidate."""
    candidates = _candidate_paths(raw)
    if not candidates:
        return None
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _legacy_spec(name: str) -> ModelSpec:
    """Builds a spec for checkpoints that are not registered in the manifest."""
    configured = os.environ.get("MODEL_PATH") or os.environ.get("INFERENCE_WEIGHTS")
    if configured:
        weights = Path(configured)
    else:
        candidate = ROOT / "modelos" / "best.pt"
        weights = candidate if candidate.is_file() else (
            ROOT / "training" / "weights" / "B_e35" / "weights" / "best.pt"
        )
    return ModelSpec(
        name=name,
        weights=weights,
        version=os.environ.get("MODEL_VERSION", weights.stem),
    )


def _shelfvision_spec() -> ModelSpec:
    """Builds the spec of the two-model ShelfVision pipeline."""
    product_weights = Path(os.environ.get(
        "SHELFVISION_PRODUCT_WEIGHTS",
        ROOT / "modelos" / "shelfvision" / "product_best.pt",
    ))
    missing_weights = Path(os.environ.get(
        "SHELFVISION_MISSING_WEIGHTS",
        ROOT / "modelos" / "shelfvision" / "missing_best.pt",
    ))
    return ModelSpec(
        name="shelfvision",
        weights=product_weights,
        missing_weights=missing_weights,
        version=os.environ.get("SHELFVISION_MODEL_VERSION", "manifest-v1"),
        pipeline="shelfvision",
    )


def model_catalog() -> dict[str, ModelSpec]:
    """Builds the catalog of registered models plus the built-in fallbacks."""
    manifest = _read_manifest()
    catalog: dict[str, ModelSpec] = {}

    for name, entry in (manifest.get("models") or {}).items():
        weights = _resolve_path(entry.get("path"))
        if weights is None:
            continue
        catalog[name] = ModelSpec(
            name=name,
            weights=weights,
            version=name,
            pipeline=entry.get("pipeline", "official"),
            imgsz=int(entry.get("imgsz", 640)),
            max_det=int(entry.get("max_det", 750)),
            default_conf=float(entry.get("default_conf", 0.25)),
            classes=dict(entry.get("classes") or {}),
            sha256=entry.get("sha256"),
            source=entry.get("source"),
        )

    catalog.setdefault("official", _legacy_spec("official"))
    catalog.setdefault("shelfvision", _shelfvision_spec())
    return catalog


def active_model_name() -> str:
    """Returns the manifest `active` key unless `MODEL_NAME` overrides it."""
    override = os.environ.get("MODEL_NAME")
    if override:
        return override
    manifest = _read_manifest()
    return manifest.get("active") or "official"


def default_model_name() -> str:
    """Backwards-compatible alias of `active_model_name`."""
    return active_model_name()


def resolve_model(name: str | None = None) -> ModelSpec:
    """Resolves a model name into its spec."""
    selected = name or active_model_name()
    catalog = model_catalog()
    try:
        return catalog[selected]
    except KeyError as exc:
        available = ", ".join(sorted(catalog))
        raise ValueError(
            f"Modelo desconocido '{selected}'. Disponibles: {available}."
        ) from exc


def verify_checksum(spec: ModelSpec) -> bool:
    """Verifies the SHA256 digest of a spec, logging a warning on mismatch."""
    if not spec.sha256:
        return True
    if not spec.weights.is_file():
        logger.warning("Model file missing for %s: %s", spec.name, spec.weights)
        return False
    import hashlib

    digest = hashlib.sha256()
    with spec.weights.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != spec.sha256:
        logger.warning(
            "SHA256 mismatch for %s: expected %s, got %s",
            spec.name, spec.sha256, digest.hexdigest(),
        )
        return False
    return True


def public_catalog() -> list[dict[str, object]]:
    """Returns the public description of every registered model."""
    return [
        {
            "name": spec.name,
            "version": spec.version,
            "pipeline": spec.pipeline,
            "imgsz": spec.imgsz,
            "max_det": spec.max_det,
            "default_conf": spec.default_conf,
            "classes": spec.classes,
            "sha256": (spec.sha256 or "")[:12],
            "source": spec.source,
            "available": spec.weights.is_file() and (
                spec.missing_weights is None or spec.missing_weights.is_file()
            ),
        }
        for spec in model_catalog().values()
    ]
