// frontend/src/data/syntheticData.js
// Deterministic synthetic data engine — same values every load.
// Used when the FastAPI backend is not running.

// ─── SEED FUNCTION ────────────────────────────────────────────
function seed(s) {
  const x = Math.sin(s) * 10000;
  return x - Math.floor(x);
}

// ─── HOSPITAL CONFIG ──────────────────────────────────────────
export const HOSPITAL = {
  name: "Aarogya Multi-Specialty Hospital",
  location: "Chennai, Tamil Nadu",
  beds: 450,
  established: 2008,
  fy: "2024–25",
  ceo: "Dr. Arun Krishnaswamy",
};

// ─── DEPARTMENTS ──────────────────────────────────────────────
export const DEPARTMENTS = [
  { id: "cardiology", name: "Cardiology", head: "Dr. Ramesh Iyer", beds: 60, color: "#e74c3c" },
  { id: "orthopedics", name: "Orthopaedics", head: "Dr. Meena Suresh", beds: 50, color: "#3498db" },
  { id: "neurology", name: "Neurology", head: "Dr. Arjun Pillai", beds: 45, color: "#9b59b6" },
  { id: "oncology", name: "Oncology", head: "Dr. Priya Nair", beds: 55, color: "#e67e22" },
  { id: "pediatrics", name: "Paediatrics", head: "Dr. Kavitha Rajan", beds: 40, color: "#27ae60" },
  { id: "gynecology", name: "Gynaecology", head: "Dr. Sujatha Venkat", beds: 35, color: "#f39c12" },
  { id: "emergency", name: "Emergency", head: "Dr. Karthik Mohan", beds: 30, color: "#e74c3c" },
  { id: "icu", name: "ICU / Critical Care", head: "Dr. Balaji Krishnan", beds: 40, color: "#c0392b" },
  { id: "radiology", name: "Radiology", head: "Dr. Deepa Srinivasan", beds: 0, color: "#1abc9c" },
  { id: "pharmacy", name: "Pharmacy", head: "Mr. Senthil Kumar", beds: 0, color: "#34495e" },
];

export const MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"];

// ─── DATA GENERATORS ──────────────────────────────────────────
export function genRevenue() {
  return MONTHS.map((m, i) => ({
    month: m,
    revenue: Math.round(8500000 + seed(i * 7) * 3500000),
    opex: Math.round(5800000 + seed(i * 3) * 1200000),
    insurance: Math.round(3200000 + seed(i * 11) * 1500000),
    outOfPocket: Math.round(2800000 + seed(i * 5) * 1000000),
  }));
}

export function genPatients() {
  return MONTHS.map((m, i) => ({
    month: m,
    inpatient: Math.round(1200 + seed(i * 13) * 400),
    outpatient: Math.round(3800 + seed(i * 17) * 800),
    emergency: Math.round(420 + seed(i * 19) * 150),
    surgeries: Math.round(280 + seed(i * 23) * 90),
  }));
}

export function genOT() {
  return DEPARTMENTS.filter(d => d.beds > 0).map((dept, i) => {
    const scheduled = Math.round(60 + seed(i * 29) * 40);
    const completed = Math.round(50 + seed(i * 31) * 35);
    const cancelled = Math.round(5 + seed(i * 37) * 10);
    return {
      dept: dept.name,
      scheduled,
      completed,
      cancelled,
      avgDuration: Math.round(90 + seed(i * 41) * 120),
      utilization: Math.round(68 + seed(i * 43) * 25),
    };
  });
}

export function genHR() {
  const roles = [
    { role: "Senior Consultant", count: 45, salary: 280000 },
    { role: "Junior Consultant", count: 62, salary: 180000 },
    { role: "Resident Doctor", count: 88, salary: 95000 },
    { role: "Staff Nurse", count: 210, salary: 42000 },
    { role: "Lab Technician", count: 55, salary: 35000 },
    { role: "Pharmacist", count: 28, salary: 38000 },
    { role: "Radiology Tech", count: 22, salary: 40000 },
    { role: "Admin Staff", count: 90, salary: 28000 },
    { role: "Support Staff", count: 120, salary: 22000 },
  ];
  return roles.map((r, i) => ({
    ...r,
    present: Math.round(r.count * (0.88 + seed(i * 47) * 0.1)),
    onLeave: Math.round(r.count * (0.04 + seed(i * 53) * 0.06)),
    attrition: +(2.5 + seed(i * 59) * 4).toFixed(1),
    overtimeHrs: Math.round(12 + seed(i * 61) * 20),
  }));
}

export function genInsurance() {
  const insurers = [
    "Star Health", "HDFC ERGO", "Bajaj Allianz", "New India Assurance",
    "United India", "Medi Assist TPA", "Vidal Health TPA", "CGHS", "ECHS"
  ];
  return insurers.map((ins, i) => ({
    insurer: ins,
    claims: Math.round(200 + seed(i * 67) * 300),
    approved: Math.round(160 + seed(i * 71) * 250),
    pending: Math.round(20 + seed(i * 73) * 60),
    rejected: Math.round(10 + seed(i * 79) * 30),
    amount: Math.round(3500000 + seed(i * 83) * 5000000),
    avgDays: Math.round(18 + seed(i * 89) * 25),
  }));
}

export function genBedOccupancy() {
  return DEPARTMENTS.filter(d => d.beds > 0).map((dept, i) => ({
    dept: dept.name,
    totalBeds: dept.beds,
    occupied: Math.round(dept.beds * (0.6 + seed(i * 97) * 0.35)),
    color: dept.color,
  }));
}

export function genDeptFinancials() {
  return DEPARTMENTS.map((dept, i) => {
    const revenue = Math.round(800000 + seed(i * 101) * 2200000);
    const cost = Math.round(500000 + seed(i * 103) * 1500000);
    const profit = revenue - cost;
    return {
      dept: dept.name,
      revenue, cost, profit,
      margin: +((profit / revenue) * 100).toFixed(1),
      color: dept.color,
    };
  });
}

export function genAppointments() {
  const statuses = ["Confirmed", "Completed", "Cancelled", "No-Show"];
  const doctors = [
    "Dr. Ramesh Iyer", "Dr. Meena Suresh", "Dr. Arjun Pillai", "Dr. Priya Nair",
    "Dr. Kavitha Rajan", "Dr. Sujatha Venkat", "Dr. Karthik Mohan", "Dr. Balaji Krishnan",
  ];
  return Array.from({ length: 80 }, (_, i) => ({
    id: `APT${1000 + i}`,
    patient: `Patient ${i + 1}`,
    doctor: doctors[i % doctors.length],
    dept: DEPARTMENTS[i % DEPARTMENTS.length].name,
    date: `2025-03-${String((i % 28) + 1).padStart(2, "0")}`,
    time: `${String(9 + (i % 8)).padStart(2, "0")}:${i % 2 === 0 ? "00" : "30"}`,
    status: statuses[i % 4],
    type: i % 3 === 0 ? "Follow-up" : "New",
  }));
}

export function genBedForecast() {
  const depts = ["ICU / Critical Care", "Cardiology", "Emergency", "Orthopaedics"];
  const today = new Date();
  return depts.map(dept => ({
    dept,
    forecast: Array.from({ length: 14 }, (_, i) => {
      const d = new Date(today);
      d.setDate(d.getDate() + i + 1);
      const base = dept === "ICU / Critical Care" ? 85 : dept === "Emergency" ? 88 : 72;
      const val = base + Math.round(seed(i * 17 + dept.length) * 12 - 6);
      return {
        date: d.toISOString().slice(0, 10),
        predicted: Math.min(val, 98),
        lower: Math.max(val - 8, 40),
        upper: Math.min(val + 8, 100),
      };
    }),
  }));
}

export function genNABHCheckpoints() {
  const domains = [
    { domain: "Patient Care", code: "PC-1", desc: "Patient identification using two identifiers", status: "compliant" },
    { domain: "Patient Care", code: "PC-2", desc: "Informed consent before all procedures", status: "compliant" },
    { domain: "Patient Care", code: "PC-3", desc: "Patient rights and responsibilities displayed", status: "partial" },
    { domain: "Infection Control", code: "IC-1", desc: "Hand hygiene compliance >90%", status: "partial" },
    { domain: "Infection Control", code: "IC-2", desc: "Isolation protocols for infectious patients", status: "compliant" },
    { domain: "Infection Control", code: "IC-3", desc: "CSSD sterilization standards", status: "compliant" },
    { domain: "Medication Management", code: "MM-1", desc: "High-alert medication storage and labeling", status: "compliant" },
    { domain: "Medication Management", code: "MM-2", desc: "Medication reconciliation at admission/discharge", status: "non-compliant" },
    { domain: "Quality Improvement", code: "QI-1", desc: "Incident reporting system active", status: "compliant" },
    { domain: "Quality Improvement", code: "QI-2", desc: "Root cause analysis for sentinel events", status: "partial" },
    { domain: "Staff Competency", code: "SC-1", desc: "Credentialing and privileging for all doctors", status: "compliant" },
    { domain: "Staff Competency", code: "SC-2", desc: "Annual competency assessment for nurses", status: "partial" },
    { domain: "Facility Management", code: "FM-1", desc: "Fire safety and evacuation plan tested", status: "compliant" },
    { domain: "Facility Management", code: "FM-2", desc: "Medical equipment maintenance logs current", status: "partial" },
    { domain: "Information Management", code: "IM-1", desc: "Patient data privacy policy (DPDP Act 2023)", status: "compliant" },
    { domain: "Information Management", code: "IM-2", desc: "Medical records completeness audit", status: "partial" },
  ];
  return domains;
}

// ── Pre-computed all data (memoized) ─────────────────────────────
export const DATA = {
  revenue: genRevenue(),
  patients: genPatients(),
  ot: genOT(),
  hr: genHR(),
  insurance: genInsurance(),
  bedOccupancy: genBedOccupancy(),
  deptFinancials: genDeptFinancials(),
  appointments: genAppointments(),
  bedForecast: genBedForecast(),
  nabh: genNABHCheckpoints(),
};

// ── Summary calculations ─────────────────────────────────────────
export const totalRevenue = DATA.revenue.reduce((a, b) => a + b.revenue, 0);
export const totalOpex = DATA.revenue.reduce((a, b) => a + b.opex, 0);
export const totalPatients = DATA.patients.reduce((a, b) => a + b.inpatient + b.outpatient, 0);
export const totalStaff = DATA.hr.reduce((a, b) => a + b.count, 0);
export const netProfit = totalRevenue - totalOpex;
export const totalInsuranceClaims = DATA.insurance.reduce((a, b) => a + b.claims, 0);
export const totalInsurancePending = DATA.insurance.reduce((a, b) => a + b.pending, 0);

// ── Formatters ───────────────────────────────────────────────────
export const fmt = (n) => {
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(1)}Cr`;
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  return `₹${n.toLocaleString("en-IN")}`;
};
export const fmtNum = (n) => n.toLocaleString("en-IN");
