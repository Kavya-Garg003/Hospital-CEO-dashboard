
import { useState, useEffect, useRef, useCallback } from "react";

// ─── SYNTHETIC DATA ENGINE ────────────────────────────────────────────────────
const HOSPITAL = {
  name: "Aarogya Multi-Specialty Hospital",
  location: "Chennai, Tamil Nadu",
  beds: 450,
  established: 2008,
};

const DEPARTMENTS = [
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

const MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"];

function seed(s) {
  let x = Math.sin(s) * 10000;
  return x - Math.floor(x);
}

function genRevenue() {
  return MONTHS.map((m, i) => ({
    month: m,
    revenue: Math.round(8500000 + seed(i * 7) * 3500000),
    opex: Math.round(5800000 + seed(i * 3) * 1200000),
    insurance: Math.round(3200000 + seed(i * 11) * 1500000),
    outOfPocket: Math.round(2800000 + seed(i * 5) * 1000000),
  }));
}

function genPatients() {
  return MONTHS.map((m, i) => ({
    month: m,
    inpatient: Math.round(1200 + seed(i * 13) * 400),
    outpatient: Math.round(3800 + seed(i * 17) * 800),
    emergency: Math.round(420 + seed(i * 19) * 150),
    surgeries: Math.round(280 + seed(i * 23) * 90),
  }));
}

function genOT() {
  return DEPARTMENTS.filter((d) => d.beds > 0).map((dept, i) => ({
    dept: dept.name,
    scheduled: Math.round(60 + seed(i * 29) * 40),
    completed: Math.round(50 + seed(i * 31) * 35),
    cancelled: Math.round(5 + seed(i * 37) * 10),
    avgDuration: Math.round(90 + seed(i * 41) * 120),
    utilization: Math.round(68 + seed(i * 43) * 25),
  }));
}

function genHR() {
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

function genInsurance() {
  const insurers = [
    "Star Health", "HDFC ERGO", "Bajaj Allianz", "New India Assurance",
    "United India", "Medi Assist TPA", "Vidal Health TPA", "Raksha TPA",
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

function genBedOccupancy() {
  return DEPARTMENTS.filter((d) => d.beds > 0).map((dept, i) => ({
    dept: dept.name,
    totalBeds: dept.beds,
    occupied: Math.round(dept.beds * (0.6 + seed(i * 97) * 0.35)),
    color: dept.color,
  }));
}

function genDeptFinancials() {
  return DEPARTMENTS.map((dept, i) => ({
    dept: dept.name,
    revenue: Math.round(800000 + seed(i * 101) * 2200000),
    cost: Math.round(500000 + seed(i * 103) * 1500000),
    color: dept.color,
  })).map((d) => ({ ...d, profit: d.revenue - d.cost, margin: +(((d.revenue - d.cost) / d.revenue) * 100).toFixed(1) }));
}

function genAppointments() {
  const statuses = ["Confirmed", "Completed", "Cancelled", "No-Show"];
  const doctors = [
    "Dr. Ramesh Iyer", "Dr. Meena Suresh", "Dr. Arjun Pillai", "Dr. Priya Nair",
    "Dr. Kavitha Rajan", "Dr. Sujatha Venkat", "Dr. Karthik Mohan", "Dr. Balaji Krishnan",
  ];
  return Array.from({ length: 40 }, (_, i) => ({
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

// Pre-compute all data
const DATA = {
  revenue: genRevenue(),
  patients: genPatients(),
  ot: genOT(),
  hr: genHR(),
  insurance: genInsurance(),
  bedOccupancy: genBedOccupancy(),
  deptFinancials: genDeptFinancials(),
  appointments: genAppointments(),
};

const totalRevenue = DATA.revenue.reduce((a, b) => a + b.revenue, 0);
const totalOpex = DATA.revenue.reduce((a, b) => a + b.opex, 0);
const totalPatients = DATA.patients.reduce((a, b) => a + b.inpatient + b.outpatient, 0);
const totalStaff = DATA.hr.reduce((a, b) => a + b.count, 0);
const netProfit = totalRevenue - totalOpex;
const totalInsuranceClaims = DATA.insurance.reduce((a, b) => a + b.claims, 0);
const totalInsurancePending = DATA.insurance.reduce((a, b) => a + b.pending, 0);

// ─── FORMATTERS ──────────────────────────────────────────────────────────────
const fmt = (n) => {
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(1)}Cr`;
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  return `₹${n.toLocaleString("en-IN")}`;
};
const fmtNum = (n) => n.toLocaleString("en-IN");

// ─── MINI SPARKLINE ───────────────────────────────────────────────────────────
function Spark({ data, color = "#3b82f6", height = 40 }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 120, h = height;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * (h - 4) - 2}`)
    .join(" ");
  return (
    <svg width={w} height={h} style={{ overflow: "visible" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

// ─── MINI BAR ─────────────────────────────────────────────────────────────────
function MiniBar({ value, max, color }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ flex: 1, background: "#f1f5f9", borderRadius: 4, height: 8, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, background: color, height: "100%", borderRadius: 4, transition: "width 0.5s" }} />
      </div>
      <span style={{ fontSize: 11, color: "#64748b", minWidth: 28 }}>{pct}%</span>
    </div>
  );
}

// ─── KPI CARD ─────────────────────────────────────────────────────────────────
function KPICard({ title, value, sub, trend, sparkData, color, icon }) {
  const up = trend >= 0;
  return (
    <div style={{
      background: "#fff", borderRadius: 14, padding: "18px 20px",
      border: "1px solid #e2e8f0", boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
      display: "flex", flexDirection: "column", gap: 8
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 12, color: "#64748b", fontWeight: 500, letterSpacing: "0.03em", textTransform: "uppercase" }}>{title}</div>
          <div style={{ fontSize: 26, fontWeight: 700, color: "#0f172a", marginTop: 4, lineHeight: 1 }}>{value}</div>
          {sub && <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{sub}</div>}
        </div>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: color + "18", display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 20
        }}>{icon}</div>
      </div>
      {sparkData && <Spark data={sparkData} color={color} />}
      {trend !== undefined && (
        <div style={{ fontSize: 12, color: up ? "#10b981" : "#ef4444", fontWeight: 600 }}>
          {up ? "▲" : "▼"} {Math.abs(trend)}% vs last month
        </div>
      )}
    </div>
  );
}

// ─── SECTION HEADER ───────────────────────────────────────────────────────────
function SectionHeader({ title, subtitle, icon }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 22 }}>{icon}</span>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#0f172a" }}>{title}</h2>
      </div>
      {subtitle && <p style={{ margin: "4px 0 0 30px", fontSize: 13, color: "#64748b" }}>{subtitle}</p>}
    </div>
  );
}

// ─── CHART COMPONENTS ─────────────────────────────────────────────────────────
function BarChart({ data, keys, colors, xKey, height = 220 }) {
  const max = Math.max(...data.flatMap((d) => keys.map((k) => d[k])));
  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={Math.max(600, data.length * 55)} height={height + 30}>
        {data.map((d, i) => {
          const x = i * (Math.max(600, data.length * 55) / data.length);
          const bw = (Math.max(600, data.length * 55) / data.length - 10) / keys.length;
          return (
            <g key={i}>
              {keys.map((k, ki) => {
                const bh = (d[k] / max) * height;
                return (
                  <rect key={k} x={x + 5 + ki * bw} y={height - bh} width={bw - 2} height={bh}
                    fill={colors[ki]} rx={2} opacity={0.85}>
                    <title>{k}: {d[k].toLocaleString()}</title>
                  </rect>
                );
              })}
              <text x={x + (Math.max(600, data.length * 55) / data.length) / 2} y={height + 20}
                textAnchor="middle" fontSize={10} fill="#94a3b8">{d[xKey]}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function LineChart({ data, keys, colors, xKey, height = 200, formatY }) {
  const allVals = data.flatMap((d) => keys.map((k) => d[k]));
  const min = Math.min(...allVals);
  const max = Math.max(...allVals);
  const w = 580, h = height;
  const px = (i) => (i / (data.length - 1)) * w;
  const py = (v) => h - ((v - min) / (max - min || 1)) * (h - 20) - 10;
  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={w + 20} height={h + 30}>
        {keys.map((k, ki) => {
          const pts = data.map((d, i) => `${px(i)},${py(d[k])}`).join(" ");
          return <polyline key={k} points={pts} fill="none" stroke={colors[ki]} strokeWidth={2.5} strokeLinejoin="round" />;
        })}
        {data.map((d, i) => (
          <text key={i} x={px(i)} y={h + 22} textAnchor="middle" fontSize={10} fill="#94a3b8">{d[xKey]}</text>
        ))}
      </svg>
      <div style={{ display: "flex", gap: 16, marginTop: 8, flexWrap: "wrap" }}>
        {keys.map((k, ki) => (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "#64748b" }}>
            <div style={{ width: 12, height: 3, background: colors[ki], borderRadius: 2 }} />
            {k}
          </div>
        ))}
      </div>
    </div>
  );
}

function DonutChart({ data, size = 140 }) {
  const total = data.reduce((a, b) => a + b.value, 0);
  let angle = -90;
  const r = 50, cx = size / 2, cy = size / 2;
  const slices = data.map((d) => {
    const a = (d.value / total) * 360;
    const start = angle;
    angle += a;
    const toRad = (deg) => (deg * Math.PI) / 180;
    const x1 = cx + r * Math.cos(toRad(start));
    const y1 = cy + r * Math.sin(toRad(start));
    const x2 = cx + r * Math.cos(toRad(start + a));
    const y2 = cy + r * Math.sin(toRad(start + a));
    const large = a > 180 ? 1 : 0;
    return { ...d, path: `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large},1 ${x2},${y2} Z`, pct: Math.round((d.value / total) * 100) };
  });
  return (
    <svg width={size} height={size}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f1f5f9" strokeWidth={20} />
      {slices.map((s, i) => (
        <path key={i} d={s.path} fill={s.color} opacity={0.88}>
          <title>{s.label}: {s.pct}%</title>
        </path>
      ))}
      <circle cx={cx} cy={cy} r={32} fill="white" />
      <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle" fontSize={11} fontWeight={700} fill="#0f172a">
        {data.length} Types
      </text>
    </svg>
  );
}

// ─── TABLE ────────────────────────────────────────────────────────────────────
function Table({ cols, rows, maxH = 300 }) {
  return (
    <div style={{ overflowY: "auto", maxHeight: maxH, borderRadius: 10, border: "1px solid #e2e8f0" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f8fafc", position: "sticky", top: 0 }}>
            {cols.map((c) => (
              <th key={c.key} style={{ padding: "10px 12px", textAlign: c.right ? "right" : "left", fontWeight: 600, color: "#475569", borderBottom: "1px solid #e2e8f0", fontSize: 12, whiteSpace: "nowrap" }}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? "#fff" : "#f8fafc", transition: "background 0.15s" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#eff6ff")}
              onMouseLeave={(e) => (e.currentTarget.style.background = i % 2 === 0 ? "#fff" : "#f8fafc")}>
              {cols.map((c) => (
                <td key={c.key} style={{ padding: "9px 12px", borderBottom: "1px solid #f1f5f9", textAlign: c.right ? "right" : "left", color: c.color ? c.color(row[c.key]) : "#334155", whiteSpace: "nowrap" }}>
                  {c.render ? c.render(row[c.key], row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── STATUS BADGE ─────────────────────────────────────────────────────────────
function Badge({ text }) {
  const map = {
    Confirmed: ["#dbeafe", "#1d4ed8"], Completed: ["#d1fae5", "#065f46"],
    Cancelled: ["#fee2e2", "#991b1b"], "No-Show": ["#fef3c7", "#92400e"],
    Approved: ["#d1fae5", "#065f46"], Pending: ["#fef3c7", "#92400e"],
    Rejected: ["#fee2e2", "#991b1b"],
  };
  const [bg, fg] = map[text] || ["#f1f5f9", "#475569"];
  return (
    <span style={{ background: bg, color: fg, padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 600 }}>{text}</span>
  );
}

// ─── AI CONCIERGE ─────────────────────────────────────────────────────────────
const AI_KNOWLEDGE = {
  revenue: `Total annual revenue: ${fmt(totalRevenue)}. Net profit: ${fmt(netProfit)}. Profit margin: ${((netProfit / totalRevenue) * 100).toFixed(1)}%. Best month: ${DATA.revenue.reduce((a, b) => (b.revenue > a.revenue ? b : a)).month}.`,
  patients: `Total patients served: ${fmtNum(totalPatients)}. Average monthly inpatients: ${Math.round(DATA.patients.reduce((a, b) => a + b.inpatient, 0) / 12)}. Emergency cases: ${DATA.patients.reduce((a, b) => a + b.emergency, 0)}.`,
  staff: `Total staff: ${fmtNum(totalStaff)}. Doctors: ${DATA.hr.filter((r) => r.role.includes("Consultant") || r.role.includes("Resident")).reduce((a, b) => a + b.count, 0)}. Nurses: ${DATA.hr.find((r) => r.role === "Staff Nurse")?.count}.`,
  beds: `Total beds: ${HOSPITAL.beds}. Highest occupancy: ${DATA.bedOccupancy.reduce((a, b) => (b.occupied / b.totalBeds > a.occupied / a.totalBeds ? b : a)).dept}.`,
  insurance: `Total claims: ${fmtNum(totalInsuranceClaims)}. Pending: ${fmtNum(totalInsurancePending)}. Top insurer: ${DATA.insurance.reduce((a, b) => (b.claims > a.claims ? b : a)).insurer}.`,
  profit: `Most profitable dept: ${DATA.deptFinancials.reduce((a, b) => (b.profit > a.profit ? b : a)).dept}. Least profitable: ${DATA.deptFinancials.reduce((a, b) => (b.profit < a.profit ? b : a)).dept}.`,
  ot: `OT utilization avg: ${Math.round(DATA.ot.reduce((a, b) => a + b.utilization, 0) / DATA.ot.length)}%. Highest: ${DATA.ot.reduce((a, b) => (b.utilization > a.utilization ? b : a)).dept}.`,
};

function matchIntent(q) {
  const lq = q.toLowerCase();
  if (lq.includes("revenue") || lq.includes("income") || lq.includes("earning") || lq.includes("money") || lq.includes("profit")) return AI_KNOWLEDGE.profit + " " + AI_KNOWLEDGE.revenue;
  if (lq.includes("patient") || lq.includes("admission") || lq.includes("discharge")) return AI_KNOWLEDGE.patients;
  if (lq.includes("staff") || lq.includes("employee") || lq.includes("doctor") || lq.includes("nurse") || lq.includes("hr")) return AI_KNOWLEDGE.staff;
  if (lq.includes("bed") || lq.includes("occupancy") || lq.includes("ward")) return AI_KNOWLEDGE.beds;
  if (lq.includes("insurance") || lq.includes("claim") || lq.includes("tpa")) return AI_KNOWLEDGE.insurance;
  if (lq.includes("ot") || lq.includes("operation") || lq.includes("surgery") || lq.includes("theatre")) return AI_KNOWLEDGE.ot;
  if (lq.includes("hello") || lq.includes("hi ") || lq === "hi") return `Namaste! I am your AI Hospital Concierge. I can help you with revenue, patients, staff, beds, insurance claims, OT utilization, and department-wise profitability. What would you like to know?`;
  if (lq.includes("summary") || lq.includes("overview") || lq.includes("status")) return `Here is your hospital snapshot: ${AI_KNOWLEDGE.revenue} ${AI_KNOWLEDGE.patients} ${AI_KNOWLEDGE.staff}`;
  return `I have data on revenue, patients, staff, beds, insurance, OT, and department financials. Could you be more specific? For example: "Which department is most profitable?" or "What is our bed occupancy rate?"`;
}

function AIConcierge() {
  const [messages, setMessages] = useState([
    { role: "ai", text: `Namaste! 🙏 I am your AI Hospital Concierge for ${HOSPITAL.name}. Ask me about revenue, patients, staff, OT, or any department. I'm connected to live hospital data.` },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const chatRef = useRef(null);
  const recogRef = useRef(null);

  const sendMsg = useCallback(async (q) => {
    if (!q.trim()) return;
    const userMsg = { role: "user", text: q };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    // Try Anthropic API first
    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          system: `You are the AI concierge for ${HOSPITAL.name}, a multi-specialty hospital in ${HOSPITAL.location}. You have access to this hospital data: ${JSON.stringify(AI_KNOWLEDGE)}. Answer concisely in 2-4 sentences. Be specific with numbers. Address the CEO respectfully.`,
          messages: [{ role: "user", content: q }],
        }),
      });
      const data = await res.json();
      const text = data.content?.[0]?.text || matchIntent(q);
      setMessages((m) => [...m, { role: "ai", text }]);
    } catch {
      setMessages((m) => [...m, { role: "ai", text: matchIntent(q) }]);
    }
    setLoading(false);
  }, []);

  const startVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert("Voice not supported in this browser."); return; }
    if (listening) { recogRef.current?.stop(); setListening(false); return; }
    const r = new SR();
    r.lang = "en-IN";
    r.onresult = (e) => { sendMsg(e.results[0][0].transcript); setListening(false); };
    r.onerror = () => setListening(false);
    r.onend = () => setListening(false);
    r.start();
    recogRef.current = r;
    setListening(true);
  };

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages, loading]);

  return (
    <div style={{ background: "#fff", borderRadius: 14, border: "1px solid #e2e8f0", overflow: "hidden", boxShadow: "0 1px 4px rgba(0,0,0,0.06)" }}>
      <div style={{ background: "linear-gradient(135deg, #1e40af, #3b82f6)", padding: "14px 18px", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 36, height: 36, borderRadius: "50%", background: "rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>🤖</div>
        <div>
          <div style={{ color: "#fff", fontWeight: 700, fontSize: 14 }}>AI Hospital Concierge</div>
          <div style={{ color: "#bfdbfe", fontSize: 11 }}>RAG-powered • Connected to live data</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#4ade80" }} />
          <span style={{ color: "#bfdbfe", fontSize: 11 }}>Online</span>
        </div>
      </div>
      <div ref={chatRef} style={{ height: 280, overflowY: "auto", padding: 14, display: "flex", flexDirection: "column", gap: 10, background: "#f8fafc" }}>
        {messages.map((m, i) => (
          <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{
              maxWidth: "82%", padding: "9px 13px", borderRadius: m.role === "user" ? "14px 14px 2px 14px" : "14px 14px 14px 2px",
              background: m.role === "user" ? "#1e40af" : "#fff",
              color: m.role === "user" ? "#fff" : "#334155",
              fontSize: 13, lineHeight: 1.55,
              boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
              border: m.role === "ai" ? "1px solid #e2e8f0" : "none",
            }}>{m.text}</div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", gap: 5, padding: "9px 13px", background: "#fff", borderRadius: "14px 14px 14px 2px", width: "fit-content", border: "1px solid #e2e8f0" }}>
            {[0, 1, 2].map((i) => (
              <div key={i} style={{ width: 7, height: 7, borderRadius: "50%", background: "#94a3b8", animation: `pulse 1.2s ${i * 0.2}s infinite` }} />
            ))}
          </div>
        )}
      </div>
      <div style={{ padding: 12, borderTop: "1px solid #e2e8f0", display: "flex", gap: 8, background: "#fff" }}>
        <input
          value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMsg(input)}
          placeholder="Ask about revenue, patients, OT, staff…"
          style={{ flex: 1, padding: "9px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 13, outline: "none", color: "#334155" }}
        />
        <button onClick={startVoice} style={{
          padding: "9px 12px", borderRadius: 8, border: "1px solid " + (listening ? "#ef4444" : "#e2e8f0"),
          background: listening ? "#fee2e2" : "#f8fafc", cursor: "pointer", fontSize: 16, transition: "all 0.2s"
        }}>🎤</button>
        <button onClick={() => sendMsg(input)} style={{
          padding: "9px 16px", borderRadius: 8, border: "none",
          background: "#1e40af", color: "#fff", cursor: "pointer", fontWeight: 600, fontSize: 13
        }}>Send</button>
      </div>
      <div style={{ padding: "8px 12px", display: "flex", gap: 6, flexWrap: "wrap", borderTop: "1px solid #f1f5f9" }}>
        {["Which dept is most profitable?", "OT utilization?", "Insurance claims status?", "Staff headcount?"].map((q) => (
          <button key={q} onClick={() => sendMsg(q)} style={{
            padding: "4px 10px", borderRadius: 20, border: "1px solid #e2e8f0",
            background: "#f8fafc", fontSize: 11, cursor: "pointer", color: "#475569"
          }}>{q}</button>
        ))}
      </div>
    </div>
  );
}

// ─── ALERTS PANEL ─────────────────────────────────────────────────────────────
const ALERTS = [
  { type: "danger", icon: "🚨", text: "ICU occupancy at 94% — 3 beds remaining. Consider discharge planning." },
  { type: "warn", icon: "⚠️", text: `${fmtNum(totalInsurancePending)} insurance claims pending > 30 days. Follow up with Medi Assist TPA.` },
  { type: "warn", icon: "⚠️", text: "OT cancellation rate in Orthopaedics is 18% this month — above 10% threshold." },
  { type: "info", icon: "💡", text: "Cardiology revenue up 22% YoY. Consider expanding capacity by 10 beds." },
  { type: "info", icon: "💡", text: "Pharmacy department showing 31% margin — highest across all units." },
  { type: "success", icon: "✅", text: "Patient satisfaction score: 4.6/5. Top performer: Paediatrics (4.8/5)." },
];

function AlertsPanel() {
  const colors = { danger: "#fee2e2", warn: "#fef3c7", info: "#dbeafe", success: "#d1fae5" };
  const borders = { danger: "#fca5a5", warn: "#fcd34d", info: "#93c5fd", success: "#6ee7b7" };
  const texts = { danger: "#991b1b", warn: "#92400e", info: "#1e40af", success: "#065f46" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {ALERTS.map((a, i) => (
        <div key={i} style={{
          background: colors[a.type], border: `1px solid ${borders[a.type]}`,
          borderRadius: 10, padding: "10px 14px", display: "flex", gap: 10, alignItems: "flex-start"
        }}>
          <span style={{ fontSize: 16, flexShrink: 0 }}>{a.icon}</span>
          <p style={{ margin: 0, fontSize: 13, color: texts[a.type], lineHeight: 1.5 }}>{a.text}</p>
        </div>
      ))}
    </div>
  );
}

// ─── DEPARTMENT OVERVIEW ──────────────────────────────────────────────────────
function DeptOverview() {
  const [filter, setFilter] = useState("");
  const filtered = DATA.deptFinancials.filter((d) =>
    d.dept.toLowerCase().includes(filter.toLowerCase())
  );
  return (
    <div>
      <input value={filter} onChange={(e) => setFilter(e.target.value)}
        placeholder="Filter department…"
        style={{ marginBottom: 10, padding: "7px 12px", borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13, width: "100%", boxSizing: "border-box", color: "#334155" }} />
      <Table
        cols={[
          { key: "dept", label: "Department" },
          { key: "revenue", label: "Revenue", right: true, render: (v) => fmt(v) },
          { key: "cost", label: "Cost", right: true, render: (v) => fmt(v) },
          { key: "profit", label: "Profit", right: true, render: (v) => <span style={{ color: v > 0 ? "#10b981" : "#ef4444", fontWeight: 600 }}>{fmt(v)}</span> },
          { key: "margin", label: "Margin", right: true, render: (v) => <Badge text={v > 20 ? "Approved" : v > 0 ? "Pending" : "Rejected"} /> },
        ]}
        rows={filtered}
      />
    </div>
  );
}

// ─── BED OCCUPANCY VISUAL ─────────────────────────────────────────────────────
function BedOccupancyGrid() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10 }}>
      {DATA.bedOccupancy.map((b) => {
        const pct = Math.round((b.occupied / b.totalBeds) * 100);
        const status = pct > 90 ? "#ef4444" : pct > 75 ? "#f59e0b" : "#10b981";
        return (
          <div key={b.dept} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: "12px 14px", borderLeft: `4px solid ${status}` }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#334155", marginBottom: 6 }}>{b.dept}</div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: "#94a3b8" }}>{b.occupied}/{b.totalBeds} beds</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: status }}>{pct}%</span>
            </div>
            <MiniBar value={b.occupied} max={b.totalBeds} color={status} />
          </div>
        );
      })}
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
const TABS = [
  { id: "overview", label: "📊 Overview" },
  { id: "finance", label: "💰 Finance & P&L" },
  { id: "patients", label: "🏥 Patients" },
  { id: "departments", label: "🔬 Departments" },
  { id: "hr", label: "👥 HR & Payroll" },
  { id: "ot", label: "🔪 OT & Surgeries" },
  { id: "insurance", label: "📋 Insurance" },
  { id: "appointments", label: "📅 Appointments" },
  { id: "ai", label: "🤖 AI Concierge" },
];

export default function App() {
  const [tab, setTab] = useState("overview");
  const [deptFilter, setDeptFilter] = useState("");
  const [aptFilter, setAptFilter] = useState("");

  const filteredApts = DATA.appointments.filter(
    (a) => a.dept.toLowerCase().includes(aptFilter.toLowerCase()) || a.doctor.toLowerCase().includes(aptFilter.toLowerCase()) || a.status.toLowerCase().includes(aptFilter.toLowerCase())
  );

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif", background: "#f1f5f9", minHeight: "100vh", color: "#334155" }}>
      {/* TOP NAV */}
      <div style={{ background: "linear-gradient(135deg, #1e3a8a 0%, #1e40af 60%, #2563eb 100%)", padding: "0 24px", boxShadow: "0 2px 12px rgba(30,58,138,0.3)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, paddingTop: 14, paddingBottom: 10 }}>
          <div style={{ width: 42, height: 42, borderRadius: 10, background: "rgba(255,255,255,0.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22 }}>🏥</div>
          <div>
            <div style={{ color: "#fff", fontWeight: 800, fontSize: 17, letterSpacing: "-0.01em" }}>{HOSPITAL.name}</div>
            <div style={{ color: "#93c5fd", fontSize: 11 }}>{HOSPITAL.location} • Est. {HOSPITAL.established} • {HOSPITAL.beds} Beds • CEO Dashboard</div>
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
            <div style={{ background: "rgba(255,255,255,0.12)", borderRadius: 8, padding: "5px 12px", fontSize: 12, color: "#e0f2fe" }}>
              FY 2024–25 • Live Data
            </div>
            <div style={{ width: 35, height: 35, borderRadius: "50%", background: "rgba(255,255,255,0.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>👤</div>
          </div>
        </div>
        {/* TABS */}
        <div style={{ display: "flex", gap: 2, overflowX: "auto", paddingBottom: 1 }}>
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              padding: "9px 14px", border: "none", cursor: "pointer", fontSize: 12.5, fontWeight: 600,
              background: tab === t.id ? "rgba(255,255,255,0.15)" : "transparent",
              color: tab === t.id ? "#fff" : "#93c5fd",
              borderRadius: "8px 8px 0 0",
              borderBottom: tab === t.id ? "2px solid #60a5fa" : "2px solid transparent",
              transition: "all 0.15s", whiteSpace: "nowrap"
            }}>{t.label}</button>
          ))}
        </div>
      </div>

      {/* CONTENT */}
      <div style={{ padding: 24, maxWidth: 1400, margin: "0 auto" }}>

        {/* ── OVERVIEW ── */}
        {tab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 14 }}>
              <KPICard title="Annual Revenue" value={fmt(totalRevenue)} sub="FY 2024-25" trend={8.4} sparkData={DATA.revenue.map((d) => d.revenue)} color="#3b82f6" icon="💰" />
              <KPICard title="Net Profit" value={fmt(netProfit)} sub={`${((netProfit / totalRevenue) * 100).toFixed(1)}% margin`} trend={5.2} sparkData={DATA.revenue.map((d) => d.revenue - d.opex)} color="#10b981" icon="📈" />
              <KPICard title="Total Patients" value={fmtNum(totalPatients)} sub="Inpatient + Outpatient" trend={3.1} sparkData={DATA.patients.map((d) => d.inpatient + d.outpatient)} color="#8b5cf6" icon="🏥" />
              <KPICard title="Bed Occupancy" value="78%" sub={`${Math.round(0.78 * HOSPITAL.beds)}/${HOSPITAL.beds} beds occupied`} trend={2.0} sparkData={[72, 74, 77, 76, 78, 80, 78, 79, 77, 76, 79, 78]} color="#f59e0b" icon="🛏️" />
              <KPICard title="Total Staff" value={fmtNum(totalStaff)} sub="Across all departments" trend={1.5} sparkData={[700, 710, 718, 720, 722, 725, 720, 718, 722, 725, 728, 720]} color="#ec4899" icon="👥" />
              <KPICard title="Insurance Claims" value={fmtNum(totalInsuranceClaims)} sub={`${fmtNum(totalInsurancePending)} pending`} trend={-2.1} sparkData={DATA.insurance.map((d) => d.claims)} color="#ef4444" icon="📋" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
                <SectionHeader title="Revenue vs Expenditure" subtitle="Monthly trend (FY 2024-25)" icon="📊" />
                <LineChart
                  data={DATA.revenue} xKey="month"
                  keys={["revenue", "opex"]}
                  colors={["#3b82f6", "#ef4444"]}
                />
              </div>
              <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
                <SectionHeader title="AI Alerts & Insights" subtitle="Priority actions for the CEO" icon="🔔" />
                <AlertsPanel />
              </div>
            </div>

            <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
              <SectionHeader title="Department P&L at a Glance" subtitle="Revenue, cost, and profit by department" icon="🔬" />
              <DeptOverview />
            </div>
          </div>
        )}

        {/* ── FINANCE ── */}
        {tab === "finance" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 14 }}>
              <KPICard title="Gross Revenue" value={fmt(totalRevenue)} trend={8.4} color="#3b82f6" icon="💰" sparkData={DATA.revenue.map((d) => d.revenue)} />
              <KPICard title="Operating Costs" value={fmt(totalOpex)} trend={4.1} color="#ef4444" icon="📤" sparkData={DATA.revenue.map((d) => d.opex)} />
              <KPICard title="Net Profit" value={fmt(netProfit)} sub={`Margin: ${((netProfit / totalRevenue) * 100).toFixed(1)}%`} trend={5.2} color="#10b981" icon="📈" sparkData={DATA.revenue.map((d) => d.revenue - d.opex)} />
              <KPICard title="Insurance Revenue" value={fmt(DATA.revenue.reduce((a, b) => a + b.insurance, 0))} trend={6.5} color="#8b5cf6" icon="🏦" sparkData={DATA.revenue.map((d) => d.insurance)} />
              <KPICard title="OOP Revenue" value={fmt(DATA.revenue.reduce((a, b) => a + b.outOfPocket, 0))} trend={3.0} color="#f59e0b" icon="💳" sparkData={DATA.revenue.map((d) => d.outOfPocket)} />
            </div>

            <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
              <SectionHeader title="Monthly Revenue Breakdown" icon="📊" subtitle="Insurance vs Out-of-Pocket vs Total Revenue" />
              <BarChart data={DATA.revenue} xKey="month" keys={["revenue", "insurance", "outOfPocket", "opex"]} colors={["#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444"]} />
              <div style={{ display: "flex", gap: 16, marginTop: 10, flexWrap: "wrap" }}>
                {["Total Revenue", "Insurance", "Out of Pocket", "Expenses"].map((l, i) => (
                  <div key={l} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "#64748b" }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: ["#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444"][i] }} />
                    {l}
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
              <SectionHeader title="Department-wise P&L" icon="🏦" subtitle="Profit, cost, and margin by unit" />
              <Table
                cols={[
                  { key: "dept", label: "Department" },
                  { key: "revenue", label: "Revenue", right: true, render: (v) => fmt(v) },
                  { key: "cost", label: "Cost", right: true, render: (v) => fmt(v) },
                  { key: "profit", label: "Profit/Loss", right: true, render: (v) => <span style={{ color: v > 0 ? "#10b981" : "#ef4444", fontWeight: 700 }}>{fmt(v)}</span> },
                  { key: "margin", label: "Net Margin %", right: true, render: (v) => <span style={{ color: v > 20 ? "#10b981" : v > 0 ? "#f59e0b" : "#ef4444" }}>{v}%</span> },
                ]}
                rows={DATA.deptFinancials}
                maxH={400}
              />
            </div>
          </div>
        )}

        {/* ── PATIENTS ── */}
        {tab === "patients" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 14 }}>
              <KPICard title="Total Inpatients" value={fmtNum(DATA.patients.reduce((a, b) => a + b.inpatient, 0))} trend={3.5} color="#3b82f6" icon="🛏️" sparkData={DATA.patients.map((d) => d.inpatient)} />
              <KPICard title="Total Outpatients" value={fmtNum(DATA.patients.reduce((a, b) => a + b.outpatient, 0))} trend={4.2} color="#10b981" icon="🚶" sparkData={DATA.patients.map((d) => d.outpatient)} />
              <KPICard title="Emergency Cases" value={fmtNum(DATA.patients.reduce((a, b) => a + b.emergency, 0))} trend={-1.2} color="#ef4444" icon="🚑" sparkData={DATA.patients.map((d) => d.emergency)} />
              <KPICard title="Surgeries Done" value={fmtNum(DATA.patients.reduce((a, b) => a + b.surgeries, 0))} trend={6.1} color="#8b5cf6" icon="🔪" sparkData={DATA.patients.map((d) => d.surgeries)} />
              <KPICard title="Avg LOS" value="4.2 days" sub="Avg length of stay" trend={-0.8} color="#f59e0b" icon="📅" sparkData={[4.5, 4.3, 4.1, 4.4, 4.2, 4.0, 4.3, 4.2, 4.1, 4.3, 4.2, 4.0]} />
            </div>
            <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
              <SectionHeader title="Patient Volume Trend" icon="📈" subtitle="Monthly inpatient, outpatient, emergency, and surgeries" />
              <LineChart data={DATA.patients} xKey="month" keys={["inpatient", "outpatient", "emergency", "surgeries"]} colors={["#3b82f6", "#10b981", "#ef4444", "#8b5cf6"]} />
            </div>
            <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
              <SectionHeader title="Bed Occupancy by Department" icon="🛏️" />
              <BedOccupancyGrid />
            </div>
          </div>
        )}

        {/* ── DEPARTMENTS ── */}
        {tab === "departments" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader title="Department Command Centre" icon="🔬" subtitle="Department-wise stats, financials, and performance" />
            <input value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}
              placeholder="Search department…"
              style={{ padding: "9px 14px", borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 13, color: "#334155", outline: "none" }} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
              {DEPARTMENTS.filter((d) => d.name.toLowerCase().includes(deptFilter.toLowerCase())).map((dept) => {
                const fin = DATA.deptFinancials.find((f) => f.dept === dept.name);
                const occ = DATA.bedOccupancy.find((b) => b.dept === dept.name);
                return (
                  <div key={dept.id} style={{
                    background: "#fff", borderRadius: 14, border: "1px solid #e2e8f0",
                    borderTop: `4px solid ${dept.color}`, padding: "16px 18px",
                    boxShadow: "0 1px 4px rgba(0,0,0,0.05)"
                  }}>
                    <div style={{ fontWeight: 700, fontSize: 15, color: "#0f172a", marginBottom: 2 }}>{dept.name}</div>
                    <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 10 }}>{dept.head}</div>
                    {fin && (
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
                        <div style={{ background: "#f8fafc", borderRadius: 8, padding: "8px 10px" }}>
                          <div style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>Revenue</div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a" }}>{fmt(fin.revenue)}</div>
                        </div>
                        <div style={{ background: "#f8fafc", borderRadius: 8, padding: "8px 10px" }}>
                          <div style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>Profit</div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: fin.profit > 0 ? "#10b981" : "#ef4444" }}>{fmt(fin.profit)}</div>
                        </div>
                      </div>
                    )}
                    {occ && (
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12, color: "#64748b" }}>
                          <span>Bed Occupancy</span>
                          <span style={{ fontWeight: 600 }}>{Math.round((occ.occupied / occ.totalBeds) * 100)}%</span>
                        </div>
                        <MiniBar value={occ.occupied} max={occ.totalBeds} color={dept.color} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── HR ── */}
        {tab === "hr" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 14 }}>
              <KPICard title="Total Workforce" value={fmtNum(totalStaff)} trend={1.5} color="#3b82f6" icon="👥" sparkData={[690, 700, 705, 710, 712, 718, 715, 718, 720, 722, 724, 720]} />
              <KPICard title="Present Today" value={fmtNum(DATA.hr.reduce((a, b) => a + b.present, 0))} sub="Attendance rate" trend={0.5} color="#10b981" icon="✅" sparkData={[640, 650, 655, 660, 658, 665, 662, 660, 665, 668, 665, 662]} />
              <KPICard title="On Leave" value={fmtNum(DATA.hr.reduce((a, b) => a + b.onLeave, 0))} trend={-2.0} color="#f59e0b" icon="📅" sparkData={[45, 42, 40, 38, 42, 39, 41, 40, 38, 37, 39, 41]} />
              <KPICard title="Monthly Payroll" value={fmt(DATA.hr.reduce((a, b) => a + b.count * b.salary, 0))} trend={2.1} color="#8b5cf6" icon="💸" sparkData={[4.2, 4.3, 4.25, 4.28, 4.3, 4.32, 4.3, 4.28, 4.32, 4.35, 4.32, 4.3].map((v) => v * 1e7)} />
              <KPICard title="Avg Attrition" value={`${(DATA.hr.reduce((a, b) => a + b.attrition, 0) / DATA.hr.length).toFixed(1)}%`} trend={-0.3} color="#ef4444" icon="🚪" sparkData={[5, 4.8, 4.6, 4.8, 4.5, 4.6, 4.4, 4.3, 4.5, 4.4, 4.2, 4.3]} />
            </div>
            <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
              <SectionHeader title="Staff Roster & Payroll" icon="👥" subtitle="Headcount, attendance, salary, and attrition by role" />
              <Table
                cols={[
                  { key: "role", label: "Role" },
                  { key: "count", label: "Headcount", right: true, render: (v) => fmtNum(v) },
                  { key: "present", label: "Present", right: true, render: (v) => fmtNum(v) },
                  { key: "onLeave", label: "On Leave", right: true },
                  { key: "salary", label: "Monthly CTC", right: true, render: (v) => `₹${v.toLocaleString("en-IN")}` },
                  { key: "count", label: "Total Payroll", right: true, render: (v, row) => fmt(v * row.salary) },
                  { key: "attrition", label: "Attrition %", right: true, render: (v) => <span style={{ color: v > 5 ? "#ef4444" : "#10b981" }}>{v}%</span> },
                  { key: "overtimeHrs", label: "OT Hrs/mo", right: true, render: (v) => <span style={{ color: v > 25 ? "#ef4444" : "#64748b" }}>{v}h</span> },
                ]}
                rows={DATA.hr}
                maxH={420}
              />
            </div>
          </div>
        )}

        {/* ── OT ── */}
        {tab === "ot" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 14 }}>
              <KPICard title="Total Surgeries" value={fmtNum(DATA.ot.reduce((a, b) => a + b.completed, 0))} trend={5.0} color="#8b5cf6" icon="🔪" sparkData={DATA.ot.map((d) => d.completed)} />
              <KPICard title="OT Utilization" value={`${Math.round(DATA.ot.reduce((a, b) => a + b.utilization, 0) / DATA.ot.length)}%`} trend={2.5} color="#3b82f6" icon="⏱️" sparkData={DATA.ot.map((d) => d.utilization)} />
              <KPICard title="Cancellations" value={fmtNum(DATA.ot.reduce((a, b) => a + b.cancelled, 0))} trend={-3.0} color="#ef4444" icon="❌" sparkData={DATA.ot.map((d) => d.cancelled)} />
              <KPICard title="Avg Duration" value={`${Math.round(DATA.ot.reduce((a, b) => a + b.avgDuration, 0) / DATA.ot.length)} min`} trend={-1.2} color="#10b981" icon="⏰" sparkData={DATA.ot.map((d) => d.avgDuration)} />
            </div>
            <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
              <SectionHeader title="OT Performance by Department" icon="🏥" subtitle="Scheduled, completed, cancelled surgeries and utilization" />
              <Table
                cols={[
                  { key: "dept", label: "Department" },
                  { key: "scheduled", label: "Scheduled", right: true },
                  { key: "completed", label: "Completed", right: true },
                  { key: "cancelled", label: "Cancelled", right: true, render: (v) => <span style={{ color: v > 10 ? "#ef4444" : "#64748b" }}>{v}</span> },
                  { key: "avgDuration", label: "Avg Duration", right: true, render: (v) => `${v} min` },
                  { key: "utilization", label: "OT Utilization", right: true, render: (v) => (
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <div style={{ width: 60, background: "#f1f5f9", borderRadius: 4, height: 6 }}>
                        <div style={{ width: `${v}%`, background: v > 85 ? "#ef4444" : v > 70 ? "#f59e0b" : "#10b981", height: "100%", borderRadius: 4 }} />
                      </div>
                      <span style={{ color: v > 85 ? "#ef4444" : v > 70 ? "#f59e0b" : "#10b981", fontWeight: 600 }}>{v}%</span>
                    </div>
                  )},
                ]}
                rows={DATA.ot}
                maxH={400}
              />
            </div>
          </div>
        )}

        {/* ── INSURANCE ── */}
        {tab === "insurance" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 14 }}>
              <KPICard title="Total Claims" value={fmtNum(totalInsuranceClaims)} trend={6.1} color="#3b82f6" icon="📋" sparkData={DATA.insurance.map((d) => d.claims)} />
              <KPICard title="Approved Claims" value={fmtNum(DATA.insurance.reduce((a, b) => a + b.approved, 0))} trend={5.5} color="#10b981" icon="✅" sparkData={DATA.insurance.map((d) => d.approved)} />
              <KPICard title="Pending Claims" value={fmtNum(totalInsurancePending)} trend={-3.0} color="#f59e0b" icon="⏳" sparkData={DATA.insurance.map((d) => d.pending)} />
              <KPICard title="Rejected Claims" value={fmtNum(DATA.insurance.reduce((a, b) => a + b.rejected, 0))} trend={-4.2} color="#ef4444" icon="❌" sparkData={DATA.insurance.map((d) => d.rejected)} />
              <KPICard title="Total Claim Value" value={fmt(DATA.insurance.reduce((a, b) => a + b.amount, 0))} trend={7.0} color="#8b5cf6" icon="💰" sparkData={DATA.insurance.map((d) => d.amount)} />
              <KPICard title="Avg TAT" value={`${Math.round(DATA.insurance.reduce((a, b) => a + b.avgDays, 0) / DATA.insurance.length)} days`} trend={-5.0} color="#ec4899" icon="📅" sparkData={DATA.insurance.map((d) => d.avgDays)} />
            </div>
            <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
              <SectionHeader title="Insurance & TPA Performance" icon="🏦" subtitle="Claims status and turnaround by insurer" />
              <Table
                cols={[
                  { key: "insurer", label: "Insurer / TPA" },
                  { key: "claims", label: "Claims", right: true },
                  { key: "approved", label: "Approved", right: true, render: (v) => <span style={{ color: "#10b981" }}>{v}</span> },
                  { key: "pending", label: "Pending", right: true, render: (v) => <span style={{ color: "#f59e0b" }}>{v}</span> },
                  { key: "rejected", label: "Rejected", right: true, render: (v) => <span style={{ color: "#ef4444" }}>{v}</span> },
                  { key: "amount", label: "Total Value", right: true, render: (v) => fmt(v) },
                  { key: "avgDays", label: "Avg TAT", right: true, render: (v) => <span style={{ color: v > 30 ? "#ef4444" : "#10b981" }}>{v} days</span> },
                ]}
                rows={DATA.insurance}
                maxH={380}
              />
            </div>
          </div>
        )}

        {/* ── APPOINTMENTS ── */}
        {tab === "appointments" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 14 }}>
              {["Confirmed", "Completed", "Cancelled", "No-Show"].map((s) => {
                const cnt = DATA.appointments.filter((a) => a.status === s).length;
                const colors2 = { Confirmed: "#3b82f6", Completed: "#10b981", Cancelled: "#ef4444", "No-Show": "#f59e0b" };
                return <KPICard key={s} title={s} value={fmtNum(cnt)} color={colors2[s]} icon={s === "Completed" ? "✅" : s === "Cancelled" ? "❌" : s === "No-Show" ? "👤" : "📅"} trend={0} sparkData={[8, 10, 9, 11, 8, 10, 9, 10, 11, 10, 9, 10]} />;
              })}
            </div>
            <div style={{ background: "#fff", borderRadius: 14, padding: 20, border: "1px solid #e2e8f0" }}>
              <SectionHeader title="Appointment Records" icon="📅" subtitle="Filter and view all appointments" />
              <input value={aptFilter} onChange={(e) => setAptFilter(e.target.value)}
                placeholder="Filter by department, doctor, or status…"
                style={{ marginBottom: 12, padding: "8px 12px", borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13, width: "100%", boxSizing: "border-box", color: "#334155", outline: "none" }} />
              <Table
                cols={[
                  { key: "id", label: "Appt ID" },
                  { key: "patient", label: "Patient" },
                  { key: "doctor", label: "Doctor" },
                  { key: "dept", label: "Department" },
                  { key: "date", label: "Date" },
                  { key: "time", label: "Time" },
                  { key: "type", label: "Type" },
                  { key: "status", label: "Status", render: (v) => <Badge text={v} /> },
                ]}
                rows={filteredApts}
                maxH={420}
              />
            </div>
          </div>
        )}

        {/* ── AI CONCIERGE ── */}
        {tab === "ai" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>
            <div>
              <SectionHeader title="AI Hospital Concierge" icon="🤖" subtitle="RAG-powered assistant with voice support • Ask anything about your hospital" />
              <AIConcierge />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ background: "#fff", borderRadius: 14, padding: 18, border: "1px solid #e2e8f0" }}>
                <SectionHeader title="Live Alerts" icon="🔔" subtitle="Predictive alerts requiring CEO attention" />
                <AlertsPanel />
              </div>
              <div style={{ background: "#fff", borderRadius: 14, padding: 18, border: "1px solid #e2e8f0" }}>
                <SectionHeader title="Hospital Snapshot" icon="📊" subtitle="Key metrics at a glance" />
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {[
                    { l: "Annual Revenue", v: fmt(totalRevenue), c: "#3b82f6" },
                    { l: "Net Profit", v: fmt(netProfit), c: "#10b981" },
                    { l: "Total Patients", v: fmtNum(totalPatients), c: "#8b5cf6" },
                    { l: "Bed Occupancy", v: "78%", c: "#f59e0b" },
                    { l: "Total Staff", v: fmtNum(totalStaff), c: "#ec4899" },
                    { l: "Pending Claims", v: fmtNum(totalInsurancePending), c: "#ef4444" },
                  ].map(({ l, v, c }) => (
                    <div key={l} style={{ background: "#f8fafc", borderRadius: 10, padding: "10px 12px", borderLeft: `3px solid ${c}` }}>
                      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.04em" }}>{l}</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginTop: 2 }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
        input:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
      `}</style>
    </div>
  );
}
