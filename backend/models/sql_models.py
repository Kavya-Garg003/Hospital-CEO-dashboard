"""
backend/models/sql_models.py
-----------------------------
SQLAlchemy ORM models for all relational tables.

PHI encryption policy:
  Columns marked # [ENCRYPTED] store AES-256-GCM ciphertext.
  Decryption happens in the route layer, not here — keeping the ORM
  layer storage-agnostic.

Audit notes:
  All models include created_at / updated_at timestamps.
  The audit_log table is append-only (no UPDATE/DELETE in routes).
"""

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Index,
    Integer, Numeric, String, Text, Time, func,
)
from sqlalchemy.orm import relationship

from database import Base


# ── Departments ───────────────────────────────────────────────────────────────
class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    head_doctor = Column(String(100))
    total_beds = Column(Integer, default=0)
    color_hex = Column(String(7), default="#3b82f6")
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    patients = relationship("Patient", back_populates="department")
    staff = relationship("Staff", back_populates="department")
    financials = relationship("Financial", back_populates="department")
    ot_records = relationship("OTRecord", back_populates="department")
    appointments = relationship("Appointment", back_populates="department")


# ── Patients ──────────────────────────────────────────────────────────────────
class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        Index("ix_patients_department_id", "department_id"),
        Index("ix_patients_admission_date", "admission_date"),
        Index("ix_patients_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    # PHI — stored AES-256-GCM encrypted
    name_encrypted = Column(Text, nullable=False)                # [ENCRYPTED] Full name
    phone_encrypted = Column(Text)                               # [ENCRYPTED] Phone number
    aadhaar_hash = Column(String(64))                            # SHA-256 hash for dedup
    aadhaar_encrypted = Column(Text)                             # [ENCRYPTED] Aadhaar number
    diagnosis_encrypted = Column(Text)                           # [ENCRYPTED] Diagnosis text

    # Non-PHI fields (stored plain)
    age = Column(Integer)
    gender = Column(String(10))
    department_id = Column(Integer, ForeignKey("departments.id"))
    admission_date = Column(Date)
    discharge_date = Column(Date)
    patient_type = Column(String(20))        # inpatient / outpatient / emergency
    icd_code = Column(String(10))            # ICD-10 diagnosis code (not PHI)
    insurance_provider = Column(String(100))
    bill_amount = Column(Numeric(12, 2))
    status = Column(String(20), default="active")  # active / discharged / deceased
    readmission_risk_score = Column(Integer)  # 0–100, from ML model
    neo4j_synced = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    department = relationship("Department", back_populates="patients")
    insurance_claims = relationship("InsuranceClaim", back_populates="patient")
    ot_records = relationship("OTRecord", back_populates="patient")
    consents = relationship("PatientConsent", back_populates="patient")


# ── Staff ─────────────────────────────────────────────────────────────────────
class Staff(Base):
    __tablename__ = "staff"
    __table_args__ = (
        Index("ix_staff_department_id", "department_id"),
        Index("ix_staff_role", "role"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    role = Column(String(100))
    department_id = Column(Integer, ForeignKey("departments.id"))
    monthly_salary = Column(Numeric(10, 2))
    join_date = Column(Date)
    status = Column(String(20), default="active")   # active / leave / resigned
    working_hours_per_week = Column(Integer, default=40)
    overtime_hours = Column(Integer, default=0)
    specialization = Column(String(100))
    registration_number = Column(String(50))         # Medical council reg number
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    department = relationship("Department", back_populates="staff")
    surgeries_performed = relationship("OTRecord", back_populates="surgeon")
    appointments = relationship("Appointment", back_populates="doctor")


# ── Financials ────────────────────────────────────────────────────────────────
class Financial(Base):
    __tablename__ = "financials"
    __table_args__ = (
        Index("ix_financials_year_month", "year", "month"),
        Index("ix_financials_department_id", "department_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(10), nullable=False)
    year = Column(Integer, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    revenue = Column(Numeric(14, 2), default=0)
    operating_cost = Column(Numeric(14, 2), default=0)
    insurance_revenue = Column(Numeric(14, 2), default=0)
    oop_revenue = Column(Numeric(14, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    department = relationship("Department", back_populates="financials")


# ── OT Records ────────────────────────────────────────────────────────────────
class OTRecord(Base):
    __tablename__ = "ot_records"
    __table_args__ = (
        Index("ix_ot_records_department_id", "department_id"),
        Index("ix_ot_records_scheduled_date", "scheduled_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    surgery_type = Column(String(100))
    scheduled_date = Column(Date)
    actual_date = Column(Date)
    status = Column(String(20))              # completed / cancelled / scheduled
    duration_minutes = Column(Integer)
    cancellation_reason = Column(String(200))
    surgeon_id = Column(Integer, ForeignKey("staff.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    department = relationship("Department", back_populates="ot_records")
    surgeon = relationship("Staff", back_populates="surgeries_performed")
    patient = relationship("Patient", back_populates="ot_records")


# ── Insurance Claims ──────────────────────────────────────────────────────────
class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"
    __table_args__ = (
        Index("ix_insurance_claims_patient_id", "patient_id"),
        Index("ix_insurance_claims_status", "status"),
        Index("ix_insurance_claims_insurer", "insurer"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    insurer = Column(String(100))
    claim_amount = Column(Numeric(12, 2))
    approved_amount = Column(Numeric(12, 2))
    status = Column(String(20))              # approved / pending / rejected
    submitted_date = Column(Date)
    resolved_date = Column(Date)
    tat_days = Column(Integer)
    rejection_reason = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="insurance_claims")


# ── Appointments ──────────────────────────────────────────────────────────────
class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_department_id", "department_id"),
        Index("ix_appointments_appointment_date", "appointment_date"),
        Index("ix_appointments_doctor_id", "doctor_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_name_encrypted = Column(Text)    # [ENCRYPTED]
    doctor_id = Column(Integer, ForeignKey("staff.id"))
    department_id = Column(Integer, ForeignKey("departments.id"))
    appointment_date = Column(Date)
    appointment_time = Column(Time)
    appointment_type = Column(String(20))    # new / follow-up
    status = Column(String(20))             # confirmed / completed / cancelled / no-show
    notes_encrypted = Column(Text)           # [ENCRYPTED]
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    doctor = relationship("Staff", back_populates="appointments")
    department = relationship("Department", back_populates="appointments")


# ── Patient Consents (DPDP Act 2023) ─────────────────────────────────────────
class PatientConsent(Base):
    __tablename__ = "patient_consents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    consent_type = Column(String(50), nullable=False)
    given_at = Column(DateTime(timezone=True))
    withdrawn_at = Column(DateTime(timezone=True))
    version = Column(String(10), default="1.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="consents")


# ── Audit Log (Immutable — no UPDATE/DELETE) ──────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_timestamp", "timestamp"),
        Index("ix_audit_log_user_id", "user_id"),
        Index("ix_audit_log_action", "action"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id = Column(Integer)
    user_role = Column(String(20))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    ip_address = Column(String(45))           # IPv4/IPv6
    session_id = Column(String(36))           # UUID string
    request_summary = Column(Text)
    data_hash = Column(String(64))            # SHA-256 of request payload


# ── Token Blacklist (JWT logout) ──────────────────────────────────────────────
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    jti = Column(String(36), primary_key=True)  # JWT ID
    blacklisted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))


# ── System Users ──────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="dept_head")  # ceo / dept_head / finance
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── NABH Compliance Checkpoints ───────────────────────────────────────────────
class NABHCheckpoint(Base):
    __tablename__ = "nabh_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(100), nullable=False)
    checkpoint_code = Column(String(20), unique=True)
    description = Column(Text)
    status = Column(String(20), default="non-compliant")  # compliant / partial / non-compliant
    last_reviewed = Column(Date)
    reviewer = Column(String(100))
    evidence_url = Column(Text)
    remarks = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
