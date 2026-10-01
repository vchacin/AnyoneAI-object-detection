"""Entrena y evalúa un brazo (A=object-only, B=object+missing) durante N épocas.

Brazo A: nc=1, validación en test_obj.  Brazo B: nc=2, validación en
test_2cls (object + missing).
Configuración del POC: yolo26s, imgsz 1024, seed 42, batch 1, max_det 750.

  python training/train.py --which A --epochs 35
  python training/train.py --which B --epochs 35 --batch 8
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "training" / "configs"
OUT = ROOT / "training" / "weights"
WEIGHTS = ROOT / "training" / "weights" / "yolo26s.pt"


def tolist(x):
    try:
        return [round(float(v), 5) for v in x]
    except TypeError:
        return round(float(x), 5)


def run(which: str, epochs: int, batch: int = 1, dset: Path | None = None,
        workers: int = 0, patience: int = 100, resume: bool = False,
        init: Path | None = None, name: str | None = None,
        lr0: float | None = None):
    dset = dset or CONFIGS
    data = dset / (f"data_arm_{which.lower()}.yaml" if which else "data.yaml")
    test = dset / ("test_obj.yaml" if which == "A" else "test_2cls.yaml")
    name = name or f"{which}_e{epochs}"
    OUT.mkdir(parents=True, exist_ok=True)

    from ultralytics import YOLO

    started = time.perf_counter()
    last = OUT / name / "weights" / "last.pt"
     # init: continúa desde otros pesos (nueva run); resume: misma run de ultralytics
    model = YOLO(str(init if init else (last if resume and last.exists()
                                        else WEIGHTS)))
    model.train(data=str(data), epochs=epochs, imgsz=1024, seed=42, batch=batch,
                workers=workers, max_det=750, patience=patience,
                resume=resume and not init and last.exists(),
                project=str(OUT), name=name, exist_ok=True,
                 # optimizer=auto ignora lr0; si se especifica explícitamente, respetarlo
                **({"lr0": lr0, "optimizer": "SGD"} if lr0 else {}))
    best = str(Path(model.trainer.best))

    metrics = YOLO(best).val(data=str(test), imgsz=1024, batch=1, workers=0,
                             max_det=750, project=str(OUT), name=f"{name}_val",
                             exist_ok=True)
    box = metrics.box
    summary = {
        "which": which,
        "epochs": epochs,
        "init": str(init) if init else None,
        "lr0": lr0,
        "weights": best,
        "seconds": round(time.perf_counter() - started, 1),
        "names": list(box.names.values()) if hasattr(box, "names") else None,
        "results_dict": {k: round(float(v), 5) for k, v in metrics.results_dict.items()},
        "per_class": {
            "precision": tolist(box.p),
            "recall": tolist(box.r),
            "ap50": tolist(box.ap50),
            "map50_95": tolist(box.maps),
        },
    }
    (OUT / f"{name}_metrics.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--which", choices=["A", "B"], required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--dset", type=Path, default=None,
                    help="raiz alternativa de los configs (default: training/configs)")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--patience", type=int, default=100,
                    help="early stopping sin mejora (100 = off)")
    ap.add_argument("--resume", action="store_true",
                    help="reanuda desde weights/last.pt del mismo name")
    ap.add_argument("--init", type=Path, default=None,
                    help="pesos iniciales (inicia una nueva run que continúa otros pesos)")
    ap.add_argument("--name", type=str, default=None,
                    help="nombre de run (default: <A|B>_e<epochs>)")
    ap.add_argument("--lr0", type=float, default=None,
                    help="lr inicial (usar < 0.01 al continuar pesos)")
    a = ap.parse_args()
    print(json.dumps(run(a.which, a.epochs, a.batch, a.dset, a.workers,
                         a.patience, a.resume, a.init, a.name, a.lr0),
                     indent=2))


if __name__ == "__main__":
    main()
