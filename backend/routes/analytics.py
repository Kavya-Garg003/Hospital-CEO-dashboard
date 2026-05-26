"""
backend/routes/analytics.py
----------------------------
Overview / KPI aggregation endpoint.
Returns all metrics for the CEO landing page.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import get_current_user, CurrentUser, require_any_staff
from audit.audit_log import log_action, get_client_ip
from database import get_db
from models.sql_models import Department, Financial, Patient, Staff, InsuranceClaim, OTRecord
from models.schemas import KPISummary, Alert
from config import settings

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def generate_alerts(data: dict) -> List[Alert]:
    """
    Rule-based alert engine — generates explainable alerts with thresholds.
    Every alert includes the rule that triggered it (explainability).
    """
    alerts = []
    s = settings

    # Bed occupancy alerts
    for dept in data.get("bed_occupancy", []):
        if dept["total_beds"] > 0:
            pct = (dept["occupied"] / dept["total_beds"]) * 100
            if pct > s.BED_OCCUPANCY_CRITICAL_PCT:
                alerts.append(Alert(
                    alert_type="danger", icon="🚨",
                    message=f"{dept['name']} at {pct:.0f}% occupancy — {dept['total_beds'] - dept['occupied']} beds remaining.",
                    department=dept["name"],
                    rule_triggered=f"Bed occupancy exceeded critical threshold ({s.BED_OCCUPANCY_CRITICAL_PCT}%)",
                    threshold_value=float(s.BED_OCCUPANCY_CRITICAL_PCT),
                    actual_value=round(pct, 1),
                    recommendation="Initiate discharge planning and consider transferring stable patients.",
                ))
            elif pct > s.BED_OCCUPANCY_WARNING_PCT:
                alerts.append(Alert(
                    alert_type="warn", icon="⚠️",
                    message=f"{dept['name']} bed occupancy at {pct:.0f}% — approaching capacity.",
                    department=dept["name"],
                    rule_triggered=f"Bed occupancy exceeded warning threshold ({s.BED_OCCUPANCY_WARNING_PCT}%)",
                    threshold_value=float(s.BED_OCCUPANCY_WARNING_PCT),
                    actual_value=round(pct, 1),
                    recommendation="Monitor closely. Prepare contingency beds in adjacent wards.",
                ))

    # Insurance TAT alerts
    for ins in data.get("insurance_summary", []):
        if ins["avg_tat_days"] > s.INSURANCE_TAT_CRITICAL_DAYS:
            alerts.append(Alert(
                alert_type="danger", icon="🚨",
                message=f"{ins['insurer']} avg TAT {ins['avg_tat_days']:.0f} days — severely delayed.",
                rule_triggered=f"Insurance TAT exceeded critical threshold ({s.INSURANCE_TAT_CRITICAL_DAYS} days)",
                threshold_value=float(s.INSURANCE_TAT_CRITICAL_DAYS),
                actual_value=ins["avg_tat_days"],
                recommendation="Escalate to TPA relationship manager. Review claim documentation completeness.",
            ))
        elif ins["avg_tat_days"] > s.INSURANCE_TAT_WARNING_DAYS:
            alerts.append(Alert(
                alert_type="warn", icon="⚠️",
                message=f"{ins['insurer']} TAT {ins['avg_tat_days']:.0f} days — approaching 21-day target.",
                rule_triggered=f"Insurance TAT exceeded warning threshold ({s.INSURANCE_TAT_WARNING_DAYS} days)",
                threshold_value=float(s.INSURANCE_TAT_WARNING_DAYS),
                actual_value=ins["avg_tat_days"],
                recommendation="Follow up with TPA. Ensure all supporting documents are submitted.",
            ))

    # Revenue MoM drop
    rev_trend = data.get("revenue_trend", [])
    if len(rev_trend) >= 2:
        prev, curr = float(rev_trend[-2]["revenue"]), float(rev_trend[-1]["revenue"])
        if prev > 0:
            drop_pct = ((prev - curr) / prev) * 100
            if drop_pct > s.REVENUE_DROP_CRITICAL_PCT:
                alerts.append(Alert(
                    alert_type="danger", icon="🚨",
                    message=f"Revenue declined {drop_pct:.1f}% month-over-month — requires immediate CEO attention.",
                    rule_triggered=f"Revenue MoM decline exceeded critical threshold ({s.REVENUE_DROP_CRITICAL_PCT}%)",
                    threshold_value=float(s.REVENUE_DROP_CRITICAL_PCT),
                    actual_value=round(drop_pct, 1),
                    recommendation="Review OPD volume, surgery cancellations, and insurance claim delays.",
                ))

    # OT cancellation alerts
    for dept in data.get("ot_summary", []):
        if dept["scheduled"] > 0:
            cancel_rate = (dept["cancelled"] / dept["scheduled"]) * 100
            if cancel_rate > s.OT_CANCELLATION_CRITICAL_PCT:
                alerts.append(Alert(
                    alert_type="warn", icon="⚠️",
                    message=f"OT cancellation rate in {dept['department']} is {cancel_rate:.0f}% — above {s.OT_CANCELLATION_CRITICAL_PCT}% threshold.",
                    department=dept["department"],
                    rule_triggered=f"OT cancellation exceeded critical threshold ({s.OT_CANCELLATION_CRITICAL_PCT}%)",
                    threshold_value=float(s.OT_CANCELLATION_CRITICAL_PCT),
                    actual_value=round(cancel_rate, 1),
                    recommendation="Audit pre-operative evaluation process and patient preparation protocols.",
                ))

    # Top department insight
    dept_financials = data.get("dept_financials", [])
    if dept_financials:
        top = max(dept_financials, key=lambda x: x.get("margin", 0))
        alerts.append(Alert(
            alert_type="info", icon="💡",
            message=f"{top['department']} leads with {top['margin']:.1f}% net margin — consider capacity expansion.",
            rule_triggered="Top performing department insight (informational)",
            recommendation=f"Review bed/staff allocation to {top['department']} to maximise revenue.",
        ))

    return alerts


@router.get("/overview", response_model=KPISummary)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    """CEO overview KPIs — aggregated from all departments."""
    await log_action(db, "VIEW_OVERVIEW", user.user_id, user.role, ip_address=get_client_ip(request))

    # Revenue & profit
    rev_result = await db.execute(
        select(func.sum(Financial.revenue), func.sum(Financial.operating_cost))
    )
    total_rev, total_opex = rev_result.one()
    total_rev = total_rev or Decimal(0)
    total_opex = total_opex or Decimal(0)
    net_profit = total_rev - total_opex

    # Patients
    pat_count = await db.execute(select(func.count(Patient.id)))
    total_patients = pat_count.scalar() or 0

    # Beds
    bed_result = await db.execute(select(func.sum(Department.total_beds)))
    total_beds = bed_result.scalar() or 450

    # Approximate current occupancy from patients with no discharge date
    occ_result = await db.execute(
        select(func.count(Patient.id)).where(
            Patient.status == "active", Patient.patient_type == "inpatient"
        )
    )
    occupied_beds = min(occ_result.scalar() or 0, total_beds)
    bor = (occupied_beds / total_beds * 100) if total_beds > 0 else 0

    # Staff
    staff_count = await db.execute(select(func.count(Staff.id)).where(Staff.status == "active"))
    total_staff = staff_count.scalar() or 0

    # Insurance
    ins_total = await db.execute(select(func.count(InsuranceClaim.id)))
    ins_pending = await db.execute(
        select(func.count(InsuranceClaim.id)).where(InsuranceClaim.status == "pending")
    )

    # OT utilization (avg)
    ot_result = await db.execute(
        select(
            func.count(OTRecord.id).label("total"),
            func.sum(func.cast(OTRecord.status == "completed", int)).label("completed"),
        )
    )
    ot_row = ot_result.one()
    ot_util = (ot_row.completed / ot_row.total * 100) if ot_row.total else 0

    return KPISummary(
        annual_revenue=total_rev,
        net_profit=net_profit,
        profit_margin=round(float(net_profit / total_rev * 100) if total_rev else 0, 1),
        total_patients=total_patients,
        bed_occupancy_pct=round(bor, 1),
        occupied_beds=occupied_beds,
        total_beds=total_beds,
        total_staff=total_staff,
        total_insurance_claims=ins_total.scalar() or 0,
        pending_insurance_claims=ins_pending.scalar() or 0,
        avg_los_days=4.2,  # Computed from patient LOS in full implementation
        ot_utilization_pct=round(ot_util, 1),
        as_of=datetime.now(timezone.utc),
    )


@router.get("/alerts", response_model=List[Alert])
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
):
    """Rule-based alert engine with explainability."""
    # Gather data needed for rule engine
    from routes.finance import _get_dept_financials, _get_monthly_revenue
    from routes.ot import _get_ot_summary
    from routes.insurance import _get_insurer_summary
    from routes.patients import _get_bed_occupancy

    data = {
        "bed_occupancy": await _get_bed_occupancy(db),
        "dept_financials": await _get_dept_financials(db),
        "revenue_trend": await _get_monthly_revenue(db),
        "ot_summary": await _get_ot_summary(db),
        "insurance_summary": await _get_insurer_summary(db),
    }
    return generate_alerts(data)
