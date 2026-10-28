"""Export the chosen checkpoint without modifying it or the legacy ONNX model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, nargs="?",
                        default=Path(__file__).with_name("yolo26m-auto-120ep.pt"))
    parser.add_argument("--dynamic", action="store_true",
                        help="Export one ONNX graph that accepts several square input sizes")
    parser.add_argument("--output", type=Path,
                        help="Output path (defaults to model.onnx or model-dynamic.onnx)")
    args = parser.parse_args()
    source = args.checkpoint.resolve(strict=True)
    output = (args.output.resolve() if args.output else
              Path(__file__).with_name("model-dynamic.onnx" if args.dynamic else "model.onnx"))

    import onnx
    import onnxruntime as ort
    import torch
    import ultralytics
    import numpy as np
    from ultralytics import YOLO

    torch.set_num_threads(2)
    model = YOLO(str(source))
    training = model.ckpt.get("train_args", {})
    imgsz = int(training.get("imgsz", 1280))
    max_det = int(training.get("max_det", 700))
    iou = float(training.get("iou", 0.7))
    classes = ["missing" if name.lower() == "missing1" else name.lower()
               for _, name in sorted(model.names.items())]
    if model.task != "detect" or set(classes) != {"object", "missing"}:
        raise ValueError("El servicio requiere un detector de object/missing")
    if len(classes) != 2:
        raise ValueError("El servicio requiere exactamente dos clases")
    exported = Path(model.export(format="onnx", imgsz=imgsz, batch=1,
                                device="cpu", half=False, dynamic=args.dynamic,
                                simplify=False, opset=17, nms=None))
    graph = onnx.load(str(exported))
    onnx.checker.check_model(graph)

    def shape(value_info):
        return [dim.dim_value or dim.dim_param or None
                for dim in value_info.type.tensor_type.shape.dim]

    input_shape = shape(graph.graph.input[0])
    output_shape = shape(graph.graph.output[0])
    if (len(input_shape) != 4 or input_shape[1] != 3 or len(output_shape) != 3 or
            (not args.dynamic and (input_shape[0] != 1 or output_shape[:2] != [1, 6]))):
        raise ValueError(f"Exportacion raw incompatible: {input_shape} -> {output_shape}")
    if args.dynamic:
        expected_anchors = (imgsz // 8) ** 2 + (imgsz // 16) ** 2 + (imgsz // 32) ** 2
        if input_shape[2:] == [imgsz, imgsz] or output_shape[2] == expected_anchors:
            raise ValueError("ONNX no conserva dimensiones dinamicas")
        runtime = ort.InferenceSession(str(exported), providers=["CPUExecutionProvider"])
        input_name = runtime.get_inputs()[0].name
        for size in [640, 960, 1280, 1600, 1920]:
            output_array = runtime.run(None, {input_name: np.zeros((1, 3, size, size), dtype=np.float32)})[0]
            anchors = (size // 8) ** 2 + (size // 16) ** 2 + (size // 32) ** 2
            if output_array.shape != (1, 6, anchors):
                raise ValueError(f"ONNX dinamico incompatible en {size}px: {output_array.shape}")
    elif input_shape != [1, 3, imgsz, imgsz] or output_shape[2] != (imgsz // 8) ** 2 + (imgsz // 16) ** 2 + (imgsz // 32) ** 2:
        raise ValueError(f"Exportacion estatica incompatible: {input_shape} -> {output_shape}")
    shutil.copy2(exported, output)
    if exported != output:
        exported.unlink(missing_ok=True)

    manifest = {
        "source_model": source.stem,
        "source_checkpoint_sha256": sha256(source),
        "onnx_sha256": sha256(output),
        "imgsz": imgsz, "max_det": max_det, "iou": iou,
        "default_conf": 0.25, "classes": classes,
        "output_format": "raw_xywh", "input_shape": input_shape,
        "output_shape": output_shape,
        "dynamic_image_size": args.dynamic,
        "supported_imgsz": [640, 960, 1280, 1600, 1920] if args.dynamic else [imgsz],
        "ultralytics_version": ultralytics.__version__,
        "torch_version": torch.__version__, "onnx_version": onnx.__version__,
    }
    output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
