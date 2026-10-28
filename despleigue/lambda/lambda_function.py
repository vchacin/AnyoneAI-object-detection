"""Lambda de inferencia: imagen -> JSON de detecciones (object / missing).

Tres formas de invocarla:
  1) Directa:     {"image": "<base64>", "conf": 0.25}          -> JSON con detecciones
  2) API GW HTTP: {"body": "<base64>", "isBase64Encoded": true} -> statusCode/body
  3) Evento S3:   imagen nueva en el bucket -> escribe results/<archivo>.json

Configuracion del modelo en model.json; compatible con ONNX raw y NMS embebido.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
import json
import math
import os
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

MODEL_PATH = os.environ.get("MODEL_PATH", "model.onnx")
_config_path = Path(MODEL_PATH).with_suffix(".json")
CONFIG = json.loads(_config_path.read_text(encoding="utf-8")) if _config_path.is_file() else {}
CONF = float(os.environ.get("CONF", str(CONFIG.get("default_conf", 0.25))))
NAMES = CONFIG.get("classes", ["object", "missing"])
INPUT = int(CONFIG.get("imgsz", 640))
MAX_DET = int(CONFIG.get("max_det", 300))
IOU = float(CONFIG.get("iou", 0.7))
OUTPUT_FORMAT = CONFIG.get("output_format", "xyxy_nms")
DYNAMIC_IMAGE_SIZE = bool(CONFIG.get("dynamic_image_size", False))
SUPPORTED_IMGSZ = tuple(int(size) for size in CONFIG.get("supported_imgsz", [INPUT]))

_session: ort.InferenceSession | None = None


@lru_cache(maxsize=1)
def metadata() -> dict:
    path = Path(MODEL_PATH)
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
    return {
        "ok": True, "model_name": os.environ.get("MODEL_NAME", "active"),
        "model_version": os.environ.get("MODEL_VERSION") or digest or "pending",
        "model_sha256": digest,
        "available": bool(digest) and digest == CONFIG.get("onnx_sha256", digest),
        "imgsz": INPUT, "max_det": MAX_DET, "default_conf": CONF, "classes": NAMES,
        "dynamic_image_size": DYNAMIC_IMAGE_SIZE,
        "supported_imgsz": list(SUPPORTED_IMGSZ),
        "source_model": CONFIG.get("source_model"),
        "source_checkpoint_sha256": CONFIG.get("source_checkpoint_sha256"),
    }


def session() -> ort.InferenceSession:
    global _session
    if _session is None:
        options = ort.SessionOptions()
        options.intra_op_num_threads = int(os.environ.get("ORT_NUM_THREADS", "2"))
        options.inter_op_num_threads = 1
        _session = ort.InferenceSession(MODEL_PATH, sess_options=options,
                                       providers=["CPUExecutionProvider"])
    return _session


def _postprocess(out: np.ndarray, conf: float, iou: float) -> np.ndarray:
    if OUTPUT_FORMAT == "xyxy_nms":
        if out.ndim != 3 or out.shape[0] != 1 or out.shape[2] != 6:
            raise ValueError("Salida ONNX incompatible con xyxy_nms")
        return out[0]
    if OUTPUT_FORMAT != "raw_xywh" or out.ndim != 3 or out.shape[:2] != (1, 4 + len(NAMES)):
        raise ValueError("Salida ONNX incompatible con raw_xywh")
    predictions = out[0].T
    classes = predictions[:, 4:].argmax(axis=1)
    scores = predictions[:, 4:].max(axis=1)
    selected = np.flatnonzero((scores >= conf) & np.isfinite(predictions).all(axis=1))
    if not selected.size:
        return np.empty((0, 6), dtype=np.float32)
    # Same candidate bound as Ultralytics NMS; avoid quadratic work at conf=0.
    selected = selected[np.argsort(-scores[selected], kind="stable")[:30000]]
    boxes = predictions[selected, :4].copy()
    boxes[:, :2] -= boxes[:, 2:] / 2
    indices = cv2.dnn.NMSBoxesBatched(boxes.tolist(), scores[selected].tolist(),
                                     classes[selected].tolist(), conf, iou)
    indices = np.asarray(indices, dtype=np.int64).reshape(-1)[:MAX_DET]
    boxes = boxes[indices]
    boxes[:, 2:] += boxes[:, :2]
    return np.column_stack((boxes, scores[selected[indices]], classes[selected[indices]]))


def _decode(raw: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("imagen ilegible (no es JPEG/PNG valido)")
    return img


def _letterbox(img: np.ndarray, size: int = INPUT):
    h, w = img.shape[:2]
    s = min(size / h, size / w)
    nh, nw = int(round(h * s)), int(round(w * s))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    top, left = (size - nh) // 2, (size - nw) // 2
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    canvas[top:top + nh, left:left + nw] = resized
    return canvas, s, left, top


def detect(image_bgr: np.ndarray, conf: float = CONF, iou: float = IOU,
           imgsz: int = INPUT) -> dict:
    t0 = time.perf_counter()
    lb, s, left, top = _letterbox(image_bgr, imgsz)
    blob = lb[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    sess = session()
    out = sess.run(None, {sess.get_inputs()[0].name: blob})[0]
    h, w = image_bgr.shape[:2]
    dets = []
    for x1, y1, x2, y2, c, cls in _postprocess(out, conf, iou):
        if c < conf or c <= 0:
            continue
        x1, x2 = (x1 - left) / s, (x2 - left) / s
        y1, y2 = (y1 - top) / s, (y2 - top) / s
        x1, y1 = max(0.0, float(x1)), max(0.0, float(y1))
        x2, y2 = min(w - 1.0, float(x2)), min(h - 1.0, float(y2))
        if x2 <= x1 or y2 <= y1:
            continue
        i = int(cls)
        if i < 0 or i >= len(NAMES):
            raise ValueError("Clase del modelo no configurada")
        box = [round(x1), round(y1), round(x2), round(y2)]
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        dets.append({
            "box": box,
            "conf": round(float(c), 3),
            "cls": i,
            "label": NAMES[i],
        })
    dets.sort(key=lambda d: -d["conf"])
    return {
        "detections": dets,
        "count": len(dets),
        "counts_by_class": {n: sum(1 for d in dets if d["label"] == n) for n in NAMES},
        "image_size": [w, h],
        "conf_threshold": conf,
        "iou_threshold": iou,
        "imgsz": imgsz,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000),
    }


def handler(event, context):
    event = event or {}
    if event.get("action") == "metadata":
        return metadata()

    # 3) Evento S3: imagen nueva -> JSON al lado del original
    if "Records" in event and event["Records"][0].get("eventSource") == "aws:s3":
        import boto3  # preinstalado en el runtime de Lambda
        rec = event["Records"][0]["s3"]
        bucket, key = rec["bucket"]["name"], rec["object"]["key"]
        s3 = boto3.client("s3")
        raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        result = detect(_decode(raw))
        out_key = f"results/{key.rsplit('/', 1)[-1]}.json"
        s3.put_object(Bucket=bucket, Key=out_key,
                      Body=json.dumps(result, indent=2).encode())
        return {"ok": True, "result_key": out_key,
                "count": result["count"], "elapsed_ms": result["elapsed_ms"]}

    # 2) API Gateway HTTP API (payload v2)
    if "requestContext" in event:
        body = event.get("body") or ""
        raw = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode()
        result = detect(_decode(raw), float(event.get("conf", CONF)),
                        float(event.get("iou", IOU)), int(event.get("imgsz", INPUT)))
        return {"statusCode": 200,
                "headers": {"Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*"},
                "isBase64Encoded": False,
                "body": json.dumps(result)}

    # 1) Invocacion directa
    b64 = event.get("image")
    if not b64:
        return {"ok": False,
                "error": "envia {'image': '<base64>', 'conf': 0.25} o un evento S3"}
    info = metadata()
    if not info["available"]:
        return {"ok": False, "code": "MODEL_NOT_READY"}
    if event.get("model") and event["model"] != info["model_name"]:
        return {"ok": False, "code": "UNKNOWN_MODEL"}
    try:
        threshold = float(event.get("conf", CONF))
        if not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("conf fuera de rango")
        iou = float(event.get("iou", IOU))
        if not math.isfinite(iou) or not 0 <= iou <= 1:
            raise ValueError("iou fuera de rango")
        imgsz = int(event.get("imgsz", INPUT))
        if imgsz not in SUPPORTED_IMGSZ:
            raise ValueError("imgsz no soportado")
        raw = base64.b64decode(b64, validate=True)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError("imagen mayor a 4 MiB")
        image = _decode(raw)
    except (ValueError, TypeError):
        return {"ok": False, "code": "INVALID_INPUT"}
    result = detect(image, threshold, iou, imgsz)
    return {"ok": True, **result, **{key: info[key] for key in
            ("model_name", "model_version", "model_sha256")}}
