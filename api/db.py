"""Persistencia de detecciones.

Por defecto utiliza SQLite (cero infraestructura) mediante SQLAlchemy. Para
PostgreSQL basta definir `DATABASE_URL=postgresql+psycopg://...`; el modelo no
cambia.

Tabla `detections`: una fila por imagen procesada, con el JSON de cajas de
producto y de huecos, para permitir consultas históricas de inventario.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (JSON, Column, DateTime, Float, Integer, String,
                        create_engine)
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "api" / "data" / "detections.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DB.as_posix()}")

Base = declarative_base()


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_name = Column(String(255), nullable=False, index=True)
    model_weights = Column(String(512))
    n_objects = Column(Integer, default=0)
    n_missing = Column(Integer, default=0)
    confidence = Column(Float, default=0.0)
    objects = Column(JSON, default=list)
    missing = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "image_name": self.image_name,
            "model_weights": self.model_weights,
            "n_objects": self.n_objects,
            "n_missing": self.n_missing,
            "confidence": self.confidence,
            "objects": self.objects,
            "missing": self.missing,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def _engine_kwargs(url: str) -> dict:
    return {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}


engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       **_engine_kwargs(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Crea las tablas. Operación idempotente."""
    if DATABASE_URL.startswith("sqlite"):
        Path(DATABASE_URL.replace("sqlite:///", "", 1)).parent.mkdir(
            parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get_session():
    """Dependencia de FastAPI: proporciona una sesión por request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def save_detection(session, *, image_name: str, result: dict,
                   model_weights: str | None = None) -> Detection:
    row = Detection(
        image_name=image_name,
        model_weights=model_weights or str(getattr(result, "weights", "")) or None,
        n_objects=len(result.get("objects", [])),
        n_missing=len(result.get("missing", [])),
        confidence=float(result.get("conf", 0.0)),
        objects=result.get("objects", []),
        missing=result.get("missing", []),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def to_json(row: Detection) -> str:
    return json.dumps(row.as_dict(), ensure_ascii=False)
