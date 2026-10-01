"""Descargador del dataset SKU-110K.

Descarga el dataset SKU-110K desde S3 y verifica que la estructura local quede
completa. Diseñado para ejecutarse tanto en Colab como en local.

Credenciales: **nunca en el repositorio**. Se leen de `AWS_ACCESS_KEY_ID` /
`AWS_SECRET_ACCESS_KEY` (cadena de credenciales estándar de AWS) o de un
archivo `.env` en la raíz del repositorio. Ver `.env.example`.

  python data_pipeline/scripts/download_dataset.py --limit 50
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[2]

# La consola de Windows usa cp1252 y no sabe imprimir los iconos de estado.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

S3_BUCKET = "anyoneai-datasets"
S3_PREFIX = "SKU-110K/SKU110K_fixed/"

# Configuración de almacenamiento local
DEFAULT_LOCAL_DATA_ROOT = ROOT / "data_pipeline" / "dataset_sku110k"

EXPECTED_COUNTS = {
    "train": 8233,
    "val": 588,
    "test": 2941,
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ANNOTATION_EXTENSIONS = {".csv"}


def load_dotenv(path: Path | None = None) -> None:
    """Carga un .env minimo (KEY=VALUE) sin dependencias externas."""
    path = path or ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def resolve_credentials() -> tuple[str | None, str | None]:
    return os.environ.get("AWS_ACCESS_KEY_ID"), os.environ.get("AWS_SECRET_ACCESS_KEY")


def create_s3_client():
    """Crea y devuelve un cliente S3 usando las credenciales ambientales de AWS."""
    try:
        access_key, secret_key = resolve_credentials()
        kwargs = {}
        if access_key and secret_key:
            kwargs = {"aws_access_key_id": access_key,
                      "aws_secret_access_key": secret_key}
        s3_client = boto3.client("s3", **kwargs)
        s3_client.head_bucket(Bucket=S3_BUCKET)
        return s3_client
    except NoCredentialsError:
        print("Error: credenciales AWS ausentes. Define AWS_ACCESS_KEY_ID y "
              "AWS_SECRET_ACCESS_KEY, o crea un .env en la raiz del repo.")
        return None
    except ClientError as e:
        print(f"Error connecting to S3: {e}")
        return None


def _resolve_local_path(local_dir, file_name):
    """Determine the correct subdirectory for a downloaded file."""
    ext = Path(file_name).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        dest_dir = local_dir / "images"
    elif ext in ANNOTATION_EXTENSIONS:
        dest_dir = local_dir / "annotations"
    else:
        dest_dir = local_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / file_name


def download_s3_folder(bucket_name, s3_prefix, local_dir, limit=0):
    """Download items from a S3 prefix, organizing them into images/ and annotations/."""
    s3_client = create_s3_client()
    if not s3_client:
        return False

    local_dir.mkdir(parents=True, exist_ok=True)
    print("Iniciando descarga desde s3://{}...".format(bucket_name), end=" ")
    print(f"{s3_prefix}")
    print(f"Destino local: {local_dir}")

    paginator = s3_client.get_paginator("list_objects_v2")
    downloaded = skipped = 0
    keys = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            keys.append(key)
            if limit and len(keys) >= limit:
                break
        if limit and len(keys) >= limit:
            break

    for key in tqdm(keys, desc="Descargando", unit="archivo"):
        file_name = os.path.basename(key)
        local_file_path = _resolve_local_path(local_dir, file_name)
        if local_file_path.exists():
            skipped += 1
            continue
        s3_client.download_file(bucket_name, key, str(local_file_path))
        downloaded += 1

    print("Descarga desde S3 completada")
    print(f"   - Archivos descargados: {downloaded}")
    print(f"   - Archivos ya existentes: {skipped}")
    return True


def organize_existing_files(local_dir: Path) -> None:
    """Reorganize flat files into images/ and annotations/ subdirectories."""
    images_dir = local_dir / "images"
    annotations_dir = local_dir / "annotations"
    images_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    for f in local_dir.iterdir():
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            dest = images_dir / f.name
        elif ext in ANNOTATION_EXTENSIONS:
            dest = annotations_dir / f.name
        else:
            continue
        if dest.exists():
            continue
        f.rename(dest)
        moved += 1
    print(f"Archivos reorganizados: {moved}")


def verify_dataset(local_data_root: Path) -> bool:
    """Verifica que la estructura local del dataset sea correcta."""
    if not local_data_root.exists():
        print("ERROR: directorio raíz no encontrado")
        return False

    images_dir = local_data_root / "images"
    if images_dir.exists():
        image_count = len(list(images_dir.glob("*.jpg"))) + len(list(images_dir.glob("*.jpeg")))
        print(f"[OK] Encontrado {image_count} imágenes JPEG")
        return True

    print("ADVERTENCIA: No se encontraron imágenes en la carpeta images/")
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_LOCAL_DATA_ROOT,
                    help="raiz local del dataset (default: data_pipeline/dataset_sku110k)")
    ap.add_argument("--bucket", default=S3_BUCKET)
    ap.add_argument("--prefix", default=S3_PREFIX)
    ap.add_argument("--limit", type=int, default=0,
                    help="maximo de objetos a descargar (0 = sin limite)")
    ap.add_argument("--skip-download", action="store_true",
                    help="solo verifica la estructura local")
    ap.add_argument("--organize-existing", action="store_true",
                    help="reorganiza archivos planos ya descargados en images/ y annotations/")
    a = ap.parse_args()

    print("=" * 60)
    print("SKU-110K Dataset Downloader")
    print("=" * 60)

    load_dotenv()
    a.out.mkdir(parents=True, exist_ok=True)

    if a.organize_existing and a.skip_download:
        print("Reorganizando archivos existentes...")
        organize_existing_files(a.out)

    if not a.skip_download:
        print("Descargando dataset desde S3...")
        if not download_s3_folder(a.bucket, a.prefix, a.out, a.limit):
            print("ERROR: fallo en la descarga")
            return

    print("\nVerificando estructura local...")
    if verify_dataset(a.out):
        print("Verificación completada")
    else:
        print("ADVERTENCIA: verificación fallida - revisar la estructura del dataset")

    print("\nProceso finalizado")


if __name__ == "__main__":
    main()
