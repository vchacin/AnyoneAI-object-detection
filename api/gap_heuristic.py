"""Heurística geométrica de huecos (`missing`).

Módulo sin dependencias de FastAPI ni de Ultralytics: recibe cajas xyxy en
píxeles y devuelve cajas candidatas de producto faltante. Es la única fuente de
verdad de la heurística y es compartida por:

  - `labeling/generate_missing_labels.py`  (etiquetado offline → entrenamiento)
  - `api/inference.py`                     (serving en producción)

Estrategia: los productos de una repisa se apoyan en el mismo estante, por lo
que `y2` es un ancla estable para agruparlos en filas. Dentro de cada fila, el
ancho mediano aproxima el pitch del slot, y todo hueco de ~1 producto se propone
como candidato. Posteriormente se puntúa por apariencia (oscuro y de borde bajo)
para separar "hueco real" de "borde de la repisa".

Los parámetros (`strategy.md`) se calibraron sobre 50 imágenes con ground truth
humano.
"""
from __future__ import annotations

import itertools

import numpy as np

# ---------------------------------------------------------------- parámetros
ROW_TOL = 0.5
GAP_MIN_FRAC = 0.6
MAX_SLOTS = 4
EDGE_GAP_MIN_FRAC = 0.6
EDGE_MAX_SLOTS = 1
EDGE_MIN_ROW = 6
DARK, BRIGHT = 30.0, 90.0
EDGE_LOW, EDGE_HIGH = 2.0, 10.0
AUTO_SCORE = 0.5

# Clases COCO que consideramos oclusores del estante.
OCCLUDERS = {"person", "backpack", "handbag", "suitcase"}


# ---------------------------------------------------------------- geometria

def _h(b):
    return b[3] - b[1]


def _w(b):
    return b[2] - b[0]


def _cy(b):
    return (b[1] + b[3]) / 2


def iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = _w(a) * _h(a) + _w(b) * _h(b) - inter
    return inter / union if union > 0 else 0.0


def center_in(box, container):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return container[0] <= cx <= container[2] and container[1] <= cy <= container[3]


def group_rows(boxes, tol_frac=ROW_TOL):
    """Agrupa en filas por el borde inferior (y2), con rango acotado.

    Los productos de una repisa se apoyan en el mismo estante aunque tengan
    alturas distintas, por lo que y2 es un ancla estable. La segmentación se
    realiza sobre y2 ordenado comparando contra el **mínimo** de la fila (no el
    último), para admitir la inclinación por perspectiva sin fusionar repisas
    contiguas."""
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
    """Ancho típico de producto en una fila (px). Los productos van pegados,
    por lo que el ancho mediano aproxima bien el paso de slot y es más estable
    que las distancias entre centros (que un hueco distorsiona).
    `width_scale` escala ese ancho (calibración de UI: productos más anchos o
    angostos que la mediana)."""
    widths = sorted(_w(b) for b in boxes)
    return float(widths[len(widths) // 2]) * width_scale


def row_slots(boxes, gap_min_frac=GAP_MIN_FRAC, max_slots=MAX_SLOTS,
              width_scale=1.0):
    """Huecos de ~1 producto entre cajas contiguas de una fila.

    La banda vertical del hueco es el promedio de los bordes superior e inferior
    de los dos vecinos (la "diagonal" de la repisa): no se utiliza la altura
    mediana de la fila, ya que haría caer el borde inferior por debajo de la
    repisa."""
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
    la fila. La frontera esperada se estima ajustando y→x sobre TODAS las filas,
    lo que absorbe la perspectiva de manera robusta. Solo se emite si la fila es
    densa (>= min_row_len) y el hueco cabe en max_slots slots, ya que los bordes
    sobre fondo de estante son el principal foco de falsos positivos."""
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


def overlaps_object(box, objects, iou_thr=0.2, cand_frac=0.10, obj_frac=0.15):
    """True si el candidato se superpone a un producto.

    No basta el IoU: un candidato grande que cubre parte de un producto puede
    tener IoU bajo pero solapamiento visible. Se verifica también la fracción del
    candidato cubierta (`cand_frac`) y la fracción del producto cubierta
    (`obj_frac`)."""
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


def predict_missing(boxes, row_tol=ROW_TOL, gap_min_frac=GAP_MIN_FRAC,
                    max_slots=MAX_SLOTS, edges=True, width_scale=1.0,
                    edge_min_row=EDGE_MIN_ROW,
                    edge_gap_min_frac=EDGE_GAP_MIN_FRAC,
                    edge_max_slots=EDGE_MAX_SLOTS):
    """Candidatos de hueco en toda la imagen (interiores + bordes de fila).

    Invariante: un candidato no puede superponerse a una caja de producto (por
    IoU, centro dentro, o fracción de área cubierta). Sin esto, el agrupado de
    filas por perspectiva divide una repisa en dos grupos y el hueco pasa por
    encima de productos del otro grupo (solapamiento visible)."""
    rows = group_rows(boxes, row_tol)
    out = []
    for row in rows:
        out.extend(row_slots(row, gap_min_frac, max_slots, width_scale))
    if edges:
        for row in rows:
            out.extend(row_edges(rows, row, edge_min_row, edge_gap_min_frac,
                                 edge_max_slots, width_scale))
    return [c for c in out if not overlaps_object(c, boxes)]


# ---------------------------------------------------------------- aparición

def appearance(gray, box, dark=DARK, bright=BRIGHT,
                 edge_low=EDGE_LOW, edge_high=EDGE_HIGH):
    """Puntuación [0,1] de "parece fondo de estante" (oscuro y de borde bajo)."""
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


def drop_occluded(candidates, occluders, iou_thr=0.3):
    """Elimina candidatos tapados por personas u objetos (centro dentro o IoU)."""
    return [c for c in candidates
            if not any(center_in(c["box"], o) or iou(c["box"], o) >= iou_thr
                       for o in occluders)]


def score_candidates(gray, boxes, auto_score=AUTO_SCORE, occluders=None):
    """Pipeline completo de la heurística sobre una imagen en escala de grises.

    `boxes` son las cajas de producto en xyxy. Devuelve la lista de candidatos
    ya puntuados, con `auto` indicando los que superan el umbral. Es el punto
    de entrada compartido por el etiquetado offline y la API.
    """
    cands = [{"box": b, **appearance(gray, b)}
             for b in predict_missing(boxes)]
    if occluders:
        cands = drop_occluded(cands, occluders)
    for c in cands:
        c["box"] = [round(v, 2) for v in c["box"]]
        c["auto"] = c["score"] >= auto_score
    return cands
