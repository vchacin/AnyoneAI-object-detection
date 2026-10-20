"""SQLAlchemy models for the multi-tenant backend."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Store(Base):
    __tablename__ = "stores"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    users: Mapped[list["User"]] = relationship(back_populates="store")


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str | None] = mapped_column(ForeignKey("stores.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    store: Mapped[Store | None] = relationship(back_populates="users")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Shift(Base):
    __tablename__ = "shifts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)


class Shelf(Base):
    __tablename__ = "shelves"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(100))
    gap_threshold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    shelf_id: Mapped[str | None] = mapped_column(ForeignKey("shelves.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(300))
    token_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Inspection(Base):
    __tablename__ = "inspections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    camera_id: Mapped[str | None] = mapped_column(ForeignKey("cameras.id"), index=True)
    shelf_id: Mapped[str | None] = mapped_column(ForeignKey("shelves.id"), index=True)
    image_key: Mapped[str | None] = mapped_column(String(500))
    image_width: Mapped[int | None] = mapped_column(Integer)
    image_height: Mapped[int | None] = mapped_column(Integer)
    image_bytes: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    model_version: Mapped[str] = mapped_column(String(200), nullable=False)
    n_objects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    n_missing: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class DetectionRecord(Base):
    __tablename__ = "detection_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"), index=True)
    class_name: Mapped[str] = mapped_column("class", String(30), nullable=False)
    x1: Mapped[float] = mapped_column(Float, nullable=False)
    y1: Mapped[float] = mapped_column(Float, nullable=False)
    x2: Mapped[float] = mapped_column(Float, nullable=False)
    y2: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str | None] = mapped_column(String(30))


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"))
    shelf_id: Mapped[str | None] = mapped_column(ForeignKey("shelves.id"), index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    acked_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_id: Mapped[str | None] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36))
    store_id: Mapped[str | None] = mapped_column(String(36), index=True)
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class StoreSetting(Base):
    __tablename__ = "store_settings"
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Bogota")
    opening_time: Mapped[str | None] = mapped_column(String(5))
    closing_time: Mapped[str | None] = mapped_column(String(5))
    peak_hours: Mapped[list | None] = mapped_column(JSON)
    default_conf: Mapped[float] = mapped_column(Float, default=0.25)
    alert_cooldown_minutes: Mapped[int] = mapped_column(Integer, default=0)
