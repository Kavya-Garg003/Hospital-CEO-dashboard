# 🏥 MASTER PROMPT — Aarogya Hospital CEO BI Dashboard
## For: Antigravity / Any AI Coding Agent | Hackathon 2025

---

## CONTEXT & MISSION

Build a **production-grade, full-stack Business Intelligence Dashboard** for the CEO of **Aarogya Multi-Specialty Hospital, Chennai, India**. The dashboard must empower the CEO with real-time operational insights, P&L visibility, AI-driven recommendations, and voice-enabled RAG Q&A across all hospital departments.

This must be self-explanatory — no separate PPT needed. The dashboard IS the presentation.

---

## TECH STACK (ALL FREE TIER)

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + Vite |
| Styling | TailwindCSS |
| Charts | Recharts + D3 |
| Backend API | FastAPI (Python) |
| Database | PostgreSQL (local) or SQLite for hackathon |
| AI / LLM | Anthropic Claude Sonnet (claude-sonnet-4-20250514) via API |
| RAG | LlamaIndex or LangChain + local vector store (ChromaDB) |
| Voice | Web Speech API (browser-native, free) |
| Auth | JWT tokens |
| Deployment | Docker Compose |

---

## PROJECT STRUCTURE

```
hospital-ceo-dashboard/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── KPICard.jsx
│   │   │   ├── LineChart.jsx
│   │   │   ├── BarChart.jsx
│   │   │   ├── DonutChart.jsx
│   │   │   ├── Table.jsx
│   │   │   ├── AlertsPanel.jsx
│   │   │   ├── BedOccupancyGrid.jsx
│   │   │   └── AIConcierge.jsx
│   │   ├── pages/
│   │   │   ├── Overview.jsx
│   │   │   ├── Finance.jsx
│   │   │   ├── Patients.jsx
│   │   │   ├── Departments.jsx
│   │   │   ├── HRPayroll.jsx
│   │   │   ├── OTSurgeries.jsx
│   │   │   ├── Insurance.jsx
│   │   │   ├── Appointments.jsx
│   │   │   └── AIConcierge.jsx
│   │   ├── data/
│   │   │   └── syntheticData.js   ← full synthetic dataset
│   │   └── App.jsx
├── backend/
│   ├── main.py                    ← FastAPI app
│   ├── routes/
│   │   ├── analytics.py
│   │   ├── patients.py
│   │   ├── finance.py
│   │   ├── hr.py
│   │   ├── insurance.py
│   │   ├── ot.py
│   │   ├── appointments.py
│   │   └── ai_concierge.py
│   ├── rag/
│   │   ├── embedder.py            ← ChromaDB + embeddings
│   │   └── query_engine.py        ← RAG pipeline
│   ├── models/
│   │   └── schemas.py
│   ├── seed_data.py               ← synthetic data seeder
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## SYNTHETIC DATA SCHEMA

### Departments Table
```sql
CREATE TABLE departments (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  head_doctor VARCHAR(100),
  total_beds INT,
  color_hex VARCHAR(7)
);
```

### Patients Table
```sql
CREATE TABLE patients (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  age INT,
  gender VARCHAR(10),
  department_id INT REFERENCES departments(id),
  admission_date DATE,
  discharge_date DATE,
  type VARCHAR(20),  -- inpatient/outpatient/emergency
  diagnosis TEXT,
  insurance_provider VARCHAR(100),
  bill_amount DECIMAL(12,2),
  status VARCHAR(20)
);
```

### Financial Records
```sql
CREATE TABLE financials (
  id SERIAL PRIMARY KEY,
  month VARCHAR(10),
  year INT,
  department_id INT REFERENCES departments(id),
  revenue DECIMAL(14,2),
  operating_cost DECIMAL(14,2),
  insurance_revenue DECIMAL(14,2),
  oop_revenue DECIMAL(14,2)
);
```

### HR / Staff Table
```sql
CREATE TABLE staff (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  role VARCHAR(100),
  department_id INT REFERENCES departments(id),
  monthly_salary DECIMAL(10,2),
  join_date DATE,
  status VARCHAR(20),  -- active/leave/resigned
  working_hours_per_week INT,
  overtime_hours INT
);
```

### OT Records
```sql
CREATE TABLE ot_records (
  id SERIAL PRIMARY KEY,
  department_id INT REFERENCES departments(id),
  surgery_type VARCHAR(100),
  scheduled_date DATE,
  actual_date DATE,
  status VARCHAR(20),  -- completed/cancelled/scheduled
  duration_minutes INT,
  surgeon_id INT REFERENCES staff(id),
  patient_id INT REFERENCES patients(id)
);
```

### Insurance Claims
```sql
CREATE TABLE insurance_claims (
  id SERIAL PRIMARY KEY,
  patient_id INT REFERENCES patients(id),
  insurer VARCHAR(100),
  claim_amount DECIMAL(12,2),
  approved_amount DECIMAL(12,2),
  status VARCHAR(20),  -- approved/pending/rejected
  submitted_date DATE,
  resolved_date DATE,
  tat_days INT
);
```

### Appointments
```sql
CREATE TABLE appointments (
  id SERIAL PRIMARY KEY,
  patient_name VARCHAR(100),
  doctor_id INT REFERENCES staff(id),
  department_id INT REFERENCES departments(id),
  appointment_date DATE,
  appointment_time TIME,
  type VARCHAR(20),  -- new/follow-up
  status VARCHAR(20)  -- confirmed/completed/cancelled/no-show
);
```

---

## DASHBOARD MODULES TO BUILD

### 1. Overview Tab (CEO Landing Page)
- 6 KPI cards: Revenue, Net Profit, Total Patients, Bed Occupancy, Staff Count, Pending Insurance Claims
- Revenue vs Expenditure line chart (12 months)
- AI Alerts panel (predictive, rule-based + LLM-generated)
- Department P&L summary table
- Trend sparklines on every KPI

### 2. Finance & P&L Tab
- Revenue breakdown: Insurance vs OOP vs Total
- Monthly bar chart with 4 series
- Department-wise P&L table (profit, margin, color-coded)
- Profit heatmap across departments
- Break-even analysis widget

### 3. Patients Tab
- Inpatient / Outpatient / Emergency / Surgery counters
- Patient volume trend chart (12 months)
- Avg Length of Stay KPI
- Bed occupancy grid (color: green/amber/red by threshold)
- Disease/diagnosis distribution donut chart

### 4. Departments Tab
- Department cards with color-coded headers
- Each card: Revenue, Profit, Bed occupancy bar, Head doctor
- Filter by department name
- Click-through to department detail view

### 5. HR & Payroll Tab
- Total staff, attendance, on-leave, monthly payroll, attrition
- Payroll table: role, headcount, salary, total CTC, attrition %, OT hours
- Attrition trend chart
- Department-wise staff distribution donut

### 6. OT & Surgeries Tab
- Total surgeries, OT utilization %, cancellations, avg duration
- OT performance table with inline utilization bars
- Surgery type distribution
- Cancellation reason analysis

### 7. Insurance Tab
- Claims: total, approved, pending, rejected, total value, avg TAT
- Insurer-wise breakdown table with status colors
- TAT trend chart (target: <21 days)
- Rejection rate by insurer (flag if >15%)

### 8. Appointments Tab
- Status counters: Confirmed, Completed, Cancelled, No-Show
- Searchable/filterable appointments table
- No-show rate trend
- Doctor-wise load distribution

### 9. AI Concierge Tab
- Chat interface with Claude API integration
- RAG: queries answered from live hospital database
- Voice input (Web Speech API, lang=en-IN)
- Quick-prompt chips: "Most profitable dept?", "OT status?", etc.
- Predictive alerts fed from rule engine
- Context-aware: CEO name, date, hospital name in system prompt

---

## AI CONCIERGE SYSTEM PROMPT TEMPLATE

```python
SYSTEM_PROMPT = f"""
You are the AI Concierge for {hospital_name}, a multi-specialty hospital in {location}.
Today is {today}. You are speaking with the CEO, {ceo_name}.

You have access to real-time hospital data including:
- Financial records: revenue ₹{revenue}Cr, net profit ₹{profit}Cr, margin {margin}%
- Patient statistics: {total_patients} total, {inpatient} inpatient, {outpatient} outpatient
- Staff: {total_staff} employees across {dept_count} departments
- Bed occupancy: {occupancy}% ({occupied}/{total_beds} beds)
- Insurance: {total_claims} claims, {pending} pending, avg TAT {avg_tat} days
- Top profitable dept: {top_dept} ({top_margin}% margin)
- Alerts: {alerts_summary}

Answer concisely in 2-4 sentences. Use Indian number formatting (lakhs, crores).
Provide actionable CEO-level insights, not just data.
If asked something outside hospital data, say you don't have that information.
"""
```

---

## RAG PIPELINE

```python
# backend/rag/query_engine.py
from llama_index import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores import ChromaVectorStore
import chromadb

def build_rag_index(db_records):
    """Convert DB records to documents and index them"""
    documents = records_to_documents(db_records)
    chroma_client = chromadb.Client()
    chroma_collection = chroma_client.create_collection("hospital_data")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)
    return index

def query_rag(index, question: str, context: dict) -> str:
    query_engine = index.as_query_engine()
    response = query_engine.query(f"{question}\nContext: {context}")
    return str(response)
```

---

## PREDICTIVE ALERTS (RULE ENGINE)

```python
def generate_alerts(data: dict) -> list:
    alerts = []
    
    # Bed occupancy alert
    for dept in data['bed_occupancy']:
        pct = dept['occupied'] / dept['total_beds']
        if pct > 0.90:
            alerts.append({"type": "danger", "msg": f"{dept['name']} at {pct*100:.0f}% occupancy — critical"})
        elif pct > 0.80:
            alerts.append({"type": "warn", "msg": f"{dept['name']} bed occupancy above 80%"})
    
    # Insurance TAT alert
    for ins in data['insurance']:
        if ins['avg_tat'] > 30:
            alerts.append({"type": "warn", "msg": f"{ins['insurer']} TAT {ins['avg_tat']} days — exceeds 30-day threshold"})
    
    # Revenue dip alert
    last_two = data['revenue'][-2:]
    if last_two[1]['revenue'] < last_two[0]['revenue'] * 0.95:
        alerts.append({"type": "danger", "msg": "Revenue declined >5% month-over-month"})
    
    # OT cancellation alert
    for dept in data['ot']:
        cancel_rate = dept['cancelled'] / dept['scheduled']
        if cancel_rate > 0.15:
            alerts.append({"type": "warn", "msg": f"OT cancellation rate in {dept['dept']} is {cancel_rate*100:.0f}%"})
    
    # Profitable department insight
    top = max(data['dept_financials'], key=lambda x: x['margin'])
    alerts.append({"type": "info", "msg": f"{top['dept']} leads with {top['margin']}% net margin — consider capacity expansion"})
    
    return alerts
```

---

## FAST API ROUTES

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Hospital CEO Dashboard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Routes
app.include_router(analytics_router, prefix="/api/analytics")
app.include_router(finance_router, prefix="/api/finance")
app.include_router(patients_router, prefix="/api/patients")
app.include_router(hr_router, prefix="/api/hr")
app.include_router(ot_router, prefix="/api/ot")
app.include_router(insurance_router, prefix="/api/insurance")
app.include_router(appointments_router, prefix="/api/appointments")
app.include_router(ai_router, prefix="/api/ai")

@app.get("/api/overview")
def get_overview():
    """Returns all KPIs for CEO overview page"""
    pass

@app.post("/api/ai/chat")
def chat(payload: ChatPayload):
    """RAG-powered AI concierge endpoint"""
    pass

@app.get("/api/alerts")
def get_alerts():
    """Predictive alerts from rule engine + LLM"""
    pass
```

---

## EVALUATION RUBRIC ALIGNMENT

| Rubric Area | Implementation |
|-------------|----------------|
| Business Understanding | 9 department modules, India-specific KPIs (OPD, IPD, TPA, crores) |
| Data Engineering | Full SQL schema, synthetic seeder, normalized relationships |
| Dashboard Design & UX | Tab-based nav, KPI hierarchy, color-coded status, mobile-ready |
| Descriptive Analytics | Trend charts, root cause via alerts, dept-wise breakdown |
| Predictive Analytics | Rule engine alerts + LLM-generated insights with thresholds |
| AI Concierge | Claude API + RAG + voice (Web Speech) + quick prompts |
| Presentation | Self-explanatory dashboard, no PPT needed |

---

## WHAT IS DONE (ARTIFACT)

- [x] Complete React dashboard with 9 tabs
- [x] Synthetic data engine (seeded, deterministic)
- [x] All department views: Finance, Patients, HR, OT, Insurance, Appointments
- [x] Bed occupancy visualization with color-coded thresholds
- [x] KPI cards with sparklines and trend indicators
- [x] AI Concierge with Claude API + fallback RAG
- [x] Voice input (Web Speech API)
- [x] Alerts panel (rule-based)
- [x] Department P&L table with profit/loss coloring
- [x] Searchable/filterable tables

## WHAT NEEDS TO BE DONE (NEXT AGENT)

- [ ] Connect FastAPI backend with real PostgreSQL
- [ ] Implement LlamaIndex RAG with ChromaDB
- [ ] Build seed_data.py to populate 1000+ patient records
- [ ] Add authentication (JWT + role-based access)
- [ ] Add date range picker for all charts
- [ ] Add export to PDF/Excel for reports
- [ ] Add predictive ML model: bed demand forecasting (Prophet or ARIMA)
- [ ] Add patient readmission risk score (logistic regression)
- [ ] Add revenue forecasting chart (next 3 months)
- [ ] Dockerize the full stack
- [ ] Add real-time WebSocket updates for live metrics
- [ ] Add patient satisfaction score integration
- [ ] Add NABH compliance checklist module

---

## KNOWLEDGE TRANSFER NOTES

### Hospital Context
- Name: Aarogya Multi-Specialty Hospital, Chennai, Tamil Nadu
- Beds: 450 | Departments: 10 | FY: 2024-25
- Revenue target: ₹12 Cr/month | Profit margin target: 25%

### Key Indian Hospital KPIs
- OPD: Outpatient Department visits
- IPD: Inpatient admissions
- TPA: Third Party Administrator (insurance intermediary)
- LOS: Length of Stay (target: <5 days)
- ALOS: Average LOS
- BOR: Bed Occupancy Rate (target: 75–85%)
- OT Utilization: Target >80%
- TAT: Turnaround Time for claims (target: <21 days)

### Color Conventions
- Green: healthy (occupancy 60–75%, margin >20%, TAT <21d)
- Amber: warning (occupancy 75–90%, margin 10–20%, TAT 21–30d)
- Red: critical (occupancy >90%, margin <10%, TAT >30d)

### Claude API Call Pattern
```js
const response = await fetch("https://api.anthropic.com/v1/messages", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1000,
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: userQuestion }]
  })
});
```
