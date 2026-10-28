"""Class aliases must agree across detections, counts and gap inputs."""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch

from app.backend.services.inference_service import Detector


class DetectionClassAliasesTest(unittest.TestCase):
    def test_sahi_receives_parameters_and_normalizes_classes(self):
        detector = SimpleNamespace(
            model=object(), _lock=threading.Lock(), conf=0.25, iou=0.7, imgsz=640,
            max_det=750, device="cpu", coco=None, auto_score=0.5,
            gap_mode="model", model_name="test", model_version="test",
        )
        records = [([1, 2, 8, 9], 0.8, "missing1"), ([10, 2, 18, 9], 0.9, "object")]
        with patch("app.backend.services.sahi_inference.predict_sliced", return_value=records) as sliced, \
             patch("app.backend.services.inference_service.score_candidates", return_value=[]):
            result = Detector.predict(detector, np.zeros((64, 64, 3), dtype=np.uint8), conf=0.3, iou=0.5, sahi=True, imgsz=960)
        self.assertEqual(sliced.call_args.kwargs["conf"], 0.3)
        self.assertEqual(sliced.call_args.kwargs["iou"], 0.5)
        self.assertEqual(sliced.call_args.kwargs["imgsz"], 960)
        self.assertEqual(result["imgsz"], 960)
        self.assertEqual(result["missing"][0]["class"], "missing")
        self.assertEqual(result["objects"][0]["class"], "object")
        self.assertTrue(result["sahi"])

    def test_iou_override_is_passed_to_model_without_changing_default(self):
        calls = []
        detector = SimpleNamespace(
            model=SimpleNamespace(predict=lambda *args, **kwargs: calls.append(kwargs) or [SimpleNamespace(names={}, boxes=None)]),
            _lock=threading.Lock(), conf=0.25, iou=0.7, imgsz=640,
            max_det=750, device="cpu", coco=None, auto_score=0.5,
            gap_mode="model", model_name="test", model_version="test",
        )
        with patch("app.backend.services.inference_service.score_candidates", return_value=[]):
            result = Detector.predict(detector, np.zeros((64, 64, 3), dtype=np.uint8), conf=0.3, iou=0.5, imgsz=960)
            Detector.predict(detector, np.zeros((64, 64, 3), dtype=np.uint8))
        self.assertEqual((calls[0]["conf"], calls[0]["iou"]), (0.3, 0.5))
        self.assertEqual(calls[1]["iou"], 0.7)
        self.assertEqual(calls[0]["imgsz"], 960)
        self.assertEqual(calls[1]["imgsz"], 640)
        self.assertEqual(detector.imgsz, 640)
        self.assertEqual(result["iou"], 0.5)

    def test_missing_aliases_are_normalized_before_grouping(self):
        boxes = SimpleNamespace(
            xyxy=torch.tensor([[0, 0, 10, 10], [20, 0, 30, 10], [40, 0, 50, 10]]),
            cls=torch.tensor([0, 1, 2]),
            conf=torch.tensor([0.9, 0.8, 0.7]),
        )
        result = SimpleNamespace(
            names={0: "object", 1: "missing", 2: "missing1"}, boxes=boxes,
        )
        detector = SimpleNamespace(
            model=SimpleNamespace(predict=lambda *args, **kwargs: [result]),
            _lock=threading.Lock(), conf=0.25, iou=0.7, imgsz=640,
            max_det=750, device="cpu", coco=None, auto_score=0.5,
            gap_mode="model", model_name="test", model_version="test",
        )
        with patch("app.backend.services.inference_service.score_candidates", return_value=[]) as gaps:
            prediction = Detector.predict(detector, np.zeros((64, 64, 3), dtype=np.uint8))

        self.assertEqual([item["class"] for item in prediction["objects"]], ["object"])
        self.assertEqual([item["class"] for item in prediction["missing"]], ["missing", "missing"])
        self.assertEqual(len(prediction["detections"]), 3)
        self.assertEqual(gaps.call_args.args[1], [[0.0, 0.0, 10.0, 10.0]])


if __name__ == "__main__":
    unittest.main()
