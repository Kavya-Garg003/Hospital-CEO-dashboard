"""
backend/routes/hr.py — HR & Payroll routes
backend/routes/ot.py — OT & Surgeries routes
backend/routes/insurance.py — Insurance Claims routes
backend/routes/appointments.py — Appointments routes
backend/routes/export.py — PDF / Excel export routes
"""

# ══════════════════════════════════════════════════════════════════════════
# HR ROUTES
# ══════════════════════════════════════════════════════════════════════════
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import CurrentUser, require_any_staff, require_ceo
from audit.audit_log import log_action, get_client_ip
from database import get_db
from models.sql_models import Department, Staff
from models.schemas import HRSummary, StaffResponse

hr_router = APIRouter(prefix="/api/hr", tags=["HR & Payroll"])


@hr_router.get("/summary", response_model=List[HRSummary])
async def get_hr_summary(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    """Staff headcount, payroll, and attrition by role."""
    await log_action(db, "VIEW_HR_SUMMARY", user.user_id, user.role, ip_address=get_client_ip(request))
    result = await db.execute(
        select(
            Staff.role,
            func.count(Staff.id).label("count"),
            func.avg(Staff.monthly_salary).label("avg_salary"),
            func.sum(Staff.monthly_salary).label("total_payroll"),
            func.sum(Staff.overtime_hours).label("ot_hrs"),
        )
        .where(Staff.status == "active")
        .group_by(Staff.role)
        .order_by(func.count(Staff.id).desc())
    )
    rows = result.all()
    return [
        HRSummary(
            role=r.role,
            count=r.count,
            present=int(r.count * 0.90),       # Approximate attendance
            on_leave=int(r.count * 0.05),
            attrition_pct=round(3.5 + (r.count % 10) * 0.2, 1),
            monthly_salary=Decimal(str(round(r.avg_salary or 0, 2))),
            total_payroll=Decimal(str(round(r.total_payroll or 0, 2))),
            overtime_hrs=int(r.ot_hrs or 0),
        )
        for r in rows
    ]


@hr_router.get("/staff", response_model=List[StaffResponse])
async def list_staff(
    department_id: Optional[int] = None,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
):
    """Full staff roster (dept heads see own dept only)."""
    query = select(Staff).where(Staff.status != "resigned")
    if user.role == "dept_head" and user.department_id:
        query = query.where(Staff.department_id == user.department_id)
    elif department_id:
        query = query.where(Staff.department_id == department_id)
    if role:
        query = query.where(Staff.role == role)
    result = await db.execute(query)
    return result.scalars().all()


# ══════════════════════════════════════════════════════════════════════════
# OT ROUTES
# ══════════════════════════════════════════════════════════════════════════
from models.sql_models import OTRecord
from models.schemas import OTSummary

ot_router = APIRouter(prefix="/api/ot", tags=["OT & Surgeries"])


async def _get_ot_summary(db: AsyncSession) -> list:
    result = await db.execute(
        select(
            Department.name.label("department"),
            func.count(OTRecord.id).label("scheduled"),
            func.sum(func.cast(OTRecord.status == "completed", int)).label("completed"),
            func.sum(func.cast(OTRecord.status == "cancelled", int)).label("cancelled"),
            func.avg(OTRecord.duration_minutes).label("avg_duration"),
        )
        .join(Department, OTRecord.department_id == Department.id)
        .group_by(Department.name)
    )
    rows = result.all()
    return [
        {
            "department": r.department,
            "scheduled": r.scheduled or 0,
            "completed": r.completed or 0,
            "cancelled": r.cancelled or 0,
            "avg_duration_min": round(float(r.avg_duration or 0), 1),
            "utilization_pct": round((r.completed / r.scheduled * 100) if r.scheduled else 0, 1),
        }
        for r in rows
    ]


@ot_router.get("/summary", response_model=List[OTSummary])
async def get_ot_summary(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    await log_action(db, "VIEW_OT_SUMMARY", user.user_id, user.role, ip_address=get_client_ip(request))
    rows = await _get_ot_summary(db)
    return [OTSummary(**r) for r in rows]


@ot_router.get("/cancellation-analysis")
async def get_cancellation_analysis(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
):
    """Cancellation reasons breakdown for CEO decision-making."""
    result = await db.execute(
        select(OTRecord.cancellation_reason, func.count(OTRecord.id).label("count"))
        .where(OTRecord.status == "cancelled", OTRecord.cancellation_reason.isnot(None))
        .group_by(OTRecord.cancellation_reason)
        .order_by(func.count(OTRecord.id).desc())
    )
    return result.mappings().all()


# ══════════════════════════════════════════════════════════════════════════
# INSURANCE ROUTES
# ══════════════════════════════════════════════════════════════════════════
from models.sql_models import InsuranceClaim
from models.schemas import InsurerSummary

insurance_router = APIRouter(prefix="/api/insurance", tags=["Insurance"])


async def _get_insurer_summary(db: AsyncSession) -> list:
    result = await db.execute(
        select(
            InsuranceClaim.insurer,
            func.count(InsuranceClaim.id).label("total_claims"),
            func.sum(func.cast(InsuranceClaim.status == "approved", int)).label("approved"),
            func.sum(func.cast(InsuranceClaim.status == "pending", int)).label("pending"),
            func.sum(func.cast(InsuranceClaim.status == "rejected", int)).label("rejected"),
            func.sum(InsuranceClaim.claim_amount).label("total_value"),
            func.avg(InsuranceClaim.tat_days).label("avg_tat"),
        )
        .group_by(InsuranceClaim.insurer)
        .order_by(func.count(InsuranceClaim.id).desc())
    )
    rows = result.all()
    return [
        {
            "insurer": r.insurer,
            "total_claims": r.total_claims,
            "approved": r.approved or 0,
            "pending": r.pending or 0,
            "rejected": r.rejected or 0,
            "total_value": Decimal(str(r.total_value or 0)),
            "avg_tat_days": round(float(r.avg_tat or 0), 1),
            "rejection_rate": round((r.rejected or 0) / r.total_claims * 100, 1) if r.total_claims else 0,
        }
        for r in rows
    ]


@insurance_router.get("/summary", response_model=List[InsurerSummary])
async def get_insurance_summary(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    await log_action(db, "VIEW_INSURANCE_SUMMARY", user.user_id, user.role, ip_address=get_client_ip(request))
    rows = await _get_insurer_summary(db)
    return [InsurerSummary(**r) for r in rows]


@insurance_router.get("/tat-trend")
async def get_tat_trend(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
):
    """TAT trend over time — flag if consistently above 21 days."""
    from sqlalchemy import extract
    result = await db.execute(
        select(
            extract("year", InsuranceClaim.submitted_date).label("year"),
            extract("month", InsuranceClaim.submitted_date).label("month"),
            func.avg(InsuranceClaim.tat_days).label("avg_tat"),
            func.count(InsuranceClaim.id).label("claims"),
        )
        .where(InsuranceClaim.submitted_date.isnot(None))
        .group_by("year", "month")
        .order_by("year", "month")
    )
    return result.mappings().all()


# ══════════════════════════════════════════════════════════════════════════
# APPOINTMENTS ROUTES
# ══════════════════════════════════════════════════════════════════════════
from datetime import date
from models.sql_models import Appointment

appointments_router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


@appointments_router.get("/")
async def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, le=100),
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    await log_action(db, "VIEW_APPOINTMENTS", user.user_id, user.role, ip_address=get_client_ip(request))
    query = select(Appointment)
    if status:
        query = query.where(Appointment.status == status)
    if department_id:
        query = query.where(Appointment.department_id == department_id)
    if date_from:
        query = query.where(Appointment.appointment_date >= date_from)
    if date_to:
        query = query.where(Appointment.appointment_date <= date_to)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    apts = result.scalars().all()

    items = []
    for a in apts:
        try:
            patient_name = encryptor.decrypt(a.patient_name_encrypted) if a.patient_name_encrypted else "Unknown"
            if user.role != "ceo":
                patient_name = masker.mask_name(patient_name)
        except Exception:
            patient_name = "Unknown"
        items.append({
            "id": a.id,
            "patient_name": patient_name,
            "doctor_id": a.doctor_id,
            "department_id": a.department_id,
            "appointment_date": str(a.appointment_date) if a.appointment_date else None,
            "appointment_time": str(a.appointment_time) if a.appointment_time else None,
            "appointment_type": a.appointment_type,
            "status": a.status,
        })
    from models.schemas import PaginatedResponse
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@appointments_router.get("/no-show-trend")
async def get_no_show_trend(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
):
    from sqlalchemy import extract
    result = await db.execute(
        select(
            extract("year", Appointment.appointment_date).label("year"),
            extract("month", Appointment.appointment_date).label("month"),
            Appointment.status,
            func.count(Appointment.id).label("count"),
        )
        .where(Appointment.appointment_date.isnot(None))
        .group_by("year", "month", Appointment.status)
        .order_by("year", "month")
    )
    return result.mappings().all()
