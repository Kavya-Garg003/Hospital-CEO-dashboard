"""
backend/routes/finance.py
--------------------------
Financial P&L routes.
Accessible by: CEO (all), Finance role (all), Dept Head (own dept only).
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import get_current_user, CurrentUser, require_any_staff, require_ceo_or_finance
from audit.audit_log import log_action, get_client_ip
from database import get_db
from models.sql_models import Department, Financial
from models.schemas import DeptFinancialSummary, MonthlyFinancialSummary, FinancialResponse

router = APIRouter(prefix="/api/finance", tags=["Finance"])


async def _get_monthly_revenue(db: AsyncSession) -> list:
    """Helper used by analytics alert engine."""
    result = await db.execute(
        select(
            Financial.month, Financial.year,
            func.sum(Financial.revenue).label("revenue"),
            func.sum(Financial.operating_cost).label("opex"),
            func.sum(Financial.insurance_revenue).label("insurance"),
            func.sum(Financial.oop_revenue).label("oop"),
        ).group_by(Financial.year, Financial.month)
        .order_by(Financial.year, Financial.month)
    )
    rows = result.all()
    return [
        {
            "month": r.month,
            "year": r.year,
            "revenue": r.revenue or Decimal(0),
            "opex": r.opex or Decimal(0),
            "insurance": r.insurance or Decimal(0),
            "oop": r.oop or Decimal(0),
        }
        for r in rows
    ]


async def _get_dept_financials(db: AsyncSession) -> list:
    """Department P&L summary — used by analytics and finance routes."""
    result = await db.execute(
        select(
            Department.name.label("department"),
            func.sum(Financial.revenue).label("revenue"),
            func.sum(Financial.operating_cost).label("cost"),
        )
        .join(Financial, Financial.department_id == Department.id)
        .group_by(Department.name)
        .order_by(func.sum(Financial.revenue).desc())
    )
    rows = result.all()
    data = []
    for r in rows:
        rev = float(r.revenue or 0)
        cost = float(r.cost or 0)
        profit = rev - cost
        margin = (profit / rev * 100) if rev > 0 else 0
        data.append({
            "department": r.department,
            "revenue": Decimal(rev),
            "cost": Decimal(cost),
            "profit": Decimal(profit),
            "margin": round(margin, 1),
        })
    return data


@router.get("/monthly", response_model=List[MonthlyFinancialSummary])
async def get_monthly_summary(
    year: Optional[int] = Query(None, description="Filter by financial year"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    """Monthly revenue, opex, and profit trend."""
    await log_action(db, "VIEW_FINANCE_MONTHLY", user.user_id, user.role, ip_address=get_client_ip(request))

    query = select(
        Financial.month, Financial.year,
        func.sum(Financial.revenue).label("revenue"),
        func.sum(Financial.operating_cost).label("opex"),
        func.sum(Financial.insurance_revenue).label("insurance"),
        func.sum(Financial.oop_revenue).label("oop"),
    ).group_by(Financial.year, Financial.month).order_by(Financial.year, Financial.month)

    if year:
        query = query.where(Financial.year == year)

    result = await db.execute(query)
    rows = result.all()

    summaries = []
    for r in rows:
        rev = r.revenue or Decimal(0)
        opex = r.opex or Decimal(0)
        ins = r.insurance or Decimal(0)
        oop = r.oop or Decimal(0)
        profit = rev - opex
        margin = float(profit / rev * 100) if rev else 0
        summaries.append(MonthlyFinancialSummary(
            month=r.month, year=r.year,
            total_revenue=rev, total_opex=opex,
            insurance_revenue=ins, oop_revenue=oop,
            net_profit=profit, profit_margin=round(margin, 1),
        ))
    return summaries


@router.get("/departments", response_model=List[DeptFinancialSummary])
async def get_dept_financials(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    """Department-wise P&L — revenue, cost, profit, margin."""
    await log_action(db, "VIEW_FINANCE_DEPTS", user.user_id, user.role, ip_address=get_client_ip(request))
    rows = await _get_dept_financials(db)

    # Dept heads see only their own department
    if user.role == "dept_head" and user.department_id:
        dept_result = await db.execute(
            select(Department.name).where(Department.id == user.department_id)
        )
        own_dept = dept_result.scalar()
        rows = [r for r in rows if r["department"] == own_dept]

    return [DeptFinancialSummary(**r) for r in rows]


@router.get("/breakeven")
async def get_breakeven_analysis(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_ceo_or_finance),
):
    """Break-even analysis — fixed vs variable costs."""
    result = await db.execute(
        select(
            func.sum(Financial.revenue).label("total_revenue"),
            func.sum(Financial.operating_cost).label("total_opex"),
        )
    )
    row = result.one()
    rev = float(row.total_revenue or 0)
    opex = float(row.total_opex or 0)
    # Approximate: fixed cost ~60% of opex, variable ~40%
    fixed_cost = opex * 0.60
    variable_cost_ratio = (opex * 0.40) / rev if rev > 0 else 0
    breakeven_revenue = fixed_cost / (1 - variable_cost_ratio) if variable_cost_ratio < 1 else 0
    return {
        "total_revenue": rev,
        "total_opex": opex,
        "fixed_cost_estimate": fixed_cost,
        "variable_cost_ratio": round(variable_cost_ratio, 3),
        "breakeven_revenue": round(breakeven_revenue, 2),
        "current_surplus": round(rev - breakeven_revenue, 2),
        "margin_of_safety_pct": round(((rev - breakeven_revenue) / rev * 100) if rev > 0 else 0, 1),
    }
