import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.backend.core import config


def test_production_rejects_development_defaults():
    with pytest.raises(ValidationError):
        config.Settings(_env_file=None, environment="production")


def test_secret_is_loaded_before_settings(monkeypatch):
    import boto3
    monkeypatch.setenv("APP_SECRET_ARN", "test-secret")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: SimpleNamespace(
        get_secret_value=lambda **kwargs: {"SecretString": json.dumps({
            "DATABASE_URL": "postgresql://test:test@localhost/test?sslmode=require",
            "JWT_SECRET": "s" * 40,
        })}))
    config.get_settings.cache_clear()
    try:
        loaded = config.get_settings()
        assert loaded.database_url.startswith("postgresql://")
        assert loaded.jwt_secret == "s" * 40
    finally:
        config.get_settings.cache_clear()


def test_broken_secret_fails_without_leaking_values(monkeypatch):
    import boto3
    monkeypatch.setenv("APP_SECRET_ARN", "test-secret")
    def fail(*args, **kwargs):
        raise ValueError("private-value")
    monkeypatch.setattr(boto3, "client", fail)
    config.get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as error:
            config.get_settings()
        assert "private-value" not in str(error.value)
    finally:
        config.get_settings.cache_clear()


def test_migrations_bootstrap_and_repeat_safely(tmp_path, monkeypatch):
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect
    url = f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    monkeypatch.setattr(config.settings, "migration_database_url", url)
    ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    command.upgrade(Config(str(ini)), "head")
    command.upgrade(Config(str(ini)), "head")
    engine = create_engine(url)
    try:
        assert {"users", "inspections", "detections", "alembic_version"}.issubset(inspect(engine).get_table_names())
    finally:
        engine.dispose()
