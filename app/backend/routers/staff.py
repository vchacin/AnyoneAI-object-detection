"""Employee and shift management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_role, require_store_access
from ..db import models
from ..db.session import get_session

router = APIRouter(tags=["staff"])


class EmployeeCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    position: str | None = None
    user_id: str | None = None


class EmployeePatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    position: str | None = None
    is_active: bool | None = None


class ShiftCreate(BaseModel):
    employee_id: str
    weekday: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")


def _minutes(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    if hour > 23 or minute > 59:
        raise ValueError
    return hour * 60 + minute


def _employee(store_id: str, employee_id: str, session: Session) -> models.Employee:
    employee = session.query(models.Employee).filter(
        models.Employee.id == employee_id, models.Employee.store_id == store_id).first()
    if not employee:
        raise HTTPException(404, detail={"detail": "Empleado no encontrado", "code": "NOT_FOUND"})
    return employee


def _store_guard(store_id: str, actor: models.User) -> None:
    require_store_access(store_id, actor)


@router.post("/stores/{store_id}/employees", status_code=201)
def create_employee(store_id: str, payload: EmployeeCreate, session: Session = Depends(get_session),
                    actor: models.User = Depends(require_role("super_admin", "store_admin"))):
    _store_guard(store_id, actor)
    if payload.user_id and not session.query(models.User).filter(
            models.User.id == payload.user_id, models.User.store_id == store_id).first():
        raise HTTPException(404, detail={"detail": "Usuario no encontrado", "code": "NOT_FOUND"})
    employee = models.Employee(store_id=store_id, **payload.model_dump())
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@router.get("/stores/{store_id}/employees")
def list_employees(store_id: str, session: Session = Depends(get_session),
                   actor: models.User = Depends(get_current_user)):
    _store_guard(store_id, actor)
    return session.query(models.Employee).filter(models.Employee.store_id == store_id).all()


@router.patch("/employees/{employee_id}")
def update_employee(employee_id: str, payload: EmployeePatch, session: Session = Depends(get_session),
                    actor: models.User = Depends(require_role("super_admin", "store_admin"))):
    employee = session.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(404, detail={"detail": "Empleado no encontrado", "code": "NOT_FOUND"})
    _store_guard(employee.store_id, actor)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, key, value)
    session.commit()
    return employee


@router.post("/employees/{employee_id}/shifts", status_code=201)
def create_shift(employee_id: str, payload: ShiftCreate, session: Session = Depends(get_session),
                 actor: models.User = Depends(require_role("super_admin", "store_admin"))):
    employee = session.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(404, detail={"detail": "Empleado no encontrado", "code": "NOT_FOUND"})
    _store_guard(employee.store_id, actor)
    try:
        start, end = _minutes(payload.start_time), _minutes(payload.end_time)
    except ValueError:
        raise HTTPException(422, detail={"detail": "Horario invalido", "code": "INVALID_TIME"})
    if start >= end:
        raise HTTPException(422, detail={"detail": "El inicio debe ser anterior al fin", "code": "INVALID_SHIFT"})
    existing = session.query(models.Shift).filter(
        models.Shift.employee_id == employee_id, models.Shift.weekday == payload.weekday).all()
    if any(start < _minutes(item.end_time) and end > _minutes(item.start_time) for item in existing):
        raise HTTPException(409, detail={"detail": "El turno se solapa", "code": "SHIFT_OVERLAP"})
    shift = models.Shift(store_id=employee.store_id, **payload.model_dump())
    session.add(shift)
    session.commit()
    session.refresh(shift)
    return shift


@router.get("/stores/{store_id}/shifts")
def list_shifts(store_id: str, session: Session = Depends(get_session),
                actor: models.User = Depends(get_current_user)):
    _store_guard(store_id, actor)
    return session.query(models.Shift).filter(models.Shift.store_id == store_id).all()


@router.patch("/shifts/{shift_id}")
def update_shift(shift_id: str, payload: ShiftCreate, session: Session = Depends(get_session),
                 actor: models.User = Depends(require_role("super_admin", "store_admin"))):
    shift = session.get(models.Shift, shift_id)
    if not shift:
        raise HTTPException(404, detail={"detail": "Turno no encontrado", "code": "NOT_FOUND"})
    _store_guard(shift.store_id, actor)
    employee = session.query(models.Employee).filter(
        models.Employee.id == payload.employee_id,
        models.Employee.store_id == shift.store_id).first()
    if not employee:
        raise HTTPException(404, detail={"detail": "Empleado no encontrado", "code": "NOT_FOUND"})
    try:
        start, end = _minutes(payload.start_time), _minutes(payload.end_time)
    except ValueError:
        raise HTTPException(422, detail={"detail": "Horario invalido", "code": "INVALID_TIME"})
    if start >= end:
        raise HTTPException(422, detail={"detail": "El inicio debe ser anterior al fin", "code": "INVALID_SHIFT"})
    for key, value in payload.model_dump().items():
        setattr(shift, key, value)
    session.commit()
    return shift


@router.delete("/shifts/{shift_id}", status_code=204)
def delete_shift(shift_id: str, session: Session = Depends(get_session),
                 actor: models.User = Depends(require_role("super_admin", "store_admin"))):
    shift = session.get(models.Shift, shift_id)
    if not shift:
        raise HTTPException(404, detail={"detail": "Turno no encontrado", "code": "NOT_FOUND"})
    _store_guard(shift.store_id, actor)
    session.delete(shift)
    session.commit()
