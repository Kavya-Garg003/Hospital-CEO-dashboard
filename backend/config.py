"""
backend/config.py
-----------------
Centralised settings using pydantic-settings.
All values loaded from .env — never hard-coded.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ─────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Hospital Identity ────────────────────────────────────
    HOSPITAL_NAME: str = "Aarogya Multi-Specialty Hospital"
    HOSPITAL_LOCATION: str = "Chennai, Tamil Nadu"
    CEO_NAME: str = "Dr. CEO"
    HOSPITAL_BEDS: int = 450
    FINANCIAL_YEAR: str = "2024-25"

    # ── Database — Relational ────────────────────────────────
    USE_SQLITE: bool = False
    DATABASE_URL: str = "postgresql://hospital_user:hospital_pass@localhost:5432/hospital_db"
    SQLITE_URL: str = "sqlite:///./hospital.db"

    @property
    def effective_db_url(self) -> str:
        return self.SQLITE_URL if self.USE_SQLITE else self.DATABASE_URL

    # ── Database — Neo4j ─────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"

    # ── AI / LLM (OpenRouter — OpenAI-compatible) ──────────────
    # Get your free key at https://openrouter.ai
    OPENROUTER_API_KEY: str = ""
    # Free models: meta-llama/llama-3.1-8b-instruct:free
    # Premium (cheap): google/gemini-flash-1.5, mistralai/mistral-7b-instruct
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    AI_MAX_TOKENS: int = 1000
    # Site info sent to OpenRouter (required by their API)
    OPENROUTER_SITE_URL: str = "http://localhost:5173"
    OPENROUTER_SITE_NAME: str = "Aarogya Hospital Dashboard"

    # ── Vector Store ──────────────────────────────────────────
    CHROMA_DB_PATH: str = "./chroma_store"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Security — JWT ────────────────────────────────────────
    JWT_PRIVATE_KEY_PATH: str = "./keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "./keys/public.pem"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Security — Encryption ────────────────────────────────
    ENCRYPTION_KEY: str = "0" * 64  # Placeholder — MUST be overridden in .env

    # ── CORS ─────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # ── Rate Limiting ────────────────────────────────────────
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AI_CHAT: str = "10/minute"

    # ── Compliance ───────────────────────────────────────────
    DPO_NAME: str = "Data Protection Officer"
    DPO_EMAIL: str = "dpo@hospital.in"
    DPO_PHONE: str = "+91-0000000000"
    CONSENT_FORM_VERSION: str = "1.0"

    # ── Export ───────────────────────────────────────────────
    PDF_EXPORT_PATH: str = "./exports/pdf"
    EXCEL_EXPORT_PATH: str = "./exports/excel"

    # ── Logging ──────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    AUDIT_LOG_RETAIN_DAYS: int = 2555  # 7 years (NABH)

    # ── Thresholds (customizable per hospital config) ─────────
    BED_OCCUPANCY_WARNING_PCT: int = 80
    BED_OCCUPANCY_CRITICAL_PCT: int = 90
    INSURANCE_TAT_WARNING_DAYS: int = 21
    INSURANCE_TAT_CRITICAL_DAYS: int = 30
    OT_CANCELLATION_WARNING_PCT: int = 10
    OT_CANCELLATION_CRITICAL_PCT: int = 15
    REVENUE_DROP_WARNING_PCT: int = 3
    REVENUE_DROP_CRITICAL_PCT: int = 5
    ATTRITION_WARNING_PCT: int = 5
    ATTRITION_CRITICAL_PCT: int = 8


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — loaded once on first call."""
    return Settings()


settings = get_settings()
