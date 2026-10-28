"""Application settings loaded from environment variables."""
from functools import lru_cache
from pathlib import Path
import json
import os
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    environment: Literal["development", "production"] = "development"
    inference_backend: Literal["local", "lambda", "runpod"] = "local"
    lambda_function_name: str = ""
    lambda_read_timeout_seconds: int = Field(70, ge=1, le=950)
    aws_region: str = "us-east-1"
    runpod_endpoint_id: str = ""
    runpod_api_key: str = ""
    runpod_timeout_seconds: int = Field(70, ge=1, le=950)
    migration_database_url: str | None = None
    # --- Database -----------------------------------------------------------
    database_url: str = "sqlite:///./app/data/detections.db"

    # --- Auth ---------------------------------------------------------------
    jwt_secret: str = Field("change-me-in-development-secret-32", min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(15, validation_alias=AliasChoices("ACCESS_TOKEN_MINUTES", "JWT_ACCESS_TTL_MINUTES"))
    refresh_token_days: int = Field(30, validation_alias=AliasChoices("REFRESH_TOKEN_DAYS", "JWT_REFRESH_TTL_DAYS"))
    first_superadmin_email: str | None = None
    first_superadmin_password: str | None = None

    # --- CORS / docs --------------------------------------------------------
    cors_origins: str = ""
    enable_docs: bool = True

    # --- Image upload limits ------------------------------------------------
    max_upload_mb: int = Field(10, validation_alias=AliasChoices("MAX_UPLOAD_MB", "MAX_IMAGE_MB"))
    max_image_width: int = Field(10000, validation_alias=AliasChoices("MAX_IMAGE_WIDTH", "MAX_IMAGE_RESOLUTION"))
    max_image_height: int = Field(10000, validation_alias=AliasChoices("MAX_IMAGE_HEIGHT", "MAX_IMAGE_RESOLUTION"))

    # --- Storage backend ----------------------------------------------------
    # "local" uses the filesystem under ``UPLOAD_ROOT``.
    # "s3"   uses an S3-compatible object store (AWS, MinIO, Neon S3, etc.).
    storage_backend: str = Field("local", validation_alias=AliasChoices("STORAGE_BACKEND"))
    upload_root: str = Field(str(ROOT / "app" / "data" / "uploads"))

    # S3 configuration.  boto3 auto-discovers ``AWS_ACCESS_KEY_ID`` and
    # ``AWS_SECRET_ACCESS_KEY`` via its default credential chain, so we only
    # need to expose the endpoint, bucket, region and presigned TTL here.
    s3_endpoint_url: str | None = Field(default=None, validation_alias=AliasChoices("S3_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"))
    s3_bucket: str = Field("inspections", validation_alias=AliasChoices("S3_BUCKET", "AWS_BUCKET"))
    s3_region: str = Field("us-east-2", validation_alias=AliasChoices("S3_REGION", "AWS_REGION"))
    s3_access_key: str | None = Field(default=None, validation_alias=AliasChoices("S3_ACCESS_KEY", "AWS_ACCESS_KEY_ID"))
    s3_secret_key: str | None = Field(default=None, validation_alias=AliasChoices("S3_SECRET_KEY", "AWS_SECRET_ACCESS_KEY"))
    presigned_url_ttl_seconds: int = Field(900, validation_alias=AliasChoices("PRESIGNED_URL_TTL_SECONDS", "PRESIGNED_TTL_S"))

    # --- Analytics / inference ---------------------------------------------
    cost_per_hour_usd: float | None = None
    images_per_hour_capacity: int | None = None

    @field_validator("cost_per_hour_usd", "images_per_hour_capacity", mode="before")
    @classmethod
    def _empty_to_none(cls, value):
        if value == "" or value is None:
            return None
        return value
    experiment_report_dir: str = str(ROOT / "training" / "reports" / "inference")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False,
                                     hide_input_in_errors=True)

    @model_validator(mode="after")
    def production_config(self):
        if self.environment == "production":
            if not self.is_postgres:
                raise ValueError("Produccion requiere DATABASE_URL de PostgreSQL")
            if parse_qs(urlsplit(self.database_url).query).get("sslmode", [""])[0] not in {"require", "verify-ca", "verify-full"}:
                raise ValueError("Produccion requiere TLS en DATABASE_URL")
            if self.jwt_secret.startswith("change-me"):
                raise ValueError("Produccion requiere JWT_SECRET propio")
            if self.inference_backend != "lambda" or not self.lambda_function_name:
                raise ValueError("Produccion requiere LAMBDA_FUNCTION_NAME e INFERENCE_BACKEND=lambda")
        return self

    # --- Derived helpers ----------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    secret_arn = os.environ.get("APP_SECRET_ARN")
    if secret_arn:
        import boto3
        try:
            response = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1")).get_secret_value(SecretId=secret_arn)
            values = json.loads(response["SecretString"])
            for key in ("DATABASE_URL", "JWT_SECRET", "FIRST_SUPERADMIN_EMAIL",
                        "FIRST_SUPERADMIN_PASSWORD", "MIGRATION_DATABASE_URL"):
                if key in values:
                    if not isinstance(values[key], str) or not values[key]:
                        raise ValueError("Invalid secret value")
                    os.environ.setdefault(key, values[key])
        except Exception:
            raise RuntimeError("No se pudo cargar el secreto de la aplicacion") from None
    return Settings()


settings = get_settings()
