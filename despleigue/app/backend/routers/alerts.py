"""Alert listing and lifecycle endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_role, require_store_access
from ..db import models
from ..db.session import get_session
from ..services.alert_service import transition

router = APIRouter(tags=["alerts"])


class AlertPatch(BaseModel):
    status: str


def _public(alert: models.Alert) -> dict:
    return {"id": alert.id, "store_id": alert.store_id, "inspection_id": alert.inspection_id,
            "shelf_id": alert.shelf_id, "severity": alert.severity, "status": alert.status,
            "acked_by": alert.acked_by, "created_at": alert.created_at.isoformat(),
            "acked_at": alert.acked_at.isoformat() if alert.acked_at else None,
            "closed_at": alert.closed_at.isoformat() if alert.closed_at else None}


@router.get("/stores/{store_id}/alerts")
def list_alerts(store_id: str, status: str | None = None, severity: str | None = None,
                limit: int = 50, offset: int = 0, session: Session = Depends(get_session),
                user: models.User = Depends(get_current_user)):
    require_store_access(store_id, user)
    query = session.query(models.Alert).filter(models.Alert.store_id == store_id)
    if status:
        query = query.filter(models.Alert.status == status)
    if severity:
        query = query.filter(models.Alert.severity == severity)
    rows = query.order_by(models.Alert.created_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 500)).all()
    return [_public(row) for row in rows]


@router.get("/stores/{store_id}/alerts/count")
def count_alerts(store_id: str, status: str = "open", session: Session = Depends(get_session),
                 user: models.User = Depends(get_current_user)):
    require_store_access(store_id, user)
    count = session.query(models.Alert).filter(
        models.Alert.store_id == store_id, models.Alert.status == status).count()
    return {"store_id": store_id, "status": status, "count": count}


@router.patch("/alerts/{alert_id}")
def update_alert(alert_id: str, payload: AlertPatch, session: Session = Depends(get_session),
                 user: models.User = Depends(require_role("super_admin", "store_admin", "employee"))):
    alert = session.get(models.Alert, alert_id)
    if not alert:
        raise HTTPException(404, detail={"detail": "Alerta no encontrada", "code": "NOT_FOUND"})
    require_store_access(alert.store_id, user)
    try:
        transition(alert, payload.status, user.id)
    except ValueError:
        raise HTTPException(409, detail={"detail": "Transicion de alerta invalida", "code": "INVALID_TRANSITION"})
    session.commit()
    return _public(alert)
