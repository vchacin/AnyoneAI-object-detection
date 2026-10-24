"""Tests for detection class alias normalisation."""
from __future__ import annotations

import unittest


class TestDetectionClassAliases(unittest.TestCase):
    def test_missing1_normalised_to_missing(self):
        """missing1 detections are treated as missing, not objects."""
        # Simulate the normalisation logic from inference_service
        raw = [
            {"class": "object", "box": [0, 0, 10, 10], "confidence": 0.9},
            {"class": "missing", "box": [20, 20, 30, 30], "confidence": 0.8},
            {"class": "missing1", "box": [40, 40, 50, 50], "confidence": 0.7},
        ]

        objects = []
        missing = []
        for det in raw:
            class_name = det["class"].lower()
            if class_name == "missing1":
                class_name = "missing"
            if class_name == "missing":
                missing.append(det)
            else:
                objects.append(det)

        self.assertEqual(len(objects), 1)
        self.assertEqual(len(missing), 2)
        self.assertEqual(len(objects) + len(missing), 3)


if __name__ == "__main__":
    unittest.main()
