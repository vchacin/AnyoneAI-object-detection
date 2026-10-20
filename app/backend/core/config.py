"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./app/data/detections.db"
    jwt_secret: str = Field("change-me-in-development-secret-32", min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(15, validation_alias=AliasChoices("ACCESS_TOKEN_MINUTES", "JWT_ACCESS_TTL_MINUTES"))
    refresh_token_days: int = Field(30, validation_alias=AliasChoices("REFRESH_TOKEN_DAYS", "JWT_REFRESH_TTL_DAYS"))
    cors_origins: str = ""
    enable_docs: bool = True
    first_superadmin_email: str | None = None
    first_superadmin_password: str | None = None
    max_upload_mb: int = Field(10, validation_alias=AliasChoices("MAX_UPLOAD_MB", "MAX_IMAGE_MB"))
    max_image_width: int = Field(10000, validation_alias=AliasChoices("MAX_IMAGE_WIDTH", "MAX_IMAGE_RESOLUTION"))
    max_image_height: int = Field(10000, validation_alias=AliasChoices("MAX_IMAGE_HEIGHT", "MAX_IMAGE_RESOLUTION"))

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
