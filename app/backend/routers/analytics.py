"""Dashboard, export, and usage metrics endpoints."""
from datetime import datetime, timezone
import json
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_store_access
from ..db import models
from ..db.session import get_session
from .inspections import _public

router = APIRouter(tags=["analytics"])


def _scope(query, user: models.User, store_id: str | None = None):
    if user.role == "super_admin":
        return query.filter(models.Inspection.store_id == store_id) if store_id else query
    return query.filter(models.Inspection.store_id == user.store_id)


@router.get("/dashboard/global")
def global_dashboard(session: Session = Depends(get_session),
                     user: models.User = Depends(get_current_user)):
    if user.role != "super_admin":
        raise HTTPException(403, detail={"detail": "No tiene permisos para esta operacion", "code": "FORBIDDEN"})
    active_stores = session.query(models.Store).filter(models.Store.status == "active").count()
    inspections = session.query(models.Inspection).order_by(
        models.Inspection.created_at.desc()).limit(10).all()
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly = session.query(models.Inspection).filter(
        models.Inspection.created_at >= month_start).count()
    return {"active_stores": active_stores, "monthly_images_processed": monthly,
            "recent_inspections": [_public(row, session) for row in inspections]}


@router.get("/stores/{store_id}/dashboard")
def store_dashboard(store_id: str, session: Session = Depends(get_session),
                     user: models.User = Depends(get_current_user)):
    require_store_access(store_id, user)
    inspections = session.query(models.Inspection).filter(
        models.Inspection.store_id == store_id).order_by(
        models.Inspection.created_at.desc()).limit(10).all()
    open_alerts = session.query(models.Alert).filter(
        models.Alert.store_id == store_id, models.Alert.status == "open").count()
    today = datetime.now(timezone.utc).date()
    today_count = session.query(models.Inspection).filter(
        models.Inspection.store_id == store_id,
        func.date(models.Inspection.created_at) == today).count()
    shelves = session.query(models.Shelf).filter(models.Shelf.store_id == store_id).all()
    latest_by_shelf = []
    for shelf in shelves:
        latest = session.query(models.Inspection).filter(
            models.Inspection.store_id == store_id,
            models.Inspection.shelf_id == shelf.id).order_by(
            models.Inspection.created_at.desc()).first()
        latest_by_shelf.append({"shelf_id": shelf.id, "name": shelf.name,
                                "n_missing": latest.n_missing if latest else 0})
    return {"store_id": store_id, "open_alerts_count": open_alerts,
            "inspections_today": today_count,
            "latest_inspections": [_public(row, session) for row in inspections],
            "latest_by_shelf": latest_by_shelf}


@router.get("/stores/{store_id}/cameras/summary")
def camera_summary(store_id: str, session: Session = Depends(get_session),
                   user: models.User = Depends(get_current_user)):
    require_store_access(store_id, user)
    cameras = session.query(models.Camera).filter(models.Camera.store_id == store_id).all()
    result = []
    for camera in cameras:
        latest = session.query(models.Inspection).filter(
            models.Inspection.camera_id == camera.id).order_by(
            models.Inspection.created_at.desc()).first()
        result.append({"id": camera.id, "alias": camera.name, "status": camera.status,
                       "last_seen": camera.last_seen,
                       "last_inspection_id": latest.id if latest else None,
                       "n_objects": latest.n_objects if latest else 0,
                       "n_missing": latest.n_missing if latest else 0})
    return result


@router.get("/inspections/{inspection_id}/export")
def export_inspection(inspection_id: str, session: Session = Depends(get_session),
                      user: models.User = Depends(get_current_user)):
    inspection = session.get(models.Inspection, inspection_id)
    if not inspection:
        raise HTTPException(404, detail={"detail": "Inspeccion no encontrada", "code": "NOT_FOUND"})
    require_store_access(inspection.store_id, user)
    payload = _public(inspection, session)
    return Response(content=json.dumps(payload, ensure_ascii=False),
                    media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{inspection.id}.json"'})


@router.get("/metrics/usage")
def usage_metrics(date_from: datetime | None = None, date_to: datetime | None = None,
                  store_id: str | None = None, session: Session = Depends(get_session),
                  user: models.User = Depends(get_current_user)):
    if store_id:
        require_store_access(store_id, user)
    query = _scope(session.query(models.Inspection), user, store_id)
    if date_from:
        query = query.filter(models.Inspection.created_at >= date_from)
    if date_to:
        query = query.filter(models.Inspection.created_at <= date_to)
    rows = query.all()
    latencies = sorted(row.latency_ms for row in rows if row.latency_ms is not None)
    def percentile(value: float) -> float | None:
        if not latencies:
            return None
        index = min(len(latencies) - 1, round((len(latencies) - 1) * value))
        return round(float(latencies[index]), 2)
    capacity = float(os.environ["IMAGES_PER_HOUR_CAPACITY"]) if os.environ.get("IMAGES_PER_HOUR_CAPACITY") else None
    cost = float(os.environ["COST_PER_HOUR_USD"]) if os.environ.get("COST_PER_HOUR_USD") else None
    return {"store_id": store_id or (user.store_id if user.role != "super_admin" else None),
            "images_processed": len(rows), "latency_p50_ms": percentile(0.50),
            "latency_p95_ms": percentile(0.95),
            "estimated_cost_per_1000": round(cost * 1000 / capacity, 4)
            if cost is not None and capacity else None}
