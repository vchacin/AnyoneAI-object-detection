"""Fase 1: generar etiquetado de `missing` por geometria sobre cajas de objeto.

No hay modelo entrenado: agrupa las cajas de objeto en filas, mide el pitch por
fila y propone huecos de ~1 producto de ancho. 

Ojo, espera que existe el modelo yolo26n.pt, que usé para detección depersonas, columnas, etc. 


Correr (venv reutilizado de experiment/):

  experiment/.venv/Scripts/python.exe predict.py ^
    --images-dir ../experiment/data/poc500/test/images ^
    --labels-dir ../experiment/data/poc500/test/labels ^
    --out out/poc50
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
from pathlib import Path

import cv2
import numpy as np

# Clases COCO que consideramos oclusores del estante.
OCCLUDERS = {"person", "backpack", "handbag", "suitcase"}

# Knobs (ver estrategia.md). Calibrados sobre las 50 con GT humano (tune.py).
ROW_TOL = 0.5
GAP_MIN_FRAC = 0.6
MAX_SLOTS = 4
EDGE_GAP_MIN_FRAC = 0.6
EDGE_MAX_SLOTS = 1
EDGE_MIN_ROW = 6
DARK, BRIGHT = 30.0, 90.0
EDGE_LOW, EDGE_HIGH = 2.0, 10.0
AUTO_SCORE = 0.5


# ---------------------------------------------------------------- geometria

def _h(b):
    return b[3] - b[1]


def _w(b):
    return b[2] - b[0]


def _cy(b):
    return (b[1] + b[3]) / 2


def group_rows(boxes, tol_frac=ROW_TOL):
    """Filas por el borde inferior (y2), con span acotado.

    Los productos de una repisa se apoyan en el mismo estante aunque tengan
    alturas distintas, así que y2 es un ancla estable. Se segmenta sobre y2
    ordenado comparando contra el **mínimo** de la fila (no el último), para
    admitir la inclinación por perspectiva sin fusionar repisas contiguas."""
    if not boxes:
        return []
    ordered = sorted(boxes, key=lambda b: b[3])
    med_h = float(np.median([_h(b) for b in ordered]))
    rows = [[ordered[0]]]
    for b in ordered[1:]:
        if b[3] - rows[-1][0][3] <= tol_frac * med_h:
            rows[-1].append(b)
        else:
            rows.append([b])
    return rows


def row_pitch(boxes, width_scale=1.0):
    """Ancho tipico de producto en una fila (px). Los productos van pegados, así
    que el ancho mediano aproxima bien el paso de slot y es más estable que las
    distancias entre centros (que un hueco infla). `width_scale` escala ese
    ancho (calibración de UI: productos más anchos/angostos que la mediana)."""
    widths = sorted(_w(b) for b in boxes)
    return float(widths[len(widths) // 2]) * width_scale


def row_slots(boxes, gap_min_frac=GAP_MIN_FRAC, max_slots=MAX_SLOTS,
              width_scale=1.0):
    """Huecos de ~1 producto entre cajas contiguas de una fila.

    La banda vertical del hueco es el promedio de topes y fondos de los dos
    vecinos (la "diagonal" de la repisa): no se usa la altura mediana de la fila,
    que hacía que el borde inferior cayera por debajo de la repisa."""
    if len(boxes) < 2:
        return []
    pitch = row_pitch(boxes, width_scale)
    if pitch <= 0:
        return []
    shelf = sorted(boxes, key=lambda b: b[0])
    out = []
    for left, right in zip(shelf, shelf[1:]):
        gap = right[0] - left[2]
        if gap < gap_min_frac * pitch:
            continue
        n = int(np.floor(gap / pitch + 0.5))
        if n < 1 or n > max_slots:
            continue
        slot_w = gap / n
        y1 = (left[1] + right[1]) / 2
        y2 = (left[3] + right[3]) / 2
        if y2 <= y1:
            continue
        for i in range(n):
            out.append([left[2] + i * slot_w, y1, left[2] + (i + 1) * slot_w, y2])
    return out


def predict_missing(boxes, row_tol=ROW_TOL, gap_min_frac=GAP_MIN_FRAC,
                    max_slots=MAX_SLOTS, edges=True, width_scale=1.0,
                    edge_min_row=EDGE_MIN_ROW,
                    edge_gap_min_frac=EDGE_GAP_MIN_FRAC,
                    edge_max_slots=EDGE_MAX_SLOTS):
    """Candidatos de hueco en toda la imagen (interiores + bordes de fila).

    Invariante: un candidato no puede solapar una caja de producto (por IoU,
    centro dentro, o fraccion de area cubierta). Sin esto, el agrupado de filas
    por perspectiva parte una repisa en dos grupos y el hueco pasa por encima de
    productos del otro grupo (overlap visible)."""
    rows = group_rows(boxes, row_tol)
    out = []
    for row in rows:
        out.extend(row_slots(row, gap_min_frac, max_slots, width_scale))
    if edges:
        for row in rows:
            out.extend(row_edges(rows, row, edge_min_row, edge_gap_min_frac,
                                 edge_max_slots, width_scale))
    return [c for c in out if not overlaps_object(c, boxes)]


def overlaps_object(box, objects, iou_thr=0.2, cand_frac=0.10, obj_frac=0.15):
    """True si el candidato se sienta sobre un producto.

    No basta IoU: un candidato grande que cubre parte de un producto tiene IoU
    bajo pero solape visible. Se mira tambien la fraccion del candidato cubierta
    (cand_frac) y la fraccion del producto cubierta (obj_frac)."""
    ab = _w(box) * _h(box)
    if ab <= 0:
        return False
    for o in objects:
        if center_in(box, o):
            return True
        iw = max(0.0, min(box[2], o[2]) - max(box[0], o[0]))
        ih = max(0.0, min(box[3], o[3]) - max(box[1], o[1]))
        inter = iw * ih
        if inter <= 0:
            continue
        ao = _w(o) * _h(o)
        if (iou(box, o) > iou_thr or inter / ab > cand_frac
                or (ao > 0 and inter / ao > obj_frac)):
            return True
    return False


def theilsen(points):
    """Ajuste robusto y=f(x) (mediana de pendientes). Resistente a filas cortas."""
    if len(points) < 2:
        return 0.0, (points[0][1] if points else 0.0)
    slopes = [(y2 - y1) / (x2 - x1)
              for (x1, y1), (x2, y2) in itertools.combinations(points, 2) if x2 != x1]
    slope = float(np.median(slopes)) if slopes else 0.0
    intercept = float(np.median([y - slope * x for x, y in points]))
    return slope, intercept


def row_center_y(row):
    return float(np.median([_cy(b) for b in row]))


def row_edges(rows, row, min_row_len=EDGE_MIN_ROW,
              gap_min_frac=EDGE_GAP_MIN_FRAC, max_slots=EDGE_MAX_SLOTS,
              width_scale=1.0):
    """Huecos de borde: completa el ancho esperado del estante en los extremos de
    la fila. La frontera esperada se estima ajustando y->x sobre TODAS las filas,
    lo que absorbe la perspectiva de manera robusta. ponytail: sólo se emiten si
    la fila es densa (>= min_row_len) y el hueco cabe en max_slots slots, porque
    los bordes sobre fondo de estante son el principal foco de falsos positivos."""
    if len(row) < min_row_len or len(rows) < 3:
        return []
    pitch = row_pitch(row, width_scale)
    if pitch <= 0:
        return []
    shelf = sorted(row, key=lambda b: b[0])
    cy = row_center_y(row)
    left_pts = [(row_center_y(r), min(b[0] for b in r)) for r in rows]
    right_pts = [(row_center_y(r), max(b[2] for b in r)) for r in rows]
    slope_l, icept_l = theilsen(left_pts)
    slope_r, icept_r = theilsen(right_pts)
    rmin = min(b[0] for b in row)
    rmax = max(b[2] for b in row)
    out = []
    for anchor, expected, sign, edge_box in ((rmin, slope_l * cy + icept_l, -1, shelf[0]),
                                             (rmax, slope_r * cy + icept_r, 1, shelf[-1])):
        gap = sign * (expected - anchor)
        if gap < gap_min_frac * pitch or gap > (max_slots + 0.5) * pitch:
            continue
        y1, y2 = edge_box[1], edge_box[3]
        for i in range(max_slots):
            a = anchor + sign * (i + 1) * pitch
            b = anchor + sign * i * pitch
            out.append([min(a, b), y1, max(a, b), y2])
    return out


# ---------------------------------------------------------------- apariencia

def appearance(gray, box, dark=DARK, bright=BRIGHT,
               edge_low=EDGE_LOW, edge_high=EDGE_HIGH):
    """Score [0,1] de 'parece fondo de estante' (oscuro y de borde bajo)."""
    x1, y1, x2, y2 = (int(round(v)) for v in box)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(gray.shape[1], x2), min(gray.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return {"mean": None, "edge": None, "score": 0.0}
    crop = gray[y1:y2, x1:x2].astype(np.float32)
    if crop.shape[0] < 2 or crop.shape[1] < 2:
        return {"mean": round(float(crop.mean()), 2) if crop.size else None,
                "edge": None, "score": 0.0}
    gy, gx = np.gradient(crop)
    mean = float(crop.mean())
    edge = float(np.sqrt(gx * gx + gy * gy).mean())
    b = float(np.clip((bright - mean) / (bright - dark), 0.0, 1.0))
    e = float(np.clip((edge_high - edge) / (edge_high - edge_low), 0.0, 1.0))
    return {"mean": round(mean, 2), "edge": round(edge, 2),
            "score": round(min(b, e), 3)}


def iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = _w(a) * _h(a) + _w(b) * _h(b) - inter
    return inter / union if union > 0 else 0.0


def center_in(box, container):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return container[0] <= cx <= container[2] and container[1] <= cy <= container[3]


def drop_occluded(candidates, occluders, iou_thr=0.3):
    """Quita candidatos tapados por personas/objetos (centro dentro o solape)."""
    return [c for c in candidates
            if not any(center_in(c["box"], o) or iou(c["box"], o) >= iou_thr
                       for o in occluders)]


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


# ---------------------------------------------------------------- pipeline

def load_sources(images_dir, labels_dir, limit):
    sources = []
    images = sorted(Path(images_dir).glob("*.jpg")) + sorted(Path(images_dir).glob("*.png"))
    if limit:
        images = images[:limit]
    for img in images:
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


def run(sources, out_dir, model=None, auto_score=AUTO_SCORE):
    out_dir = Path(out_dir)
    final_root = Path(__file__).resolve().parent.parent
    (out_dir / "overlays").mkdir(parents=True, exist_ok=True)
    rows, manifest = [], {"auto_score": auto_score, "images": []}
    for s in sources:
        gray = cv2.cvtColor(s["image"], cv2.COLOR_BGR2GRAY)
        cands = [{"box": b, **appearance(gray, b)}
                 for b in predict_missing(s["boxes"])]
        if model is not None:
            cands = drop_occluded(cands, coco_occluders(model, s["path"]))
        for c in cands:
            c["box"] = [round(v, 2) for v in c["box"]]
            c["auto"] = c["score"] >= auto_score
            rows.append([s["stem"], *c["box"], "missing", s["w"], s["h"]])
        cv2.imwrite(str(out_dir / "overlays" / f'{s["stem"]}.jpg'),
                    draw_overlay(s["image"], s["boxes"],
                                 [{**c, "box": c["box"]} for c in cands]))
        manifest["images"].append({
            "stem": s["stem"],
            "name": s["path"].name,
            "image": Path(s["path"]).resolve().relative_to(final_root).as_posix(),
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
    ap.add_argument("--coco-weights", type=Path,
                    default=Path(__file__).resolve().parent.parent / "weights" / "yolo26n.pt")
    ap.add_argument("--auto-score", type=float, default=AUTO_SCORE)
    a = ap.parse_args()

    if a.labels_dir:
        sources = load_sources(a.images_dir, a.labels_dir, a.limit)
    elif a.csv:
        images = sorted(Path(a.images_dir).glob(a.glob))
        if a.limit:
            images = images[:a.limit]
        data = read_sku_csv(a.csv, wanted={p.name for p in images})
        sources = []
        for img in images:
            if img.name not in data:
                continue
            image = cv2.imread(str(img))
            if image is None:
                continue
            h, w = image.shape[:2]
            sources.append({"stem": img.stem, "path": img, "image": image,
                            "w": w, "h": h, "boxes": data[img.name]["boxes"]})
    else:
        ap.error("da --labels-dir o --csv")

    model = None
    if not a.no_coco:
        from ultralytics import YOLO
        model = YOLO(str(a.coco_weights))

    print(json.dumps(run(sources, a.out, model, a.auto_score), indent=2))


if __name__ == "__main__":
    main()
