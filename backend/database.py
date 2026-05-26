"""
backend/database.py
--------------------
Database connection management for:
  1. PostgreSQL / SQLite (via SQLAlchemy async engine)
  2. Neo4j (via official neo4j-python-driver)

Design:
  - All DB access through async sessions (asyncpg / aiosqlite).
  - Neo4j driver is a module-level singleton.
  - Connection pools configured for production loads.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)

# ── SQLAlchemy — Async Engine ─────────────────────────────────────────────────

def _build_db_url() -> str:
    """Convert sync DB URLs to async driver variants (idempotent)."""
    url = settings.effective_db_url
    # Already an async URL — return as-is
    if "asyncpg" in url or "aiosqlite" in url:
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


_db_url = _build_db_url()

# SQLite and PostgreSQL need different engine kwargs
_engine_kwargs = {
    "echo": settings.APP_ENV == "development",
    "pool_pre_ping": True,
}
if not settings.USE_SQLITE:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
else:
    # SQLite: single connection, thread-safe check bypassed for async
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables (used by seed_data.py and tests)."""
    async with engine.begin() as conn:
        from models.sql_models import Base as ModelBase  # noqa: F401 — import to register models
        await conn.run_sync(ModelBase.metadata.create_all)
    logger.info("✅ Database tables initialised")


# ── Neo4j Driver ─────────────────────────────────────────────────────────────

_neo4j_driver = None


def get_neo4j_driver():
    """
    Lazy singleton for Neo4j driver.
    Returns None if Neo4j is unavailable (graceful degradation).
    """
    global _neo4j_driver
    if _neo4j_driver is not None:
        return _neo4j_driver
    try:
        from neo4j import GraphDatabase
        _neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=60,
        )
        _neo4j_driver.verify_connectivity()
        logger.info("✅ Neo4j connected at %s", settings.NEO4J_URI)
    except Exception as exc:
        logger.warning(
            "⚠️  Neo4j unavailable (%s). Graph features will return empty data. "
            "Start Neo4j Community Server to enable graph analytics.",
            exc,
        )
        _neo4j_driver = None
    return _neo4j_driver


def get_neo4j_session():
    """Context manager for a Neo4j session."""
    driver = get_neo4j_driver()
    if driver is None:
        return None
    return driver.session(database=settings.NEO4J_DATABASE)


async def close_connections() -> None:
    """Shutdown hook — closes all database connections."""
    await engine.dispose()
    global _neo4j_driver
    if _neo4j_driver:
        _neo4j_driver.close()
        _neo4j_driver = None
    logger.info("🔒 All database connections closed")
