"""
backend/main.py
----------------
FastAPI application entry point.

Features:
  - CORS restricted to frontend origin
  - Security headers middleware (CSP, X-Frame-Options, HSTS)
  - Rate limiting via slowapi
  - WebSocket for live KPI push every 30s
  - OpenAPI docs disabled in production
  - Graceful startup / shutdown with DB pool management
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Set

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from database import close_connections, init_db, get_neo4j_driver
from routes.analytics import router as analytics_router
from routes.finance import router as finance_router
from routes.patients import router as patients_router
from routes.ai_concierge import router as ai_router
from routes.compliance import router as compliance_router
from routes.auth_route import router as auth_router
from routes.hr_ot_insurance_appointments import (
    hr_router, ot_router, insurance_router, appointments_router,
)
from routes.export_route import router as export_router
from routes.ml_route import router as ml_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])

# ── WebSocket connection manager ──────────────────────────────────────────────
class WSManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        logger.info("WS connected. Total: %d", len(self.active))

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        logger.info("WS disconnected. Total: %d", len(self.active))

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.add(ws)
        self.active -= dead


ws_manager = WSManager()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting %s API — %s mode", settings.HOSPITAL_NAME, settings.APP_ENV)
    await init_db()
    get_neo4j_driver()  # Attempt Neo4j connection (graceful if unavailable)

    # Start WebSocket KPI broadcaster task
    task = asyncio.create_task(_kpi_broadcaster())
    yield
    task.cancel()
    await close_connections()
    logger.info("🔒 Shutdown complete")


async def _kpi_broadcaster():
    """Push live KPI updates to all connected WebSocket clients every 30s."""
    while True:
        await asyncio.sleep(30)
        if ws_manager.active:
            payload = {
                "type": "kpi_update",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hospital": settings.HOSPITAL_NAME,
                # In production: fetch real KPIs from DB
                "message": "KPI refresh — reload data",
            }
            await ws_manager.broadcast(payload)


# ── App init ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title=f"{settings.HOSPITAL_NAME} — CEO Dashboard API",
    description="Production-grade hospital BI dashboard backend with security, DPDP compliance, and AI concierge.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/redoc" if settings.APP_ENV == "development" else None,
    openapi_url="/openapi.json" if settings.APP_ENV == "development" else None,
)

# ── Rate limit error handler ──────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# ── Security headers middleware ───────────────────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    process_time = (time.time() - start) * 1000

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Process-Time"] = f"{process_time:.1f}ms"
    if settings.APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self' ws://localhost:* wss://localhost:*"
    )
    return response


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "hospital": settings.HOSPITAL_NAME,
        "env": settings.APP_ENV,
        "db": "sqlite" if settings.USE_SQLITE else "postgresql",
        "neo4j": "connected" if get_neo4j_driver() else "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── WebSocket endpoint ────────────────────────────────────────────────────────
@app.websocket("/ws/live-kpis")
async def ws_live_kpis(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── Register all routers ──────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(finance_router)
app.include_router(patients_router)
app.include_router(hr_router)
app.include_router(ot_router)
app.include_router(insurance_router)
app.include_router(appointments_router)
app.include_router(ai_router)
app.include_router(compliance_router)
app.include_router(export_router)
app.include_router(ml_router)


# ── Neo4j graph endpoint ──────────────────────────────────────────────────────
from models.schemas import GraphData
from models.graph_models import get_patient_graph, get_department_graph

@app.get("/api/graph/patients", response_model=GraphData, tags=["Graph Analytics"])
async def get_patient_graph_data(limit: int = 100):
    """Neo4j patient–doctor–department relationship graph."""
    driver = get_neo4j_driver()
    if not driver:
        return GraphData(nodes=[], edges=[], total_nodes=0, total_edges=0)
    return get_patient_graph(driver, limit)


@app.get("/api/graph/department/{dept_name}", response_model=GraphData, tags=["Graph Analytics"])
async def get_dept_graph(dept_name: str):
    """Neo4j department-focused subgraph."""
    driver = get_neo4j_driver()
    if not driver:
        return GraphData(nodes=[], edges=[], total_nodes=0, total_edges=0)
    return get_department_graph(driver, dept_name)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
