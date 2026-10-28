"""Compare ONNX with its source checkpoint, then exercise the backend adapter locally."""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

import cv2
import numpy as np
import torch
import onnxruntime
from ultralytics import YOLO

from export_model import sha256

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent


def compare(result, reference):
    boxes = reference.boxes.xyxy.numpy()
    classes = reference.boxes.cls.numpy().astype(int)
    scores = reference.boxes.conf.numpy()
    assert len(result["detections"]) == len(boxes), "Different detection counts"
    used = set()
    max_delta = 0.0
    max_score_delta = 0.0
    for detection in result["detections"]:
        box = np.asarray(detection["box"])
        possible = [i for i, cls in enumerate(classes) if cls == detection["cls"] and i not in used]
        assert possible, "Different class counts"
        chosen = min(possible, key=lambda i: float(np.max(np.abs(box - boxes[i]))))
        used.add(chosen)
        max_delta = max(max_delta, float(np.max(np.abs(box - boxes[chosen]))))
        max_score_delta = max(max_score_delta, abs(detection["conf"] - float(scores[chosen])))
    assert max_delta <= 1.01, f"Coordinate mismatch: {max_delta} px"
    assert max_score_delta <= 0.002, f"Confidence mismatch: {max_score_delta}"
    return {"max_coordinate_delta_px": round(max_delta, 6),
            "max_confidence_delta": round(max_score_delta, 6)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="*",
                        default=[ROOT / "cctv" / name for name in ["1.jpg", "2.jpg", "11.jpg"]])
    parser.add_argument("--checkpoint", type=Path, default=FOLDER / "yolo26m-auto-120ep.pt")
    args = parser.parse_args()
    manifest = json.loads((FOLDER / "model.json").read_text(encoding="utf-8"))
    assert sha256(args.checkpoint) == manifest["source_checkpoint_sha256"]
    os.environ["MODEL_PATH"] = str(FOLDER / "model.onnx")
    spec = importlib.util.spec_from_file_location("lambda_runtime", ROOT / "aws-lambda/lambda_function.py")
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    assert runtime.metadata()["available"], "ONNX hash does not match manifest"
    torch.set_num_threads(2)
    model = YOLO(str(args.checkpoint))
    report = {"scope": "Local equivalence check, not accuracy evaluation or AWS benchmark",
              "onnxruntime": onnxruntime.__version__, "metadata": runtime.metadata(), "images": []}
    for path in args.images:
        frame = cv2.imread(str(path))
        assert frame is not None, path
        reference = model.predict(frame, imgsz=manifest["imgsz"], rect=False,
                                  max_det=manifest["max_det"], iou=manifest["iou"],
                                  conf=0.25, device="cpu", verbose=False)[0]
        result = runtime.detect(frame, conf=0.25)
        item = {"image": path.name, "reference_count": len(reference.boxes),
                "onnx_count": result["count"], "counts_by_class": result["counts_by_class"],
                "onnx_call_ms": result["elapsed_ms"], **compare(result, reference)}
        report["images"].append(item)
        print(json.dumps(item), flush=True)

    # The SDK transport is simulated; image decoding, inference and adaptation are real.
    os.environ.pop("APP_SECRET_ARN", None)
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite://", INFERENCE_BACKEND="lambda")
    sys.path.insert(0, str(ROOT / "despligue AWS"))
    from app.backend.services import lambda_service

    class LocalLambda:
        def invoke(self, **kwargs):
            body = runtime.handler(json.loads(kwargs["Payload"]), None)
            return {"Payload": io.BytesIO(json.dumps(body).encode())}

    lambda_service.client = lambda: LocalLambda()
    lambda_service.settings.lambda_function_name = "local-validation"
    raw = args.images[-1].read_bytes()
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    height, width = frame.shape[:2]
    report["backend_adapter"] = []
    for conf in [0.1, 0.5]:
        result = lambda_service.predict(raw, conf=conf, model="active", width=width, height=height)
        assert result["conf"] == conf
        assert all(item["class"] in {"object", "missing"} for item in result["detections"])
        assert all(item["confidence"] >= conf for item in result["detections"])
        report["backend_adapter"].append({"conf": conf, "count": len(result["detections"]),
                                          "model_version": result["model_version"]})
    (FOLDER / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Model equivalence and backend adapter OK")


if __name__ == "__main__":
    main()
