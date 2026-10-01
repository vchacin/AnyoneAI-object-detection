"""Convierte las anotaciones CSV de SKU-110K al formato YOLO.

SKU-110K proporciona anotaciones en CSV (image_name,x1,y1,x2,y2,class,w,h) y
YOLO requiere un archivo `.txt` por imagen con `class cx cy w h` normalizado.
Este script genera el par `images/` + `labels/` consumido por Ultralytics.

  python data_pipeline/scripts/to_yolo_format.py \
    --csv data_pipeline/dataset_sku110k/annotations/annotations_train.csv \
    --images-dir data_pipeline/dataset_sku110k/images \
    --out data_pipeline/dataset_sku110k/yolo/train
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from tqdm import tqdm

# La consola de Windows usa cp1252 y no sabe imprimir los iconos de estado.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CSV_COLUMNS = ["image_name", "x1", "y1", "x2", "y2", "class",
               "image_width", "image_height"]


def read_rows(csv_path: Path):
    """Lee el CSV de SKU-110K y agrupa las cajas por imagen."""
    grouped: dict[str, dict] = {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) < 8:
                continue
            name = row[0]
            x1, y1, x2, y2 = (float(v) for v in row[1:5])
            w, h = float(row[6]), float(row[7])
            entry = grouped.setdefault(name, {"w": w, "h": h, "boxes": []})
            entry["boxes"].append((x1, y1, x2, y2))
    return grouped


def to_yolo_line(box, width, height) -> str | None:
    """xyxy absoluto -> `0 cx cy w h` normalizado. None si la caja es invalida."""
    x1, y1, x2, y2 = box
    if width <= 0 or height <= 0 or x2 <= x1 or y2 <= y1:
        return None
    cx = ((x1 + x2) / 2) / width
    cy = ((y1 + y2) / 2) / height
    bw = (x2 - x1) / width
    bh = (y2 - y1) / height
    return f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"


def convert(csv_path: Path, images_dir: Path, out_dir: Path,
            require_image: bool = True) -> dict:
    """Genera `out_dir/labels/<stem>.txt` para cada imagen con anotacion."""
    csv_path, images_dir, out_dir = Path(csv_path), Path(images_dir), Path(out_dir)
    labels_dir = out_dir / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)

    grouped = read_rows(csv_path)
    written = skipped = 0
    for name, entry in tqdm(sorted(grouped.items()), desc="Convirtiendo", unit="img"):
        image_path = images_dir / name
        if require_image and not image_path.is_file():
            skipped += 1
            continue
        lines = [to_yolo_line(b, entry["w"], entry["h"]) for b in entry["boxes"]]
        lines = [line for line in lines if line]
        if not lines:
            skipped += 1
            continue
        (labels_dir / f"{Path(name).stem}.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")
        written += 1

    summary = {"labels_written": written, "skipped": skipped, "out": str(out_dir)}
    print(f"Labels escritos: {written} | omitidos: {skipped}")
    print(f"   Destino: {labels_dir}")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--images-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--allow-missing-images", action="store_true",
                    help="no descartar filas cuya imagen no exista en disco")
    a = ap.parse_args()
    convert(a.csv, a.images_dir, a.out, require_image=not a.allow_missing_images)


if __name__ == "__main__":
    main()
