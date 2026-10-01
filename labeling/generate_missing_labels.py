"""Etiquetado offline de la clase `missing` mediante geometría.

Fase 1 del pipeline: a partir de las cajas de producto (YOLO o CSV de SKU-110K)
agrupa en repisas, mide el pitch y propone huecos de ~1 producto de ancho. No
requiere un modelo de detección entrenado; opcionalmente utiliza un detector
COCO (yolo26n.pt) para descartar candidatos tapados por personas.

La heurística reside en `api/gap_heuristic.py` y es compartida con la API.

Ejecución (venv del repositorio):

  python labeling/generate_missing_labels.py \
    --images-dir data_pipeline/dataset_sku110k/images \
    --csv data_pipeline/dataset_sku110k/annotations/annotations_train.csv \
    --glob "*.jpg" --limit 50 \
    --out data_pipeline/dataset_sku110k/missing_poc
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# La consola de Windows utiliza cp1252 y no admite caracteres Unicode de estado.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from api.gap_heuristic import AUTO_SCORE, OCCLUDERS, score_candidates  # noqa: E402

DEFAULT_COCO_WEIGHTS = ROOT / "training" / "weights" / "yolo26n.pt"


# ---------------------------------------------------------------- entrada

def yolo_to_xyxy(box, w, h):
    cx, cy, bw, bh = box
    return [(cx - bw / 2) * w, (cy - bh / 2) * h,
            (cx + bw / 2) * w, (cy + bh / 2) * h]


def read_yolo_objects(label_path):
    """Lee solo la clase 0 (object) de un label YOLO; devuelve cajas normalizadas."""
    out = []
    for line in Path(label_path).read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        if int(float(parts[0])) != 0:
            continue
        out.append([float(v) for v in parts[1:5]])
    return out


def read_sku_csv(path, wanted=None):
    """SKU110K: image_name,x1,y1,x2,y2,class,image_width,image_height."""
    data = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) < 8:
                continue
            name = row[0]
            if wanted is not None and name not in wanted:
                continue
            x1, y1, x2, y2 = (float(v) for v in row[1:5])
            w, h = float(row[6]), float(row[7])
            entry = data.setdefault(name, {"w": w, "h": h, "boxes": []})
            entry["boxes"].append([x1, y1, x2, y2])
    return data


def load_sources(images_dir, labels_dir, limit, pattern="*"):
    sources = []
    images = sorted(Path(images_dir).glob(pattern))
    if not pattern:
        images = sorted(Path(images_dir).glob("*.jpg")) + \
            sorted(Path(images_dir).glob("*.png"))
    if limit:
        images = images[:limit]
    for img in tqdm(images, desc="Cargando fuentes (labels)", unit="img"):
        label = Path(labels_dir) / f"{img.stem}.txt"
        if not label.is_file():
            continue
        image = cv2.imread(str(img))
        if image is None:
            continue
        h, w = image.shape[:2]
        boxes = [yolo_to_xyxy(b, w, h) for b in read_yolo_objects(label)]
        sources.append({"stem": img.stem, "path": img, "image": image,
                        "w": w, "h": h, "boxes": boxes})
    return sources


def load_sources_from_csv(images_dir, csv_path, limit, pattern):
    images = sorted(Path(images_dir).glob(pattern)) if pattern else \
        sorted(Path(images_dir).glob("*.jpg")) + sorted(Path(images_dir).glob("*.png"))
    if limit:
        images = images[:limit]
    data = read_sku_csv(csv_path, wanted={p.name for p in images})
    sources = []
    for img in tqdm(images, desc="Cargando fuentes (csv)", unit="img"):
        if img.name not in data:
            continue
        image = cv2.imread(str(img))
        if image is None:
            continue
        h, w = image.shape[:2]
        sources.append({"stem": img.stem, "path": img, "image": image,
                        "w": w, "h": h, "boxes": data[img.name]["boxes"]})
    return sources


def coco_occluders(model, image_path, conf=0.25):
    result = model.predict(str(image_path), conf=conf, verbose=False)[0]
    names = result.names
    return [[float(v) for v in xy]
            for xy, c in zip(result.boxes.xyxy.tolist(), result.boxes.cls.tolist())
            if names[int(c)] in OCCLUDERS]


def draw_overlay(image, objects, candidates):
    visual = image.copy()
    for x1, y1, x2, y2 in objects:
        cv2.rectangle(visual, (round(x1), round(y1)), (round(x2), round(y2)),
                      (0, 200, 0), 1)
    for c in candidates:
        x1, y1, x2, y2 = (round(v) for v in c["box"])
        color = (0, 140, 255) if c["auto"] else (0, 0, 255)
        cv2.rectangle(visual, (x1, y1), (x2, y2), color, 2)
        cv2.putText(visual, f'{c["score"]:.2f}', (x1, max(10, y1 - 3)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return visual


# ---------------------------------------------------------------- pipeline

def run(sources, out_dir, model=None, auto_score=AUTO_SCORE):
    out_dir = Path(out_dir)
    (out_dir / "overlays").mkdir(parents=True, exist_ok=True)
    rows, manifest = [], {"auto_score": auto_score, "images": []}
    for s in tqdm(sources, desc="Etiquetando missing", unit="img"):
        gray = cv2.cvtColor(s["image"], cv2.COLOR_BGR2GRAY)
        occluders = coco_occluders(model, s["path"]) if model is not None else None
        cands = score_candidates(gray, s["boxes"], auto_score, occluders)
        for c in cands:
            rows.append([s["stem"], *c["box"], "missing", s["w"], s["h"]])
        cv2.imwrite(str(out_dir / "overlays" / f'{s["stem"]}.jpg'),
                    draw_overlay(s["image"], s["boxes"], cands))
        try:
            rel = Path(s["path"]).resolve().relative_to(ROOT).as_posix()
        except ValueError:
            rel = Path(s["path"]).resolve().as_posix()
        manifest["images"].append({
            "stem": s["stem"],
            "name": s["path"].name,
            "image": rel,
            "width": s["w"], "height": s["h"],
            "objects": [[round(v, 2) for v in b] for b in s["boxes"]],
            "candidates": cands,
        })
    with open(out_dir / "candidates.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["image_name", "x1", "y1", "x2", "y2",
                         "class", "image_width", "image_height"])
        writer.writerows(rows)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    summary = {
        "images": len(sources),
        "objects": sum(len(s["boxes"]) for s in sources),
        "candidates": len(rows),
        "auto_accepted": sum(1 for img in manifest["images"]
                             for c in img["candidates"] if c["auto"]),
        "auto_score": auto_score,
        "used_coco": model is not None,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--images-dir", type=Path, required=True)
    ap.add_argument("--labels-dir", type=Path)
    ap.add_argument("--csv", type=Path, help="SKU110K CSV en vez de labels YOLO.")
    ap.add_argument("--glob", default="*.jpg", help="Patron de imagenes (p.ej. train_*.jpg).")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-coco", action="store_true")
    ap.add_argument("--coco-weights", type=Path, default=DEFAULT_COCO_WEIGHTS)
    ap.add_argument("--auto-score", type=float, default=AUTO_SCORE)
    a = ap.parse_args()

    pattern = a.glob or ""
    if a.labels_dir:
        sources = load_sources(a.images_dir, a.labels_dir, a.limit, pattern)
    elif a.csv:
        sources = load_sources_from_csv(a.images_dir, a.csv, a.limit, pattern)
    else:
        ap.error("da --labels-dir o --csv")

    model = None
    if not a.no_coco:
        from ultralytics import YOLO
        if not a.coco_weights.is_file():
            print(f"ADVERTENCIA: No existe {a.coco_weights}; se continúa sin filtro de oclusores.")
        else:
            model = YOLO(str(a.coco_weights))

    print(json.dumps(run(sources, a.out, model, a.auto_score), indent=2))


if __name__ == "__main__":
    main()
