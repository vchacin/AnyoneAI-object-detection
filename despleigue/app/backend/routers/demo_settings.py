"""Shared demo inference profile, persisted outside the browser."""
import os
from pathlib import Path
import tempfile
import threading
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ..core.deps import get_current_user, require_role

CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "config" / "demo-inference.json"
_lock = threading.Lock()
router = APIRouter(prefix="/api/v1/demo/settings", tags=["demo"])


class DemoSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    provider: Literal["local", "lambda", "runpod"] = "local"
    confidence: float = Field(default=0.19, ge=0, le=1, allow_inf_nan=False)
    iou: float = Field(default=0.7, ge=0, le=1, allow_inf_nan=False)
    sahi: bool = False
    imageSize: int = Field(default=640, ge=320, le=1920, strict=True)

    @field_validator("imageSize")
    @classmethod
    def valid_size(cls, value):
        if value % 32:
            raise ValueError("Processing size must be a multiple of 32")
        return value


@router.get("", response_model=DemoSettings)
def read_settings(user=Depends(get_current_user)):
    with _lock:
        try:
            return DemoSettings.model_validate_json(CONFIG_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return DemoSettings()
        except (OSError, ValidationError):
            raise HTTPException(500, "Could not read demo settings") from None


@router.put("", response_model=DemoSettings)
def save_settings(profile: DemoSettings, user=Depends(require_role("super_admin", "store_admin"))):
    with _lock:
        temporary = None
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=CONFIG_PATH.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(profile.model_dump_json(indent=2) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, CONFIG_PATH)
        except OSError:
            raise HTTPException(500, "Could not save demo settings") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return profile
