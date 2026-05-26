# 🏥 Aarogya Hospital CEO BI Dashboard
### Production-Grade Full-Stack Business Intelligence Platform
**Aarogya Multi-Specialty Hospital, Chennai, Tamil Nadu**

---

## What This Is

A **production-grade**, full-stack Business Intelligence Dashboard for the CEO of Aarogya Multi-Specialty Hospital. One screen. All departments. AI-powered. Voice-enabled. Secure. Compliant with India's DPDP Act 2023. NABH accreditation-ready.

The dashboard **IS** the presentation — no separate PPT needed.

---

## Quick Start (No Backend Needed)

```bat
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` — fully functional with synthetic data.

---

## Full Stack Quick Start

```bat
scripts\start_all.bat
```

Or step-by-step: see [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md)

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Dashboard |
| http://localhost:8000/docs | API Swagger UI |
| **CEO Login** | `ceo` / `Aarogya@2024` |

---

## Architecture

```
CEO Browser (React 18 + Vite)
    │
    ├─ 10 Tabs: Overview · Finance · Patients · Departments ·
    │            HR & Payroll · OT · Insurance · Appointments ·
    │            NABH Compliance · AI Concierge
    │
    ├─ FastAPI Backend (Python 3.11)
    │   ├─ RS256 JWT Auth + RBAC (CEO / Dept Head / Finance)
    │   ├─ Rate Limiting (slowapi)
    │   ├─ Security Headers (CSP, HSTS, X-Frame-Options)
    │   ├─ WebSocket Live KPI Push (/ws/live-kpis)
    │   └─ 40+ API Endpoints
    │
    ├─ PostgreSQL / SQLite
    │   ├─ AES-256-GCM field-level encryption for PHI
    │   ├─ Immutable audit log (7-year retention)
    │   └─ DPDP consent management + NABH checkpoints
    │
    ├─ Neo4j (Community) — Graph Analytics
    │   ├─ Patient → Doctor → Department relationships
    │   ├─ Readmission pathway analysis
    │   └─ Insurance fraud detection queries
    │
    └─ AI / RAG Pipeline
        ├─ Claude Sonnet API (claude-sonnet-4-20250514)
        ├─ ChromaDB + sentence-transformers (local, offline-capable)
        └─ Local intent-match fallback (works with no API key)
```

---

## Dashboard Tabs

| Tab | Key Features |
|-----|-------------|
| 📊 Overview | 6 KPI cards, Revenue chart, Explainable alerts, Dept P&L |
| 💰 Finance & P&L | Monthly breakdown, Insurance vs OOP, Dept margins, break-even |
| 🏥 Patients | Volume trends, LOS, Bed occupancy grid, patient types |
| 🔬 Departments | Dept cards, financials, occupancy, search/filter |
| 👥 HR & Payroll | Staff roster, payroll table, attrition |
| 🔪 OT & Surgeries | Utilization, cancellations, avg duration |
| 📋 Insurance | Claims by insurer, TAT trend, approval rates |
| 📅 Appointments | Searchable records, status breakdown |
| ✅ NABH Compliance | Compliance score, domain-wise progress, checklist |
| 🤖 AI Concierge | Claude API + RAG + Voice + Quick prompts |

---

## Security & Compliance

| Feature | Implementation |
|---------|---------------|
| PHI Encryption | AES-256-GCM field-level (name, phone, Aadhaar, diagnosis) |
| Authentication | RS256 JWT (15-min access + 7-day refresh) |
| Authorization | RBAC (CEO / Dept Head / Finance) |
| Audit Trail | Immutable log of every data access + AI query |
| DPDP Act 2023 | Consent management, right-to-erasure, data access endpoints |
| NABH Standards | 5th Edition checklist with 22 checkpoints tracked |
| IT Act S.43A | ISO 27001-aligned security practices documented |

---

## AI Concierge

1. **Natural Language Q&A** — "Which dept is most profitable?" "What's our OT utilization?"
2. **RAG-backed** — Answers grounded in hospital policies and live data
3. **DPDP-compliant** — No PHI ever sent to Claude API (aggregated stats only)
4. **Voice Input** — Click 🎤, speak in English (Indian accent supported via `lang=en-IN`)
5. **Quick Prompts** — One-tap chips for common CEO questions
6. **3-tier fallback** — Claude API → Local RAG → Intent-match (works fully offline)

---

## ML Predictive Analytics

- **Bed Demand Forecasting** — Prophet model, 30-day forecast per department with confidence intervals
- **Readmission Risk Scoring** — Logistic regression, 0–100 score with SHAP explanations
- **Rule-based Alerts** — Thresholds configurable per hospital in `.env` or `hospital_config.json`

---

## Explainability

Every AI alert shows:
- The rule that fired it
- The threshold value
- The actual measured value
- A CEO-level recommendation

ML predictions show SHAP-style feature contributions in plain language.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Recharts |
| Styling | Vanilla CSS with custom properties |
| Backend | FastAPI (Python 3.11) |
| Relational DB | PostgreSQL / SQLite fallback |
| Graph DB | Neo4j Community 5.x |
| Vector Store | ChromaDB (local) |
| Embeddings | sentence-transformers (local, no API) |
| AI / LLM | Claude Sonnet (claude-sonnet-4-20250514) |
| Auth | RS256 JWT + bcrypt |
| Encryption | AES-256-GCM (Python cryptography library) |

**No Docker required** — runs as native Windows processes.

---

## Documentation

| File | Description |
|------|-------------|
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | Complete knowledge transfer — what's done, what remains |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Encryption, auth, threat model, key rotation |
| [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) | DPDP Act 2023 + NABH compliance mapping |
| [`docs/NEO4J_SCHEMA.md`](docs/NEO4J_SCHEMA.md) | Graph schema and CEO-level Cypher queries |
| [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md) | Step-by-step Windows local setup |

---

## Indian Hospital KPI Glossary

| KPI | Definition | Target |
|-----|-----------|--------|
| OPD | Outpatient Department visits | — |
| IPD | Inpatient admissions | — |
| TPA | Third Party Administrator | — |
| BOR | Bed Occupancy Rate | 75–85% |
| ALOS | Average Length of Stay | <5 days |
| TAT | Insurance Turnaround Time | <21 days |
| OT Utilization | % of scheduled OTs completed | >80% |
| NABH | National Accreditation Board for Hospitals | >85% score |

---

## Color Conventions

| Color | Meaning | Example |
|-------|---------|---------|
| 🟢 Green | Healthy | BOR 60–75%, Margin >20%, TAT <21d |
| 🟡 Amber | Warning | BOR 75–90%, Margin 10–20%, TAT 21–30d |
| 🔴 Red | Critical | BOR >90%, Margin <10%, TAT >30d |

---

## Contact / Handoff

When transferring to another system or agent:
1. Share all files in `e:\Hospital dashboard Project\`
2. Tell them: **"Read HANDOFF.md first. Continue from the Remaining section."**
3. Ensure `.env` files are transferred securely (not via git)
