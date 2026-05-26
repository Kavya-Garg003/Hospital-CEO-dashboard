"""
backend/seed_data.py
---------------------
Synthetic data seeder: generates 5000+ patient records and all related data.
Runs as a standalone script OR via init_db.bat.

Data is deterministic (Math.sin-style seeding) — same output every run.
All PHI is AES-256-GCM encrypted before database insertion.
Neo4j graph is populated in parallel if available.

Usage:
    python seed_data.py
    python seed_data.py --records 1000  # Faster for testing
"""

import argparse
import asyncio
import hashlib
import json
import math
import os
import sys

# Force UTF-8 encoding for standard output on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from datetime import date, timedelta, datetime
from decimal import Decimal
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings


def seed(s: float) -> float:
    """Deterministic pseudo-random [0,1) using sin function."""
    x = math.sin(s) * 10000
    return x - math.floor(x)


DEPARTMENTS = [
    {"name": "Cardiology", "head": "Dr. Ramesh Iyer", "beds": 60, "color": "#e74c3c"},
    {"name": "Orthopaedics", "head": "Dr. Meena Suresh", "beds": 50, "color": "#3498db"},
    {"name": "Neurology", "head": "Dr. Arjun Pillai", "beds": 45, "color": "#9b59b6"},
    {"name": "Oncology", "head": "Dr. Priya Nair", "beds": 55, "color": "#e67e22"},
    {"name": "Paediatrics", "head": "Dr. Kavitha Rajan", "beds": 40, "color": "#27ae60"},
    {"name": "Gynaecology", "head": "Dr. Sujatha Venkat", "beds": 35, "color": "#f39c12"},
    {"name": "Emergency", "head": "Dr. Karthik Mohan", "beds": 30, "color": "#e74c3c"},
    {"name": "ICU / Critical Care", "head": "Dr. Balaji Krishnan", "beds": 40, "color": "#c0392b"},
    {"name": "Radiology", "head": "Dr. Deepa Srinivasan", "beds": 0, "color": "#1abc9c"},
    {"name": "Pharmacy", "head": "Mr. Senthil Kumar", "beds": 0, "color": "#34495e"},
]

PATIENT_NAMES = [
    "Ramesh Kumar", "Priya Sharma", "Arjun Nair", "Kavitha Rajan", "Sanjay Patel",
    "Meena Krishnan", "Vijay Subramaniam", "Anita Gupta", "Ravi Pillai", "Sunita Reddy",
    "Karthik Iyer", "Deepa Venkat", "Balaji Mohan", "Saranya Srinivasan", "Manoj Chandran",
    "Lakshmi Balasubramanian", "Senthil Nathan", "Padma Raghavan", "Suresh Menon", "Geetha Murugan",
]

INSURERS = [
    "Star Health", "HDFC ERGO", "Bajaj Allianz", "New India Assurance",
    "United India", "Medi Assist TPA", "Vidal Health TPA", "Raksha TPA",
]

ICD_CODES = [
    ("I21", "Acute myocardial infarction"), ("I10", "Essential hypertension"),
    ("M54", "Dorsalgia"), ("G40", "Epilepsy"), ("C50", "Breast neoplasm"),
    ("J18", "Pneumonia"), ("K35", "Acute appendicitis"), ("O80", "Normal delivery"),
    ("Z47", "Orthopaedic follow-up"), ("I63", "Cerebral infarction"),
    ("G35", "Multiple sclerosis"), ("E11", "Type 2 diabetes mellitus"),
    ("N18", "Chronic kidney disease"), ("A09", "Gastroenteritis"),
    ("S72", "Fracture of femur"),
]

HR_ROLES = [
    {"role": "Senior Consultant", "count": 45, "salary": 280000},
    {"role": "Junior Consultant", "count": 62, "salary": 180000},
    {"role": "Resident Doctor", "count": 88, "salary": 95000},
    {"role": "Staff Nurse", "count": 210, "salary": 42000},
    {"role": "Lab Technician", "count": 55, "salary": 35000},
    {"role": "Pharmacist", "count": 28, "salary": 38000},
    {"role": "Radiology Tech", "count": 22, "salary": 40000},
    {"role": "Admin Staff", "count": 90, "salary": 28000},
    {"role": "Support Staff", "count": 120, "salary": 22000},
]

MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]


async def seed_database(num_patients: int = 2000):
    from database import init_db, AsyncSessionLocal
    from models.sql_models import (
        Department, Patient, Staff, Financial, OTRecord,
        InsuranceClaim, Appointment, NABHCheckpoint, User, PatientConsent
    )
    from encryption import encryptor, hash_aadhaar
    from auth.jwt_handler import hash_password
    from sqlalchemy import select
    from database import get_neo4j_driver
    from models.graph_models import init_graph_schema, sync_patient_to_neo4j

    print("[DB] Initialising database...")
    await init_db()

    neo4j_driver = get_neo4j_driver()
    if neo4j_driver:
        print("[Graph] Initialising Neo4j schema...")
        init_graph_schema(neo4j_driver)

    async with AsyncSessionLocal() as db:
        # ── Departments ─────────────────────────────────────────────────────
        print("[1/8] Seeding departments...")
        dept_id_map = {}
        for i, d in enumerate(DEPARTMENTS):
            existing = await db.execute(select(Department).where(Department.name == d["name"]))
            if existing.scalar_one_or_none():
                result = await db.execute(select(Department.id).where(Department.name == d["name"]))
                dept_id_map[d["name"]] = result.scalar()
                continue
            dept = Department(
                name=d["name"], head_doctor=d["head"],
                total_beds=d["beds"], color_hex=d["color"]
            )
            db.add(dept)
            await db.flush()
            dept_id_map[d["name"]] = dept.id

        # ── Staff ────────────────────────────────────────────────────────────
        print("👥 Seeding staff...")
        staff_ids = []
        s_idx = 0
        for dept in DEPARTMENTS[:8]:
            for role_data in HR_ROLES[:3]:
                for j in range(max(1, role_data["count"] // 8)):
                    name = f"Dr. Staff {s_idx + 1}"
                    staff = Staff(
                        name=name,
                        role=role_data["role"],
                        department_id=dept_id_map[dept["name"]],
                        monthly_salary=Decimal(str(role_data["salary"] + int(seed(s_idx * 7) * 20000))),
                        join_date=date(2020, 1, 1) + timedelta(days=int(seed(s_idx * 11) * 1000)),
                        status="active",
                        working_hours_per_week=40,
                        overtime_hours=int(seed(s_idx * 13) * 20),
                    )
                    db.add(staff)
                    await db.flush()
                    staff_ids.append(staff.id)
                    s_idx += 1

        # ── Financials ───────────────────────────────────────────────────────
        print("💰 Seeding financial records...")
        for m_idx, month in enumerate(MONTHS):
            year = 2025 if m_idx >= 9 else 2024
            for d_idx, dept in enumerate(DEPARTMENTS):
                rev = int(800000 + seed(m_idx * 101 + d_idx * 7) * 2200000)
                cost = int(500000 + seed(m_idx * 103 + d_idx * 11) * 1500000)
                financial = Financial(
                    month=month, year=year,
                    department_id=dept_id_map[dept["name"]],
                    revenue=Decimal(rev),
                    operating_cost=Decimal(cost),
                    insurance_revenue=Decimal(int(rev * 0.6)),
                    oop_revenue=Decimal(int(rev * 0.4)),
                )
                db.add(financial)

        # ── Patients ─────────────────────────────────────────────────────────
        print(f"🏥 Seeding {num_patients} patients (encrypted)...")
        patient_ids = []
        for p_idx in range(num_patients):
            dept_name = DEPARTMENTS[p_idx % 8]["name"]
            icd, diag_text = ICD_CODES[p_idx % len(ICD_CODES)]
            pt_name = PATIENT_NAMES[p_idx % len(PATIENT_NAMES)] + f" {p_idx + 1}"
            admission_offset = int(seed(p_idx * 17) * 365)
            admit_date = date(2024, 4, 1) + timedelta(days=admission_offset)
            los = int(1 + seed(p_idx * 19) * 14)
            discharge = admit_date + timedelta(days=los) if seed(p_idx * 23) > 0.3 else None

            patient = Patient(
                name_encrypted=encryptor.encrypt(pt_name),
                phone_encrypted=encryptor.encrypt(f"+91-{9000000000 + p_idx}"),
                aadhaar_hash=hash_aadhaar(f"{1000000000000 + p_idx}"),
                aadhaar_encrypted=encryptor.encrypt(f"{1000000000000 + p_idx}"),
                diagnosis_encrypted=encryptor.encrypt(diag_text),
                age=int(20 + seed(p_idx * 29) * 65),
                gender=["Male", "Female"][p_idx % 2],
                department_id=dept_id_map[dept_name],
                admission_date=admit_date,
                discharge_date=discharge,
                patient_type=["inpatient", "outpatient", "emergency"][p_idx % 3],
                icd_code=icd,
                insurance_provider=INSURERS[p_idx % len(INSURERS)] if seed(p_idx * 31) > 0.3 else None,
                bill_amount=Decimal(str(int(5000 + seed(p_idx * 37) * 200000))),
                status="active" if discharge is None else "discharged",
                readmission_risk_score=int(seed(p_idx * 41) * 100),
            )
            db.add(patient)
            await db.flush()
            patient_ids.append(patient.id)
            
            if neo4j_driver:
                sync_patient_to_neo4j(neo4j_driver, {
                    "patient_id": patient.id,
                    "age": patient.age,
                    "gender": patient.gender,
                    "patient_type": patient.patient_type,
                    "status": patient.status,
                    "risk_score": patient.readmission_risk_score,
                    "dept_id": patient.department_id,
                    "dept_name": dept_name,
                    "admission_date": patient.admission_date.isoformat() if patient.admission_date else None,
                    "los_days": los,
                })

            # Consent record
            consent = PatientConsent(
                patient_id=patient.id,
                consent_type="data_processing",
                given_at=datetime.combine(admit_date, datetime.min.time()),
                version=settings.CONSENT_FORM_VERSION,
            )
            db.add(consent)

        # ── Insurance Claims ─────────────────────────────────────────────────
        print("📋 Seeding insurance claims...")
        for c_idx, pid in enumerate(patient_ids[:1000]):
            if seed(c_idx * 53) > 0.4:  # 60% have insurance claims
                claim = InsuranceClaim(
                    patient_id=pid,
                    insurer=INSURERS[c_idx % len(INSURERS)],
                    claim_amount=Decimal(str(int(10000 + seed(c_idx * 59) * 150000))),
                    approved_amount=Decimal(str(int(8000 + seed(c_idx * 61) * 140000))),
                    status=["approved", "pending", "rejected"][c_idx % 3],
                    submitted_date=date(2024, 4, 1) + timedelta(days=int(seed(c_idx * 67) * 300)),
                    tat_days=int(10 + seed(c_idx * 71) * 40),
                    rejection_reason="Insufficient documentation" if c_idx % 3 == 2 else None,
                )
                db.add(claim)

        # ── OT Records ───────────────────────────────────────────────────────
        print("🔪 Seeding OT records...")
        surgical_depts = [d for d in DEPARTMENTS if d["beds"] > 0]
        for o_idx in range(500):
            dept = surgical_depts[o_idx % len(surgical_depts)]
            scheduled = date(2024, 4, 1) + timedelta(days=int(seed(o_idx * 79) * 365))
            status_val = ["completed", "completed", "completed", "completed", "completed", "completed", "completed", "cancelled", "cancelled", "scheduled"][o_idx % 10]
            surgery_types = ["Coronary bypass", "Hip replacement", "Craniotomy", "Mastectomy", "Appendectomy", "C-section"]
            ot = OTRecord(
                department_id=dept_id_map[dept["name"]],
                surgery_type=surgery_types[o_idx % len(surgery_types)],
                scheduled_date=scheduled,
                actual_date=scheduled if status_val in ["completed"] else None,
                status=status_val,
                duration_minutes=int(60 + seed(o_idx * 83) * 240) if status_val == "completed" else None,
                cancellation_reason="Patient not ready" if status_val == "cancelled" else None,
                surgeon_id=staff_ids[o_idx % len(staff_ids)] if staff_ids else None,
                patient_id=patient_ids[o_idx % len(patient_ids)],
            )
            db.add(ot)

        # ── Appointments ─────────────────────────────────────────────────────
        print("📅 Seeding appointments...")
        for a_idx in range(400):
            appt = Appointment(
                patient_name_encrypted=encryptor.encrypt(PATIENT_NAMES[a_idx % len(PATIENT_NAMES)]),
                doctor_id=staff_ids[a_idx % len(staff_ids)] if staff_ids else None,
                department_id=dept_id_map[DEPARTMENTS[a_idx % 8]["name"]],
                appointment_date=date(2025, 3, 1) + timedelta(days=a_idx % 28),
                appointment_type="new" if a_idx % 3 != 0 else "follow-up",
                status=["confirmed", "completed", "cancelled", "no-show"][a_idx % 4],
            )
            db.add(appt)

        # ── CEO User ─────────────────────────────────────────────────────────
        print("👤 Creating CEO user (username: ceo, password: Aarogya@2024)...")
        existing_user = await db.execute(select(User).where(User.username == "ceo"))
        if not existing_user.scalar_one_or_none():
            ceo = User(
                username="ceo",
                email="ceo@aarogyahospital.in",
                hashed_password=hash_password("Aarogya@2024"),
                role="ceo",
                is_active=True,
            )
            db.add(ceo)

        # ── NABH Checkpoints ─────────────────────────────────────────────────
        print("✅ Seeding NABH compliance checkpoints...")
        nabh_data = [
            ("Patient Care", "PC-1", "Patient identification using two identifiers", "compliant"),
            ("Patient Care", "PC-2", "Informed consent before all procedures", "compliant"),
            ("Patient Care", "PC-3", "Patient rights and responsibilities displayed", "partial"),
            ("Patient Care", "PC-4", "Pain assessment and management protocol", "compliant"),
            ("Infection Control", "IC-1", "Hand hygiene compliance >90%", "partial"),
            ("Infection Control", "IC-2", "Isolation protocols for infectious patients", "compliant"),
            ("Infection Control", "IC-3", "CSSD sterilization standards", "compliant"),
            ("Infection Control", "IC-4", "Antibiotic stewardship programme", "partial"),
            ("Medication Management", "MM-1", "High-alert medication storage and labeling", "compliant"),
            ("Medication Management", "MM-2", "Medication reconciliation at admission/discharge", "non-compliant"),
            ("Quality Improvement", "QI-1", "Incident reporting system", "compliant"),
            ("Quality Improvement", "QI-2", "Root cause analysis for sentinel events", "partial"),
            ("Quality Improvement", "QI-3", "Monthly quality indicators review", "compliant"),
            ("Staff Competency", "SC-1", "Credentialing and privileging for all doctors", "compliant"),
            ("Staff Competency", "SC-2", "Annual competency assessment for nursing staff", "partial"),
            ("Staff Competency", "SC-3", "BLS/ACLS certification for ICU/Emergency staff", "compliant"),
            ("Facility Management", "FM-1", "Fire safety and evacuation plan", "compliant"),
            ("Facility Management", "FM-2", "Medical equipment maintenance logs", "partial"),
            ("Facility Management", "FM-3", "Generator backup tested monthly", "compliant"),
            ("Information Management", "IM-1", "Patient data privacy policy", "compliant"),
            ("Information Management", "IM-2", "Medical records completeness audit", "partial"),
            ("Information Management", "IM-3", "Data backup and recovery procedure", "compliant"),
        ]
        for domain, code, desc, status_val in nabh_data:
            existing = await db.execute(select(NABHCheckpoint).where(NABHCheckpoint.checkpoint_code == code))
            if not existing.scalar_one_or_none():
                cp = NABHCheckpoint(domain=domain, checkpoint_code=code, description=desc, status=status_val)
                db.add(cp)

        await db.commit()
        print(f"\n✅ Seeding complete!")
        print(f"   Departments:   {len(DEPARTMENTS)}")
        print(f"   Staff:         {s_idx}")
        print(f"   Financial rows: {len(MONTHS) * len(DEPARTMENTS)}")
        print(f"   Patients:      {num_patients}")
        print(f"   OT records:    500")
        print(f"   Appointments:  400")
        print(f"   NABH checks:   {len(nabh_data)}")
        print(f"\n🔐 CEO Login: username=ceo, password=Aarogya@2024")
        print(f"🌐 API Docs:  http://localhost:8000/docs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed hospital database")
    parser.add_argument("--records", type=int, default=2000, help="Number of patient records")
    args = parser.parse_args()

    asyncio.run(seed_database(args.records))
