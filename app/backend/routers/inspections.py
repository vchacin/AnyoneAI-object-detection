"""Inspection history endpoints."""
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_role, require_store_access
from ..db import models
from ..db.session import get_session
from ..services.storage_service import delete, path_for

router = APIRouter(tags=["inspections"])


def _inspection_or_404(inspection_id: str, session: Session, user: models.User) -> models.Inspection:
    inspection = session.get(models.Inspection, inspection_id)
    if not inspection:
        raise HTTPException(404, detail={"detail": "Inspeccion no encontrada", "code": "NOT_FOUND"})
    require_store_access(inspection.store_id, user)
    return inspection


def _public(inspection: models.Inspection, session: Session) -> dict:
    detections = session.query(models.DetectionRecord).filter(
        models.DetectionRecord.inspection_id == inspection.id).all()
    return {
        "id": inspection.id, "store_id": inspection.store_id,
        "camera_id": inspection.camera_id, "shelf_id": inspection.shelf_id,
        "image_key": inspection.image_key, "image_width": inspection.image_width,
        "image_height": inspection.image_height, "image_bytes": inspection.image_bytes,
        "source": inspection.source, "model_version": inspection.model_version,
        "n_objects": inspection.n_objects, "n_missing": inspection.n_missing,
        "latency_ms": inspection.latency_ms, "created_by": inspection.created_by,
        "employee_id": inspection.employee_id,
        "created_at": inspection.created_at.isoformat() if inspection.created_at else None,
        "detections": [
            {"class": item.class_name, "bbox": [item.x1, item.y1, item.x2, item.y2],
             "confidence": item.confidence, "source": item.source}
            for item in detections
        ],
    }


@router.get("/inspections")
def list_inspections(store_id: str | None = None, camera_id: str | None = None,
                     shelf_id: str | None = None, date_from: datetime | None = None,
                     date_to: datetime | None = None, limit: int = 50, offset: int = 0,
                     session: Session = Depends(get_session),
                     user: models.User = Depends(get_current_user)):
    query = session.query(models.Inspection)
    if user.role != "super_admin":
        query = query.filter(models.Inspection.store_id == user.store_id)
    elif store_id:
        query = query.filter(models.Inspection.store_id == store_id)
    if camera_id:
        query = query.filter(models.Inspection.camera_id == camera_id)
    if shelf_id:
        query = query.filter(models.Inspection.shelf_id == shelf_id)
    if date_from:
        query = query.filter(models.Inspection.created_at >= date_from)
    if date_to:
        query = query.filter(models.Inspection.created_at <= date_to)
    rows = query.order_by(models.Inspection.created_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 500)).all()
    return [_public(row, session) for row in rows]


@router.get("/inspections/{inspection_id}")
def get_inspection(inspection_id: str, session: Session = Depends(get_session),
                   user: models.User = Depends(get_current_user)):
    return _public(_inspection_or_404(inspection_id, session, user), session)


@router.get("/inspections/export")
def export_inspections(date_from: datetime | None = None, date_to: datetime | None = None,
                       store_id: str | None = None, shelf_id: str | None = None,
                       limit: int = 1000, session: Session = Depends(get_session),
                       user: models.User = Depends(get_current_user)):
    query = session.query(models.Inspection)
    if user.role != "super_admin":
        query = query.filter(models.Inspection.store_id == user.store_id)
    elif store_id:
        query = query.filter(models.Inspection.store_id == store_id)
    if shelf_id:
        query = query.filter(models.Inspection.shelf_id == shelf_id)
    if date_from:
        query = query.filter(models.Inspection.created_at >= date_from)
    if date_to:
        query = query.filter(models.Inspection.created_at <= date_to)
    rows = query.order_by(models.Inspection.created_at.asc()).limit(min(max(limit, 1), 10000)).all()

    def stream():
        for row in rows:
            yield json.dumps(_public(row, session), ensure_ascii=False) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson",
                             headers={"Content-Disposition": "attachment; filename=inspections.jsonl"})


@router.get("/inspections/{inspection_id}/image")
def get_inspection_image(inspection_id: str, session: Session = Depends(get_session),
                         user: models.User = Depends(get_current_user)):
    inspection = _inspection_or_404(inspection_id, session, user)
    if not inspection.image_key:
        raise HTTPException(404, detail={"detail": "Imagen no disponible", "code": "IMAGE_NOT_FOUND"})
    path = path_for(inspection.image_key)
    if not path.is_file():
        raise HTTPException(404, detail={"detail": "Imagen no disponible", "code": "IMAGE_NOT_FOUND"})
    return FileResponse(path)


@router.delete("/inspections/{inspection_id}", status_code=204)
def delete_inspection(inspection_id: str, session: Session = Depends(get_session),
                      user: models.User = Depends(require_role("super_admin", "store_admin"))):
    inspection = _inspection_or_404(inspection_id, session, user)
    if inspection.image_key:
        delete(inspection.image_key)
    session.query(models.DetectionRecord).filter(
        models.DetectionRecord.inspection_id == inspection.id).delete()
    session.delete(inspection)
    session.commit()
