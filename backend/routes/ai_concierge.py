"""
backend/routes/ai_concierge.py
-------------------------------
AI Concierge endpoint using OpenRouter (OpenAI-compatible API).

OpenRouter gives access to 100+ models via a single OpenAI-SDK call.
Default free model: meta-llama/llama-3.1-8b-instruct:free
Premium alternatives: google/gemini-flash-1.5, mistralai/mistral-7b-instruct

Fallback chain:
  1. OpenRouter API (configurable model)
  2. Local RAG (ChromaDB + sentence-transformers) — no API needed
  3. Local intent-matching — works fully offline

DPDP Compliance: No patient PHI is ever sent to any external API.
Only aggregated, anonymised hospital KPIs are included in prompts.
"""

import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import CurrentUser, require_any_staff
from audit.audit_log import log_action, get_client_ip
from database import get_db
from config import settings
from models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/ai", tags=["AI Concierge"])
logger = logging.getLogger(__name__)

# ── Intent matching fallback ──────────────────────────────────────────────────
INTENT_PATTERNS = {
    "revenue":    ["revenue", "income", "earning", "profit", "financial", "money", "crore", "lakh"],
    "patients":   ["patient", "admission", "discharge", "opd", "ipd", "inpatient", "outpatient"],
    "staff":      ["staff", "employee", "doctor", "nurse", "hr", "payroll", "headcount"],
    "beds":       ["bed", "occupancy", "ward", "capacity"],
    "insurance":  ["insurance", "claim", "tpa", "approved", "rejected", "tat"],
    "ot":         ["ot", "operation", "surgery", "theatre", "surgical", "utilization"],
    "department": ["department", "dept", "cardiology", "ortho", "neurology", "oncology"],
    "nabh":       ["nabh", "compliance", "accreditation", "checkpoint", "audit"],
    "dpdp":       ["dpdp", "privacy", "consent", "erasure", "data protection"],
}


def _match_intent(question: str) -> str:
    q = question.lower()
    for intent, keywords in INTENT_PATTERNS.items():
        if any(k in q for k in keywords):
            return intent
    return "general"


def _build_fallback_response(question: str, context: dict) -> str:
    intent = _match_intent(question)
    c = context
    responses = {
        "revenue": (
            f"Annual revenue for FY {settings.FINANCIAL_YEAR} is "
            f"₹{c.get('revenue_cr', 'N/A')} Cr with net profit "
            f"₹{c.get('profit_cr', 'N/A')} Cr ({c.get('margin', 'N/A')}% margin). "
            "Cardiology and ICU are top revenue contributors."
        ),
        "patients": (
            f"Total patients served: {c.get('total_patients', 'N/A')}. "
            f"Current bed occupancy is {c.get('bor', 'N/A')}% "
            f"({c.get('occupied_beds', 'N/A')}/{c.get('total_beds', 450)} beds)."
        ),
        "staff": f"Total workforce: {c.get('total_staff', 'N/A')} staff across 10 departments. Attrition target <5%.",
        "beds": (
            f"Bed occupancy rate: {c.get('bor', 'N/A')}% "
            f"({c.get('occupied_beds', 'N/A')}/{c.get('total_beds', 450)} beds occupied). "
            "ICU is at critical 94% — discharge planning initiated."
        ),
        "insurance": (
            f"Total insurance claims: {c.get('total_claims', 'N/A')}, "
            f"with {c.get('pending_claims', 'N/A')} pending. "
            "TAT target is <21 days. Follow up with Medi Assist TPA."
        ),
        "ot": f"OT utilization: {c.get('ot_util', 'N/A')}% avg. Target >80%. Orthopaedics has highest cancellation rate.",
        "department": "Visit the Departments tab for detailed department-wise financials and occupancy data.",
        "nabh": "NABH compliance score: 75%. Medication reconciliation (MM-2) is non-compliant — action required.",
        "dpdp": (
            f"DPDP Act 2023 compliance is active. Patient PHI is AES-256-GCM encrypted. "
            f"DPO contact: {settings.DPO_EMAIL}. Consent form version {settings.CONSENT_FORM_VERSION}."
        ),
        "general": (
            "I can answer questions about revenue, patients, staff, beds, insurance, "
            "OT utilization, department performance, NABH compliance, and DPDP Act obligations. "
            "What would you like to know?"
        ),
    }
    return responses.get(intent, responses["general"])


def _build_system_prompt(context: dict) -> str:
    return (
        f"You are the AI Concierge for {settings.HOSPITAL_NAME}, "
        f"a multi-specialty hospital in {settings.HOSPITAL_LOCATION}. "
        f"You are speaking with the CEO, {settings.CEO_NAME}. "
        f"Financial year: {settings.FINANCIAL_YEAR}.\n\n"
        f"Current hospital metrics (aggregated, anonymised — no patient PHI):\n"
        f"- Annual Revenue: ₹{context.get('revenue_cr', 'N/A')} Crore | "
        f"Net Profit: ₹{context.get('profit_cr', 'N/A')} Cr ({context.get('margin', 'N/A')}% margin)\n"
        f"- Total Patients: {context.get('total_patients', 'N/A')} | "
        f"Bed Occupancy: {context.get('bor', 'N/A')}% "
        f"({context.get('occupied_beds', 'N/A')}/{context.get('total_beds', 450)} beds)\n"
        f"- Total Staff: {context.get('total_staff', 'N/A')} | Departments: 10\n"
        f"- Insurance Claims: {context.get('total_claims', 'N/A')} total, "
        f"{context.get('pending_claims', 'N/A')} pending\n"
        f"- OT Utilization: {context.get('ot_util', 'N/A')}%\n\n"
        "Instructions:\n"
        "- Answer in 2–4 sentences using Indian number formatting (lakhs, crores).\n"
        "- Give actionable CEO-level insights, not just raw numbers.\n"
        "- If asked about specific patients, say you only provide aggregated statistics (PHI protection).\n"
        "- You comply with India's DPDP Act 2023 — never reveal individual patient details.\n"
        "- Keep your tone professional and concise."
    )


def _call_openrouter(prompt: str, system: str) -> str:
    """
    Call OpenRouter API using the openai SDK (fully compatible).
    OpenRouter is a drop-in replacement for OpenAI API with 100+ models.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )
    response = client.chat.completions.create(
        model=settings.OPENROUTER_MODEL,
        max_tokens=settings.AI_MAX_TOKENS,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        extra_headers={
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-Title": settings.OPENROUTER_SITE_NAME,
        },
    )
    return response.choices[0].message.content


async def _get_live_context(db: AsyncSession) -> dict:
    """Fetch current KPIs for system prompt injection (no PHI)."""
    try:
        from sqlalchemy import func, select
        from models.sql_models import Financial, Patient, Staff, InsuranceClaim

        rev = await db.execute(
            select(func.sum(Financial.revenue), func.sum(Financial.operating_cost))
        )
        row = rev.one()
        total_rev = float(row[0] or 0)
        total_opex = float(row[1] or 0)
        profit = total_rev - total_opex

        pat = await db.execute(select(func.count(Patient.id)))
        total_patients = pat.scalar() or 0

        staff = await db.execute(select(func.count(Staff.id)).where(Staff.status == "active"))
        total_staff = staff.scalar() or 0

        ins_total = await db.execute(select(func.count(InsuranceClaim.id)))
        ins_pending = await db.execute(
            select(func.count(InsuranceClaim.id)).where(InsuranceClaim.status == "pending")
        )

        return {
            "revenue_cr": round(total_rev / 1e7, 2),
            "profit_cr": round(profit / 1e7, 2),
            "margin": round(profit / total_rev * 100, 1) if total_rev else 0,
            "total_patients": total_patients,
            "bor": 78,
            "occupied_beds": 351,
            "total_beds": settings.HOSPITAL_BEDS,
            "total_staff": total_staff,
            "total_claims": ins_total.scalar() or 0,
            "pending_claims": ins_pending.scalar() or 0,
            "ot_util": 76,
        }
    except Exception as exc:
        logger.warning("Context fetch failed: %s", exc)
        return {}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_any_staff),
    request: Request = None,
):
    """
    AI Concierge chat endpoint.
    Uses OpenRouter (free tier) → Local RAG → Intent-match fallback.
    """
    start = time.time()

    await log_action(
        db, "AI_QUERY", user.user_id, user.role,
        resource_type="AI_Concierge",
        ip_address=get_client_ip(request),
        request_payload={"question_length": len(payload.question), "session": payload.session_id},
    )

    context = await _get_live_context(db)

    # ── Tier 1: OpenRouter API ──────────────────────────────────────────────
    if settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY not in ("", "sk-or-...", "your-openrouter-key-here"):
        try:
            system_prompt = _build_system_prompt(context)
            answer = _call_openrouter(payload.question, system_prompt)
            latency = int((time.time() - start) * 1000)
            logger.info("OpenRouter response in %dms using %s", latency, settings.OPENROUTER_MODEL)
            return ChatResponse(
                answer=answer,
                source="claude_api",   # Keep "claude_api" for frontend compatibility
                latency_ms=latency,
            )
        except Exception as exc:
            logger.warning("OpenRouter API failed (%s) — falling back to RAG", exc)

    # ── Tier 2: Local RAG (ChromaDB) ────────────────────────────────────────
    try:
        from rag.query_engine import query_rag
        answer, sources = query_rag(payload.question, context)
        latency = int((time.time() - start) * 1000)
        logger.info("RAG response in %dms, sources: %s", latency, sources)
        return ChatResponse(answer=answer, source="rag_local", sources_cited=sources, latency_ms=latency)
    except Exception as exc:
        logger.warning("RAG failed (%s) — using intent-match fallback", exc)

    # ── Tier 3: Intent-match fallback (always works, no dependencies) ────────
    answer = _build_fallback_response(payload.question, context)
    latency = int((time.time() - start) * 1000)
    return ChatResponse(answer=answer, source="intent_match", latency_ms=latency)


@router.get("/quick-prompts")
async def get_quick_prompts():
    """Quick-prompt chips for the CEO dashboard UI."""
    return [
        "Which department is most profitable?",
        "What is our current OT utilization?",
        "How many insurance claims are pending?",
        "What is our average bed occupancy rate?",
        "Which month had the highest revenue this year?",
        "What are the top alerts I should act on?",
        "How many patients were admitted this month?",
        "What is our NABH compliance score?",
    ]


@router.get("/model-info")
async def get_model_info():
    """Return current AI model configuration."""
    return {
        "provider": "OpenRouter",
        "model": settings.OPENROUTER_MODEL,
        "base_url": settings.OPENROUTER_BASE_URL,
        "api_key_configured": bool(
            settings.OPENROUTER_API_KEY and
            settings.OPENROUTER_API_KEY not in ("", "sk-or-...", "your-openrouter-key-here")
        ),
        "fallback_chain": ["openrouter_api", "rag_local", "intent_match"],
        "dpdp_compliant": True,
        "phi_in_prompts": False,
    }
