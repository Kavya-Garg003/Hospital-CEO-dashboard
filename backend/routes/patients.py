"""
backend/routes/patients.py
---------------------------
Patient data routes with PHI protection:
  - CEO sees full decrypted data
  - Other roles see masked PHI
  - Every access is audit-logged
  - Pagination enforced (max 100 per call)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import get_current_user, CurrentUser, require_any_staff
from audit.audit_log import log_action, get_client_ip
from database import get_db
from encryption import encryptor, masker
from models.sql_models import Department, Patient
from models.schemas import PatientResponse, PatientSummary, PaginatedResponse

router = APIRouter(prefix="/api/patients", tags=["Patients"])


def _decrypt_patient(patient: Patient, role: str) -> PatientResponse:
    """
    Decrypt PHI fields. Apply masking for non-CEO roles.
    CEO: full decrypted name and diagnosis.
    Others: masked name, masked diagnosis.
    """
    try:
        full_name = encryptor.decrypt(patient.name_encrypted)
        diagnosis = encryptor.decrypt_optional(patient.diagnosis_encrypted)
    except Exception:
        full_name = "Decryption Error"
        diagnosis = None

    if role != "ceo":
        full_name = masker.mask_name(full_name)
        if diagnosis:
            # Show only first word of diagnosis for non-CEO
            diagnosis = diagnosis.split()[0] + "***" if diagnosis else None

    return PatientResponse(
        id=patient.id,
        name=full_name,
        age=patient.age,
        gender=patient.gender,
        department_id=patient.department_id or 0,
        admission_date=patient.admission_date,
        discharge_date=patient.discharge_date,
        patient_type=patient.patient_type,
        icd_code=patient.icd_code,
        diagnosis=diagnosis,
        insurance_provider=patient.insurance_provider,
        bill_amount=patient.bill_amount,
        status=patient.status,
        readmission_risk_score=patient.readmission_risk_score,
    )


async def _get_bed_occupancy(db: AsyncSession) -> list:
    """Bed occupancy by department — used by analytics alert engine."""
    result = await db.execute(
        select(
            Department.name,
            Department.total_beds,
            func.count(Patient.id).label("occupied"),
        )
        .outerjoin(Patient, (Patient.department_id == Department.id) & (Patient.status == "active") & (Patient.patient_type == "inpatient"))
        .where(Department.total_beds > 0)
        .group_by(Department.name, Department.total_beds)
    )
    return [
        {"name": r.name, "total_beds": r.total_beds, "occupied": r.occupied or 0}
        for r in result.all()
    ]


@router.get("/", response_model=PaginatedResponse)
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    patient_type: Optional[str] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    """Paginated patient list with PHI protection."""
    await log_action(
        db, "VIEW_PATIENT_LIST", user.user_id, user.role,
        resource_type="Patient",
        ip_address=get_client_ip(request),
        request_payload={"page": page, "page_size": page_size, "filters": {"type": patient_type, "dept": department_id}},
    )

    query = select(Patient)

    # Dept heads see only their department's patients
    if user.role == "dept_head" and user.department_id:
        query = query.where(Patient.department_id == user.department_id)
    elif department_id:
        query = query.where(Patient.department_id == department_id)

    if patient_type:
        query = query.where(Patient.patient_type == patient_type)
    if status:
        query = query.where(Patient.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    patients = result.scalars().all()

    items = [_decrypt_patient(p, user.role) for p in patients]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    """Single patient record with PHI decryption and audit logging."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Dept head access check
    if user.role == "dept_head" and patient.department_id != user.department_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await log_action(
        db, "VIEW_PATIENT_RECORD", user.user_id, user.role,
        resource_type="Patient", resource_id=patient_id,
        ip_address=get_client_ip(request),
    )
    return _decrypt_patient(patient, user.role)


@router.get("/bed-occupancy/by-department")
async def get_bed_occupancy(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
):
    """Real-time bed occupancy grid."""
    return await _get_bed_occupancy(db)


@router.get("/summary/volume-trend")
async def get_volume_trend(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
):
    """Monthly patient volume breakdown by type."""
    from sqlalchemy import extract
    result = await db.execute(
        select(
            extract("year", Patient.admission_date).label("year"),
            extract("month", Patient.admission_date).label("month"),
            Patient.patient_type,
            func.count(Patient.id).label("count"),
        )
        .where(Patient.admission_date.isnot(None))
        .group_by("year", "month", Patient.patient_type)
        .order_by("year", "month")
    )
    return result.mappings().all()
