"""
backend/audit/audit_log.py
---------------------------
Immutable audit logging for all data access and AI queries.

Design:
  - Append-only: no UPDATE or DELETE operations on audit_log table.
  - Every patient record view, export, AI query is logged.
  - SHA-256 hash of request payload for tamper detection.
  - Compliant with DPDP Act 2023 data access obligations.
  - Retained for 7 years per NABH guidelines (AUDIT_LOG_RETAIN_DAYS=2555).
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.sql_models import AuditLog

logger = logging.getLogger(__name__)


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    user_role: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    session_id: Optional[str] = None,
    request_payload: Optional[dict] = None,
) -> None:
    """
    Append an entry to the immutable audit log.

    Actions should be uppercase_snake_case verbs:
      VIEW_PATIENT, EXPORT_PDF, AI_QUERY, LOGIN, LOGOUT,
      VIEW_FINANCE, VIEW_HR, VIEW_INSURANCE, ERASURE_REQUEST, etc.
    """
    data_hash = None
    summary = None

    if request_payload:
        payload_str = json.dumps(request_payload, sort_keys=True, default=str)
        data_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        # Summarise (truncate for storage)
        summary = payload_str[:500] if len(payload_str) > 500 else payload_str

    entry = AuditLog(
        timestamp=datetime.now(timezone.utc),
        user_id=user_id,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        session_id=session_id,
        request_summary=summary,
        data_hash=data_hash,
    )

    try:
        db.add(entry)
        await db.flush()  # Write immediately without waiting for commit
        logger.debug("🔍 Audit: %s | user=%s | resource=%s#%s", action, user_id, resource_type, resource_id)
    except Exception as exc:
        # Audit failure must never block the main operation
        logger.error("⚠️  Audit log write failed: %s", exc)


def get_client_ip(request) -> str:
    """Extract real client IP, respecting X-Forwarded-For header."""
    if hasattr(request, "headers"):
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return getattr(request.client, "host", "unknown")
    return "unknown"
