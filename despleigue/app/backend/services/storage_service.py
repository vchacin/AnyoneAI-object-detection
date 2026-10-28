"""Image storage with local and S3/MinIO backends."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from ..core.config import get_settings

settings = get_settings()

ROOT = Path(__file__).resolve().parents[3]
UPLOAD_ROOT = Path(settings.upload_root)

STORAGE_BACKEND = settings.storage_backend.lower()
S3_BUCKET = settings.s3_bucket
AWS_REGION = settings.s3_region
PRESIGNED_TTL_S = settings.presigned_url_ttl_seconds
S3_ENDPOINT_URL = settings.s3_endpoint_url
S3_ACCESS_KEY = settings.s3_access_key
S3_SECRET_KEY = settings.s3_secret_key


def _key(store_id: str, extension: str) -> str:
    suffix = ".jpg" if extension.lower() in {".jpg", ".jpeg"} else ".png"
    return (Path("stores") / store_id / "inspections" / f"{uuid4()}{suffix}").as_posix()


def _local_put(data: bytes, key: str) -> None:
    target = UPLOAD_ROOT / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _s3_client():
    import boto3
    from botocore.config import Config
    kwargs = {"region_name": AWS_REGION, "config": Config(signature_version="s3v4")}
    if S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = S3_ENDPOINT_URL
    if S3_ACCESS_KEY and S3_SECRET_KEY:
        kwargs["aws_access_key_id"] = S3_ACCESS_KEY
        kwargs["aws_secret_access_key"] = S3_SECRET_KEY
    return boto3.client("s3", **kwargs)


def put(data: bytes, *, store_id: str, extension: str) -> str:
    key = _key(store_id, extension)
    if STORAGE_BACKEND == "s3":
        _s3_client().put_object(Bucket=S3_BUCKET, Key=key, Body=data)
    else:
        _local_put(data, key)
    return key


def get(key: str) -> bytes:
    if STORAGE_BACKEND == "s3":
        response = _s3_client().get_object(Bucket=S3_BUCKET, Key=key)
        return response["Body"].read()
    target = _safe_path(key)
    if not target.is_file():
        raise FileNotFoundError(key)
    return target.read_bytes()


def delete(key: str) -> None:
    if STORAGE_BACKEND == "s3":
        _s3_client().delete_object(Bucket=S3_BUCKET, Key=key)
        return
    target = _safe_path(key)
    if target.is_file():
        target.unlink()


def presign(key: str) -> str | None:
    if STORAGE_BACKEND != "s3":
        return None
    return _s3_client().generate_presigned_url(
        "get_object", Params={"Bucket": S3_BUCKET, "Key": key}, ExpiresIn=PRESIGNED_TTL_S)


def path_for(key: str):
    if STORAGE_BACKEND == "s3":
        return None
    return _safe_path(key)


def _safe_path(key: str) -> Path:
    root = UPLOAD_ROOT.resolve()
    target = (root / key).resolve()
    if root not in target.parents:
        raise ValueError("Invalid storage key")
    return target


def is_local() -> bool:
    return STORAGE_BACKEND != "s3"
