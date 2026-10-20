"""Alert rules and lifecycle transitions."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..db import models


def create_for_inspection(session: Session, inspection: models.Inspection) -> models.Alert | None:
    if not inspection.shelf_id:
        return None
    shelf = session.get(models.Shelf, inspection.shelf_id)
    if not shelf or inspection.n_missing <= shelf.gap_threshold:
        return None
    existing = session.query(models.Alert).filter(
        models.Alert.shelf_id == shelf.id,
        models.Alert.status.in_(["open", "acknowledged"])).first()
    if existing:
        existing.inspection_id = inspection.id
        return existing
    excess = inspection.n_missing - shelf.gap_threshold
    severity = "low" if excess <= 2 else "medium" if excess <= 5 else "high"
    alert = models.Alert(store_id=inspection.store_id, inspection_id=inspection.id,
                         shelf_id=shelf.id, severity=severity, status="open")
    session.add(alert)
    return alert


def transition(alert: models.Alert, status: str, actor_id: str) -> None:
    now = datetime.now(timezone.utc)
    if alert.status == "closed" or status not in {"acknowledged", "closed"}:
        raise ValueError("INVALID_TRANSITION")
    if status == "acknowledged":
        if alert.status != "open":
            raise ValueError("INVALID_TRANSITION")
        alert.acked_by = actor_id
        alert.acked_at = now
    else:
        if alert.status not in {"open", "acknowledged"}:
            raise ValueError("INVALID_TRANSITION")
        alert.closed_at = now
    alert.status = status
