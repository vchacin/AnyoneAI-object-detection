"""Exporta el dataset etiquetado a las dos configuraciones de entrenamiento.

- **Brazo A** (`nc=1`, solo `object`): listo para el detector base de productos.
- **Brazo B** (`nc=2`, `object` + `missing`): añade las cajas de hueco generadas
  por la heurística geométrica (`api/gap_heuristic.py`).

Escribe un `data.yaml` por brazo en `training/configs/` apuntando a la ruta
absoluta del dataset, de modo que funcione igual en Colab y en local sin
modificaciones manuales. El notebook `training/pipeline_completo.ipynb`
regenera el yaml con su propio `ROOT_DIR` al ejecutarse en Colab.

  python labeling/export_empty_class/export_empty_class.py \
    --yolo-dir data_pipeline/dataset_sku110k/yolo/train \
    --images-dir data_pipeline/dataset_sku110k/images \
    --candidates data_pipeline/dataset_sku110k/missing_poc/candidates.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml
from tqdm import tqdm

# La consola de Windows utiliza cp1252 y no admite caracteres Unicode de estado.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = ROOT / "training" / "configs"

ARM_A_NAMES = ["object"]
ARM_B_NAMES = ["object", "missing"]
MISSING_CLASS_ID = 1


def load_candidates(candidates_csv: Path) -> dict[str, list[list[float]]]:
    """Lee `candidates.csv` y agrupa las cajas por imagen."""
    grouped: dict[str, list[list[float]]] = {}
    with open(candidates_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = Path(row["image_name"]).stem
            grouped.setdefault(key, []).append(
                [float(row["x1"]), float(row["y1"]),
                 float(row["x2"]), float(row["y2"])])
    return grouped


def xyxy_to_yolo(box, width, height) -> str | None:
    x1, y1, x2, y2 = box
    if width <= 0 or height <= 0 or x2 <= x1 or y2 <= y1:
        return None
    cx = ((x1 + x2) / 2) / width
    cy = ((y1 + y2) / 2) / height
    return (f"{MISSING_CLASS_ID} {cx:.6f} {cy:.6f} "
            f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}")


def export_arm_b(labels_dir: Path, out_labels_dir: Path,
                 candidates_csv: Path, write_images: Path | None) -> dict:
    """Copia los labels de `object` y añade las cajas de `missing` (clase 1)."""
    candidates = load_candidates(candidates_csv)
    out_labels_dir.mkdir(parents=True, exist_ok=True)
    labels_dir, out_labels_dir = Path(labels_dir), Path(out_labels_dir)

    label_files = sorted(labels_dir.glob("*.txt"))
    enriched = 0
    for label_path in tqdm(label_files, desc="Arm B (object+missing)", unit="img"):
        lines = label_path.read_text(encoding="utf-8").splitlines()
        width = height = None
        if write_images:
            img = write_images / f"{label_path.stem}.jpg"
            if not img.is_file():
                img = write_images / f"{label_path.stem}.png"
            if img.is_file():
                from PIL import Image
                with Image.open(img) as im:
                    width, height = im.size

        extra = []
        for box in candidates.get(label_path.stem, []):
            if width is None:
                # Sin dimensiones no se puede normalizar: el llamador debe
                # pasar --images-dir. Saltamos en vez de emitir basura.
                continue
            line = xyxy_to_yolo(box, width, height)
            if line:
                extra.append(line)

        payload = [line for line in lines if line.strip()] + extra
        (out_labels_dir / label_path.name).write_text(
            "\n".join(payload) + "\n", encoding="utf-8")
        enriched += bool(extra)

    print(f"[OK] Brazo B: {enriched}/{len(label_files)} labels con cajas `missing`")
    return {"labels": len(label_files), "with_missing": enriched}


def write_yaml(name: str, root: Path, split_dirs: dict[str, str], names: list[str]) -> Path:
    """Escribe un `data.yaml` apuntando a la ruta ABSOLUTA del dataset.

    Ultralytics resuelve un `path` relativo contra la carpeta del propio yaml
    (o sea `training/configs/`), no contra la raiz del repo, asi que relativo
    sería silenciosamente incorrecto. El notebook `pipeline_completo.ipynb`
    regenera el yaml con su propio `ROOT_DIR` al ejecutarse en Colab.
    """
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "path": Path(root).resolve().as_posix(),
        "train": split_dirs["train"],
        "val": split_dirs["val"],
        "test": split_dirs.get("test", split_dirs["val"]),
        "nc": len(names),
        "names": names,
    }
    path = CONFIGS_DIR / name
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")
    print(f"[OK] {path.relative_to(ROOT)} -> nc={len(names)} names={names}")
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yolo-dir", type=Path, required=True,
                    help="raiz del dataset YOLO (contiene labels/ e images/)")
    ap.add_argument("--candidates", type=Path,
                    help="candidates.csv de generate_missing_labels.py (para Arm B)")
    ap.add_argument("--images-dir", type=Path,
                    help="carpeta de imagenes; necesario para normalizar las cajas "
                         "de `missing` en Arm B")
    ap.add_argument("--arm", choices=["A", "B", "both"], default="both")
    a = ap.parse_args()

    yolo_dir = Path(a.yolo_dir)
    labels_dir = yolo_dir / "labels"
    images_dir = Path(a.images_dir) if a.images_dir else yolo_dir / "images"
    if not labels_dir.is_dir():
        ap.error(f"Directorio no encontrado: {labels_dir}")

    splits = {"train": "images", "val": "images", "test": "images"}

    if a.arm in ("A", "both"):
        write_yaml("data_arm_a.yaml", yolo_dir, splits, ARM_A_NAMES)
        write_yaml("test_obj.yaml", yolo_dir, splits, ARM_A_NAMES)

    if a.arm in ("B", "both"):
        if not a.candidates:
            ap.error("Arm B necesita --candidates (candidates.csv)")
        if not a.images_dir:
            ap.error("Arm B necesita --images-dir para normalizar las cajas de `missing`")
        out_labels = yolo_dir.parent / f"{yolo_dir.name}_armB" / "labels"
        export_arm_b(labels_dir, out_labels, Path(a.candidates), images_dir)
        write_yaml("data_arm_b.yaml", out_labels.parent, splits, ARM_B_NAMES)
        write_yaml("test_2cls.yaml", out_labels.parent, splits, ARM_B_NAMES)


if __name__ == "__main__":
    main()
