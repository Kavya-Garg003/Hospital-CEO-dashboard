"""
backend/routes/compliance.py
-----------------------------
DPDP Act 2023 + NABH compliance endpoints.

Endpoints:
  GET  /api/compliance/nabh              — NABH checklist status
  GET  /api/compliance/dpdp/consent/{id} — Patient consent record
  POST /api/compliance/dpdp/erasure      — Right-to-erasure request
  GET  /api/compliance/audit-log         — CEO audit trail viewer
  GET  /api/compliance/dpdp/my-data/{id} — Patient's right to access own data
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import CurrentUser, require_any_staff, require_ceo
from audit.audit_log import log_action, get_client_ip
from database import get_db
from models.sql_models import AuditLog, NABHCheckpoint, Patient, PatientConsent
from models.schemas import ConsentRecord, ErasureRequest, NABHCheckpointResponse
from config import settings

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


# ── NABH Checklist ────────────────────────────────────────────────────────────
@router.get("/nabh", response_model=List[NABHCheckpointResponse])
async def get_nabh_checklist(
    domain: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_ceo),
):
    """NABH compliance checklist — 50 checkpoints by domain."""
    query = select(NABHCheckpoint)
    if domain:
        query = query.where(NABHCheckpoint.domain.ilike(f"%{domain}%"))
    if status_filter:
        query = query.where(NABHCheckpoint.status == status_filter)
    result = await db.execute(query.order_by(NABHCheckpoint.domain, NABHCheckpoint.checkpoint_code))
    return result.scalars().all()


@router.patch("/nabh/{checkpoint_id}")
async def update_nabh_checkpoint(
    checkpoint_id: int,
    status: str,
    reviewer: str,
    remarks: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_ceo),
):
    """Update NABH checkpoint status after internal audit."""
    result = await db.execute(select(NABHCheckpoint).where(NABHCheckpoint.id == checkpoint_id))
    cp = result.scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found")
    cp.status = status
    cp.reviewer = reviewer
    cp.remarks = remarks
    cp.last_reviewed = datetime.now(timezone.utc).date()
    await log_action(db, "UPDATE_NABH_CHECKPOINT", user.user_id, user.role, resource_type="NABHCheckpoint", resource_id=checkpoint_id)
    return {"message": "Updated", "checkpoint_code": cp.checkpoint_code, "status": status}


@router.get("/nabh/summary")
async def get_nabh_summary(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_ceo),
):
    """NABH compliance score at a glance."""
    result = await db.execute(
        select(NABHCheckpoint.status, func.count(NABHCheckpoint.id).label("count"))
        .group_by(NABHCheckpoint.status)
    )
    rows = {r.status: r.count for r in result.all()}
    total = sum(rows.values())
    compliant = rows.get("compliant", 0)
    score = round(compliant / total * 100, 1) if total else 0
    return {
        "total_checkpoints": total,
        "compliant": compliant,
        "partial": rows.get("partial", 0),
        "non_compliant": rows.get("non-compliant", 0),
        "compliance_score_pct": score,
        "nabh_status": "Ready" if score >= 85 else "In Progress" if score >= 60 else "Needs Attention",
    }


# ── DPDP — Consent Management ─────────────────────────────────────────────────
@router.get("/dpdp/consent/{patient_id}", response_model=List[ConsentRecord])
async def get_patient_consents(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_ceo),
):
    """Patient consent records (DPDP Act S.6)."""
    result = await db.execute(select(PatientConsent).where(PatientConsent.patient_id == patient_id))
    return result.scalars().all()


@router.post("/dpdp/erasure")
async def request_erasure(
    payload: ErasureRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    """
    Right to erasure workflow (DPDP Act S.13).
    Note: Medical records are anonymised (not hard deleted) to preserve
    clinical integrity and regulatory obligations.
    """
    result = await db.execute(select(Patient).where(Patient.id == payload.patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Anonymise PHI instead of deleting
    from encryption import encryptor
    patient.name_encrypted = encryptor.encrypt("ANONYMISED")
    patient.phone_encrypted = encryptor.encrypt_optional("ANONYMISED")
    patient.aadhaar_encrypted = encryptor.encrypt_optional("ANONYMISED")
    patient.aadhaar_hash = "ANONYMISED"
    patient.status = "anonymised"

    await log_action(
        db, "ERASURE_REQUEST", user.user_id, user.role,
        resource_type="Patient", resource_id=payload.patient_id,
        ip_address=get_client_ip(request),
        request_payload={"reason": payload.reason, "requestor": payload.requestor_name},
    )
    return {
        "message": "Patient record anonymised per DPDP Act 2023 S.13.",
        "patient_id": payload.patient_id,
        "anonymised_at": datetime.now(timezone.utc).isoformat(),
        "note": "Clinical data retained in anonymised form per NABH 7-year retention requirement.",
        "dpo_contact": settings.DPO_EMAIL,
    }


@router.get("/dpdp/my-data/{patient_id}")
async def get_patient_data_access(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_ceo),
    request: Request = None,
):
    """Right to access own data (DPDP Act S.12)."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    from encryption import encryptor
    await log_action(db, "DPDP_DATA_ACCESS_REQUEST", user.user_id, user.role, resource_type="Patient", resource_id=patient_id, ip_address=get_client_ip(request))

    return {
        "patient_id": patient_id,
        "data_held": ["name", "age", "gender", "diagnosis", "admission_dates", "insurance_claims"],
        "consent_given": True,  # Check from consent table in production
        "data_fiduciary": settings.HOSPITAL_NAME,
        "dpo_contact": {"name": settings.DPO_NAME, "email": settings.DPO_EMAIL, "phone": settings.DPO_PHONE},
        "right_to_correction": f"PATCH /api/patients/{patient_id}",
        "right_to_erasure": "POST /api/compliance/dpdp/erasure",
        "consent_form_version": settings.CONSENT_FORM_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Audit Log Viewer ──────────────────────────────────────────────────────────
@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, le=200),
    action: Optional[str] = None,
    user_role: Optional[str] = None,
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_ceo),
):
    """CEO-accessible audit trail. Returns last N days of access logs."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    query = select(AuditLog).where(AuditLog.timestamp >= cutoff).order_by(AuditLog.timestamp.desc())

    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if user_role:
        query = query.where(AuditLog.user_role == user_role)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": l.id, "timestamp": l.timestamp.isoformat(),
                "user_id": l.user_id, "user_role": l.user_role,
                "action": l.action, "resource_type": l.resource_type,
                "resource_id": l.resource_id, "ip_address": l.ip_address,
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "days_back": days_back,
    }
