"""Database engine, session dependency, and legacy detection persistence."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, sessionmaker

from ..core.config import settings

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = ROOT / "app" / "data" / "detections.db"
DATABASE_URL = settings.database_url
if DATABASE_URL == "sqlite:///./app/data/detections.db":
    DATABASE_URL = f"sqlite:///{DEFAULT_DB}"

Base = declarative_base()


class Detection(Base):
    __tablename__ = "detections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_weights: Mapped[str | None] = mapped_column(String(512))
    n_objects: Mapped[int] = mapped_column(Integer, default=0)
    n_missing: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    objects: Mapped[list] = mapped_column(JSON, default=list)
    missing: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict:
        return {key: getattr(self, key) for key in (
            "id", "image_name", "model_weights", "n_objects", "n_missing",
            "confidence", "objects", "missing"
        )} | {"created_at": self.created_at.isoformat() if self.created_at else None}


def _engine_kwargs(url: str) -> dict:
    return {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}


engine = create_engine(DATABASE_URL, pool_pre_ping=True, **_engine_kwargs(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Path(DEFAULT_DB).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    from . import models  # noqa: F401
    models.Base.metadata.create_all(engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def save_detection(session, *, image_name: str, result: dict, model_weights: str | None = None) -> Detection:
    row = Detection(
        image_name=image_name,
        model_weights=model_weights or None,
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
