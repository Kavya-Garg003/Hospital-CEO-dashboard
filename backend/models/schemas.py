"""
backend/models/schemas.py
--------------------------
Pydantic v2 schemas for API request/response validation.

Naming convention:
  *Base    — shared fields
  *Create  — request body for POST (includes PHI in plaintext — decrypted before return)
  *Response — API response (PHI masked/decrypted based on role)
  *Summary  — lightweight version for lists
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth / Users ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int  # seconds

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    department_id: Optional[int] = None


# ── Departments ───────────────────────────────────────────────────────────────

class DepartmentResponse(BaseModel):
    id: int
    name: str
    head_doctor: Optional[str]
    total_beds: int
    color_hex: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Patients ──────────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=0, le=150)
    gender: Literal["Male", "Female", "Other"]
    department_id: int
    admission_date: date
    discharge_date: Optional[date] = None
    patient_type: Literal["inpatient", "outpatient", "emergency"]
    icd_code: Optional[str] = None
    diagnosis: Optional[str] = None
    insurance_provider: Optional[str] = None
    bill_amount: Optional[Decimal] = None
    phone: Optional[str] = None
    aadhaar: Optional[str] = None
    consent_given: bool = False


class PatientResponse(BaseModel):
    id: int
    name: str              # Decrypted or masked based on role
    age: int
    gender: str
    department_id: int
    department_name: Optional[str] = None
    admission_date: Optional[date]
    discharge_date: Optional[date]
    patient_type: str
    icd_code: Optional[str]
    diagnosis: Optional[str]   # Decrypted or masked
    insurance_provider: Optional[str]
    bill_amount: Optional[Decimal]
    status: str
    readmission_risk_score: Optional[int] = None

    model_config = {"from_attributes": True}


class PatientSummary(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    patient_type: str
    status: str
    admission_date: Optional[date]

    model_config = {"from_attributes": True}


# ── Financials ────────────────────────────────────────────────────────────────

class FinancialResponse(BaseModel):
    id: int
    month: str
    year: int
    department_id: Optional[int]
    department_name: Optional[str] = None
    revenue: Decimal
    operating_cost: Decimal
    insurance_revenue: Decimal
    oop_revenue: Decimal

    model_config = {"from_attributes": True}


class MonthlyFinancialSummary(BaseModel):
    month: str
    year: int
    total_revenue: Decimal
    total_opex: Decimal
    insurance_revenue: Decimal
    oop_revenue: Decimal
    net_profit: Decimal
    profit_margin: float


class DeptFinancialSummary(BaseModel):
    department: str
    revenue: Decimal
    cost: Decimal
    profit: Decimal
    margin: float


# ── Staff / HR ────────────────────────────────────────────────────────────────

class StaffResponse(BaseModel):
    id: int
    name: str
    role: str
    department_id: Optional[int]
    department_name: Optional[str] = None
    monthly_salary: Decimal
    status: str
    working_hours_per_week: int
    overtime_hours: int

    model_config = {"from_attributes": True}


class HRSummary(BaseModel):
    role: str
    count: int
    present: int
    on_leave: int
    attrition_pct: float
    monthly_salary: Decimal
    total_payroll: Decimal
    overtime_hrs: int


# ── OT Records ────────────────────────────────────────────────────────────────

class OTResponse(BaseModel):
    id: int
    department_id: int
    department_name: Optional[str] = None
    surgery_type: str
    scheduled_date: Optional[date]
    actual_date: Optional[date]
    status: str
    duration_minutes: Optional[int]
    cancellation_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class OTSummary(BaseModel):
    department: str
    scheduled: int
    completed: int
    cancelled: int
    avg_duration_min: float
    utilization_pct: float


# ── Insurance Claims ──────────────────────────────────────────────────────────

class InsuranceClaimResponse(BaseModel):
    id: int
    patient_id: int
    insurer: str
    claim_amount: Decimal
    approved_amount: Optional[Decimal]
    status: str
    submitted_date: Optional[date]
    resolved_date: Optional[date]
    tat_days: Optional[int]
    rejection_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class InsurerSummary(BaseModel):
    insurer: str
    total_claims: int
    approved: int
    pending: int
    rejected: int
    total_value: Decimal
    avg_tat_days: float
    rejection_rate: float


# ── Appointments ──────────────────────────────────────────────────────────────

class AppointmentResponse(BaseModel):
    id: int
    patient_name: str          # Decrypted or masked
    doctor_id: Optional[int]
    doctor_name: Optional[str] = None
    department_id: Optional[int]
    department_name: Optional[str] = None
    appointment_date: Optional[date]
    appointment_time: Optional[time]
    appointment_type: str
    status: str

    model_config = {"from_attributes": True}


# ── Overview / KPIs ───────────────────────────────────────────────────────────

class KPISummary(BaseModel):
    annual_revenue: Decimal
    net_profit: Decimal
    profit_margin: float
    total_patients: int
    bed_occupancy_pct: float
    occupied_beds: int
    total_beds: int
    total_staff: int
    total_insurance_claims: int
    pending_insurance_claims: int
    avg_los_days: float
    ot_utilization_pct: float
    as_of: datetime


# ── Alerts ────────────────────────────────────────────────────────────────────

class Alert(BaseModel):
    alert_type: Literal["danger", "warn", "info", "success"]
    icon: str
    message: str
    department: Optional[str] = None
    rule_triggered: str         # Human-readable rule explanation (explainability)
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    recommendation: Optional[str] = None


# ── AI Concierge ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    source: Literal["claude_api", "rag_local", "intent_match"]
    sources_cited: List[str] = []
    latency_ms: int


# ── ML Predictions ────────────────────────────────────────────────────────────

class BedForecast(BaseModel):
    department: str
    date: date
    predicted_occupancy: float
    lower_bound: float
    upper_bound: float
    confidence: float


class ReadmissionRisk(BaseModel):
    patient_id: int
    risk_score: int              # 0–100
    risk_level: Literal["low", "medium", "high"]
    top_factors: List[dict]      # [{"factor": "Age > 70", "contribution": 22}]
    recommendation: str


# ── DPDP Compliance ───────────────────────────────────────────────────────────

class ConsentRecord(BaseModel):
    patient_id: int
    consent_type: str
    given_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    version: str

    model_config = {"from_attributes": True}


class ErasureRequest(BaseModel):
    patient_id: int
    reason: str
    requestor_name: str
    requestor_relation: str      # "self" / "guardian" / "legal_representative"


# ── NABH Compliance ───────────────────────────────────────────────────────────

class NABHCheckpointResponse(BaseModel):
    id: int
    domain: str
    checkpoint_code: str
    description: str
    status: str
    last_reviewed: Optional[date]
    reviewer: Optional[str]
    remarks: Optional[str]

    model_config = {"from_attributes": True}


# ── Neo4j Graph ───────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    type: str        # Patient / Doctor / Department / Diagnosis
    properties: dict = {}

class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    properties: dict = {}

class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
