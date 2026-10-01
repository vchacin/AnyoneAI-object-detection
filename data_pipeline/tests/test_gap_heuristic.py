"""Tests de la heurística geométrica de huecos.

No requieren GPU ni Ultralytics: `api/gap_heuristic.py` es geometría pura.
  pytest data_pipeline/tests/ -v
"""
import numpy as np
import pytest

from api.gap_heuristic import (AUTO_SCORE, appearance, center_in,
                               drop_occluded, group_rows, iou, overlaps_object,
                               predict_missing, row_pitch, row_slots,
                               score_candidates, theilsen)


# ---------------------------------------------------------------- filas
def test_group_rows_separates_shelves():
    top = [[0, 0, 50, 100], [60, 0, 110, 100], [120, 0, 170, 100]]
    bottom = [[0, 300, 50, 400], [60, 300, 110, 400]]
    assert len(group_rows(top + bottom)) == 2


def test_group_rows_absorbs_perspective_tilt():
    # Misma repisa inclinada: y2 aumenta 20px por producto con altura mediana 110,
    # dentro del 50% de tolerancia.
    tilted = [[0, 0, 50, 100], [60, 10, 110, 120], [120, 20, 170, 140]]
    assert len(group_rows(tilted)) == 1


def test_group_rows_splits_beyond_tolerance():
    # y2 aumenta 60px con altura mediana 110 → supera el 50% y corta la repisa.
    steep = [[0, 0, 50, 100], [60, 20, 110, 130], [120, 40, 170, 160]]
    assert len(group_rows(steep)) == 2


def test_group_rows_empty():
    assert group_rows([]) == []


# ---------------------------------------------------------------- pitch y slots
def test_row_pitch_is_median_width():
    assert row_pitch([[0, 0, 50, 100], [50, 0, 100, 100], [100, 0, 200, 100]]) == 50


def test_row_slots_finds_one_gap():
    # Productos de 50px en x=[0,50] y x=[55,105]; el hueco arranca en 105 y
    # mide 55px, casi un producto.
    boxes = [[0, 0, 50, 100], [55, 0, 105, 100], [160, 0, 210, 100]]
    slots = row_slots(boxes)
    assert len(slots) == 1
    x1, y1, x2, y2 = slots[0]
    assert x1 == pytest.approx(105)
    assert x2 == pytest.approx(160)
    assert (y1, y2) == (0, 100)


def test_row_slots_ignores_touching_products():
    assert row_slots([[0, 0, 50, 100], [50, 0, 100, 100]]) == []


def test_row_slots_splits_wide_gap():
    # Hueco de 150 con pitch 50 -> 3 slots.
    boxes = [[0, 0, 50, 100], [200, 0, 250, 100]]
    assert len(row_slots(boxes)) == 3


def test_row_slots_rejects_gap_beyond_max():
    # 10 slots supera MAX_SLOTS=4: no se propone nada.
    boxes = [[0, 0, 50, 100], [550, 0, 600, 100]]
    assert row_slots(boxes) == []


# ---------------------------------------------------------------- invariantes
def test_predict_missing_never_overlaps_an_object():
    boxes = [[0, 0, 50, 100], [60, 0, 110, 100], [300, 0, 350, 100]]
    for c in predict_missing(boxes):
        assert not overlaps_object(c, boxes)


def test_overlaps_object_detects_containment():
    obj = [[0, 0, 100, 100]]
    assert overlaps_object([20, 20, 60, 60], obj)
    assert overlaps_object([50, 50, 200, 200], obj)   # solape parcial grande
    assert not overlaps_object([400, 400, 450, 450], obj)


def test_iou_identity_and_disjoint():
    box = [0, 0, 10, 10]
    assert iou(box, box) == pytest.approx(1.0)
    assert iou(box, [100, 100, 110, 110]) == 0.0


def test_center_in():
    # (10,10) cae justo en la esquina del contenedor [0,0,10,10] -> dentro.
    assert center_in([5, 5, 15, 15], [0, 0, 10, 10]) is True
    # (50,50) está claramente fuera.
    assert center_in([40, 40, 60, 60], [0, 0, 10, 10]) is False


# ---------------------------------------------------------------- apariencia
def test_appearance_scores_dark_flat_region_as_shelf():
    gray = np.full((100, 100), 20, dtype=np.uint8)
    score = appearance(gray, [10, 10, 50, 50])["score"]
    assert score > 0.5, score


def test_appearance_scores_bright_region_as_product():
    gray = np.full((100, 100), 200, dtype=np.uint8)
    score = appearance(gray, [10, 10, 50, 50])["score"]
    assert score < 0.2, score


def test_appearance_clamps_out_of_bounds_box():
    gray = np.full((100, 100), 20, dtype=np.uint8)
    assert appearance(gray, [-50, -50, 500, 500])["score"] >= 0.0


# ---------------------------------------------------------------- occlusores
def test_drop_occluded_removes_covered_candidates():
    cands = [{"box": [10, 10, 40, 40], "score": 0.9},
             {"box": [200, 200, 230, 230], "score": 0.9}]
    occluders = [[0, 0, 60, 60]]   # tapa el primer candidato
    kept = drop_occluded(cands, occluders)
    assert [c["box"] for c in kept] == [[200, 200, 230, 230]]


# ---------------------------------------------------------------- theilsen
def test_theilsen_recovers_slope():
    points = [(0, 0), (1, 2), (2, 4), (3, 6)]
    slope, intercept = theilsen(points)
    assert slope == pytest.approx(2.0)
    assert intercept == pytest.approx(0.0, abs=1e-6)


def test_theilsen_vertical_pairs_give_median_intercept():
    # Sin pares con x distinta no hay pendiente: la recta es horizontal y
    # pasa por la mediana de las y.
    assert theilsen([(5, 0), (5, 10)]) == (0.0, 5.0)


def test_theilsen_single_point():
    assert theilsen([(3, 7)]) == (0.0, 7.0)


# ---------------------------------------------------------------- pipeline
def test_score_candidates_marks_auto_by_threshold():
    gray = np.full((200, 400), 20, dtype=np.uint8)
    boxes = [[10, 100, 60, 200], [62, 100, 112, 200], [250, 100, 300, 200]]
    cands = score_candidates(gray, boxes, auto_score=AUTO_SCORE)
    assert cands, "debería proponer al menos un hueco"
    assert all("auto" in c and "score" in c for c in cands)
    assert any(c["auto"] for c in cands)
    assert all(len(c["box"]) == 4 for c in cands)


def test_score_candidates_no_gap_no_candidates():
    gray = np.full((200, 400), 20, dtype=np.uint8)
    boxes = [[10, 100, 60, 200], [61, 100, 111, 200]]
    assert score_candidates(gray, boxes) == []


def test_score_candidates_applies_occluders():
    gray = np.full((200, 400), 20, dtype=np.uint8)
    boxes = [[10, 100, 60, 200], [62, 100, 112, 200], [250, 100, 300, 200]]
    with_person = score_candidates(gray, boxes, occluders=[[0, 90, 400, 210]])
    without = score_candidates(gray, boxes)
    assert len(with_person) <= len(without)
