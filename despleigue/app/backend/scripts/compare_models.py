"""Compares registered models over a folder of images.

Usage:
    python app/backend/scripts/compare_models.py [images_dir] [--limit N]

Emits a Markdown table with per-image detection counts and latency. It does
not report precision or recall because no ground truth is available here;
those metrics come from the training reports.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.backend.services.model_registry import model_catalog  # noqa: E402

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def collect_images(folder: Path, limit: int) -> list[Path]:
    """Returns the image files of a folder, sorted by name."""
    images = sorted(
        path for path in folder.rglob("*")
        if path.suffix.lower() in IMAGE_SUFFIXES
    )
    return images[:limit]


def run_model(name: str, images: list[Path]) -> list[dict]:
    """Runs one registered model over the images."""
    from app.backend.services.inference_service import get_detector

    detector = get_detector(name)
    rows = []
    for path in images:
        frame = cv2.imread(str(path))
        if frame is None:
            continue
        result = detector.predict(frame)
        rows.append({
            "image": path.name,
            "n_objects": len(result["objects"]),
            "n_missing": len(result["missing"]),
            "latency_ms": result["latency_ms"],
        })
    return rows


def summarize(rows: list[dict]) -> dict:
    """Aggregates counts and latency for a set of rows."""
    latencies = [row["latency_ms"] for row in rows]
    return {
        "images": len(rows),
        "n_objects": sum(row["n_objects"] for row in rows),
        "n_missing": sum(row["n_missing"] for row in rows),
        "latency_p50_ms": round(statistics.median(latencies), 2) if latencies else None,
        "latency_mean_ms": round(statistics.mean(latencies), 2) if latencies else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "images_dir",
        nargs="?",
        default=str(ROOT / "data_pipeline" / "hard_examples" / "images"),
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    args = parser.parse_args()

    folder = Path(args.images_dir)
    if not folder.is_dir():
        print(f"Images directory not found: {folder}")
        return

    images = collect_images(folder, args.limit)
    if not images:
        print(f"No images found under {folder}")
        return

    catalog = model_catalog()
    report = {}
    for name in catalog:
        if not catalog[name].weights.is_file():
            continue
        try:
            rows = run_model(name, images)
        except Exception as exc:  # noqa: BLE001 - comparison is best effort
            print(f"Skipping {name}: {exc}")
            continue
        report[name] = {"summary": summarize(rows), "rows": rows}

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    print("| model | images | n_objects | n_missing | p50 ms | mean ms |")
    print("|---|---|---|---|---|---|")
    for name, data in report.items():
        summary = data["summary"]
        print(
            f"| {name} | {summary['images']} | {summary['n_objects']} | "
            f"{summary['n_missing']} | {summary['latency_p50_ms']} | "
            f"{summary['latency_mean_ms']} |"
        )


if __name__ == "__main__":
    main()
