# ⚖️ Compliance Documentation — Aarogya Hospital CEO Dashboard

## DPDP Act 2023 — Digital Personal Data Protection Act

### Applicability
This system processes Personal Data (patient names, phone numbers) and Sensitive Personal Data (Aadhaar, medical diagnoses) of Indian data principals. The hospital acts as a **Data Fiduciary** under the DPDP Act 2023.

### Compliance Matrix

| DPDP Obligation | Section | Implementation |
|----------------|---------|---------------|
| Consent before processing | S.6 | `patient_consents` table; consent gate at admission |
| Purpose limitation | S.6(3) | Audit log records purpose of every access |
| Data minimization | S.6 | API returns only fields needed per endpoint |
| Accuracy of data | S.9 | PATCH endpoints for patient record correction |
| Storage limitation | S.8 | Retention policy: medical records 7 years (NABH) |
| Data security | S.8(7) | AES-256-GCM + TLS + RBAC + audit trail |
| Right to access | S.12 | `GET /api/compliance/dpdp/my-data/{id}` |
| Right to correction | S.13 | `PATCH /api/patients/{id}` with audit log |
| Right to erasure | S.13 | `POST /api/compliance/dpdp/erasure` (anonymization) |
| Right to nominate | S.14 | Documented in patient consent form |
| DPO appointment | S.10 | DPO contact in `.env` and all patient responses |
| Breach notification | S.8(6) | 72h notification procedure in SECURITY.md |
| Cross-border transfer | S.16 | PHI never leaves India; Claude API uses aggregated stats only |
| Children's data | S.9 | Parental consent required for patients under 18 |

### Data Flow Map

```
Patient registration → Consent obtained → PHI encrypted (AES-256-GCM) → PostgreSQL
                                                                         ↓
CEO Dashboard → JWT authenticated request → RBAC check → Decrypt at response time → Masked if non-CEO
                                                                         ↓
                                                            Audit log entry (immutable)
```

### Anonymisation vs Erasure

Per NABH guidelines, medical records must be retained for **7 years**. Therefore, **right to erasure** is implemented as **anonymisation** (not hard deletion):

- Patient name → `"ANONYMISED"`
- Phone → `"ANONYMISED"`  
- Aadhaar → `"ANONYMISED"` (both hash and encrypted)
- Patient status → `"anonymised"`
- Clinical data (ICD codes, bills) → **retained** for medical/legal compliance

### Aadhaar Storage

Per UIDAI guidelines and IT Act S.43A:
- Aadhaar numbers are **never stored in plaintext**
- Stored as: SHA-256 hash (for deduplication) + AES-256-GCM encrypted value
- Displayed as: `XXXX-XXXX-9012` (last 4 digits only)

---

## NABH — National Accreditation Board for Hospitals (5th Edition)

### Compliance Domains Tracked

| Domain | Checkpoints | Current Status |
|--------|-------------|---------------|
| Patient Care | 3 | 2 compliant, 1 partial |
| Infection Control | 3 | 2 compliant, 1 partial |
| Medication Management | 2 | 1 compliant, 1 non-compliant |
| Quality Improvement | 2 | 1 compliant, 1 partial |
| Staff Competency | 2 | 1 compliant, 1 partial |
| Facility Management | 2 | 2 compliant |
| Information Management | 2 | 1 compliant, 1 partial |

### NABH Score Calculation

```
Compliance Score = (Compliant checkpoints / Total checkpoints) × 100
NABH Ready: ≥ 85%
In Progress: 60–84%
Needs Attention: < 60%
```

### Critical Non-Compliance Items

1. **MM-2 (Medication Reconciliation)** — Status: non-compliant  
   Action: Implement structured medication reconciliation at admission and discharge.  
   Owner: Chief Pharmacist  
   Target: 90 days

### NABH Evidence Trail

The `nabh_checkpoints` table stores:
- `evidence_url` — link to uploaded compliance document
- `reviewer` — staff member who verified
- `last_reviewed` — date of last audit
- `remarks` — corrective actions noted

---

## IT Act 2000 — Section 43A (Reasonable Security Practices)

The system implements **ISO 27001-aligned** security practices as required by IT Act S.43A:

- AES-256-GCM encryption (NIST-recommended)
- Role-based access control
- Audit logging
- Incident response procedure
- Regular security assessment (recommended: quarterly)

---

## Data Retention Schedule

| Data Type | Retention Period | Basis |
|-----------|-----------------|-------|
| Patient medical records | 7 years post-discharge | NABH / MCI Guidelines |
| Audit logs | 7 years | NABH IM.1 |
| Insurance claims | 7 years | IRDAI guidelines |
| Consent records | Duration of treatment + 7 years | DPDP Act S.8 |
| JWT token blacklist | 30 days | Operational |
| Anonymised records | Indefinite (no PHI remains) | Post-erasure retention |

---

## Data Protection Officer

```
Name:   [To be appointed per DPDP Act S.10]
Email:  dpo@aarogyahospital.in
Phone:  +91-XXXXXXXXXX
```

All DPDP-related requests should be directed to the DPO within the timelines:
- Right to access: 30 days
- Right to correction: 30 days
- Right to erasure: 30 days
- Breach notification: 72 hours (to Data Protection Board of India)
