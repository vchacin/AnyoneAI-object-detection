"""Verificación de integridad de imágenes.

Recorre un directorio, abre cada imagen con PIL y genera un reporte con las
imagenes corruptas. Se ejecuta antes del entrenamiento para evitar arrastrar
imagenes defectuosas al dataset.

  python data_pipeline/scripts/clean_images.py --input data_pipeline/dataset_sku110k/images
  python data_pipeline/scripts/clean_images.py --input data_pipeline/dataset_sku110k/images --delete
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageFile
from tqdm import tqdm

# La consola de Windows usa cp1252 y no sabe imprimir los iconos de estado.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ImageFile.LOAD_TRUNCATED_IMAGES = False

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff")

DEFAULT_REPORT = Path(__file__).resolve().parents[1] / "revision_imagenes.txt"


def verify_integrity(input_dir: Path, report_path: Path = DEFAULT_REPORT,
                     delete: bool = False) -> dict:
    """Escanea `input_dir` y reporta las imagenes corruptas.

    Devuelve un dict con el conteo. Con `delete=True` ademas borra las imagenes
    que fallan (deja el reporte como registro).
    """
    input_dir = Path(input_dir)
    report_path = Path(report_path)

    print(f"Directorio de búsqueda: {input_dir.resolve()}")
    files = [f for f in input_dir.rglob("*")
             if f.suffix.lower() in VALID_EXTENSIONS]

    print(f"Total de imágenes encontradas: {len(files)}")
    if not files:
        print("ADVERTENCIA: No se encontró ninguna imagen. Revisar la ruta del directorio.")
        return {"total": 0, "corrupt": 0, "report": str(report_path)}

    corrupt = []
    for path in tqdm(files, desc="Verificando integridad"):
        try:
            with Image.open(path) as img:
                img.verify()
            with Image.open(path) as img:
                img.load()
        except Exception as exc:  # noqa: BLE001 - reportamos cualquier fallo
            corrupt.append((path.resolve(), str(exc)))

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("# Reporte de imágenes corruptas\n")
        for path, error in corrupt:
            fh.write(f"{path} | Error: {error}\n")

    if delete:
        for path, _ in corrupt:
            try:
                path.unlink()
            except OSError as exc:
                print(f"⚠️  No se pudo borrar {path}: {exc}")

    print("\nProceso completado.")
    print(f"   - Imágenes dañadas encontradas: {len(corrupt)}")
    print(f"   - Informe guardado en: {report_path.resolve()}")
    return {"total": len(files), "corrupt": len(corrupt), "report": str(report_path)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True,
                    help="directorio con las imagenes a verificar")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--delete", action="store_true",
                    help="borrar las imagenes corruptas tras reportarlas")
    a = ap.parse_args()
    verify_integrity(a.input, a.report, a.delete)


if __name__ == "__main__":
    main()
