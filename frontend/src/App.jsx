import { useState, useEffect, useRef, useCallback } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell,
  AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis, ReferenceLine,
} from "recharts";
import "./index.css";
import {
  DATA, HOSPITAL, DEPARTMENTS, MONTHS,
  totalRevenue, totalOpex, netProfit, totalPatients, totalStaff,
  totalInsuranceClaims, totalInsurancePending, fmt, fmtNum,
} from "./data/syntheticData";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import ForceGraph2D from "react-force-graph-2d";

// ─── API CONFIG ────────────────────────────────────────────────────────────────
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const USE_BACKEND = import.meta.env.VITE_USE_BACKEND === "true";

// ─── ALERTS ENGINE ────────────────────────────────────────────────────────────
const ALERTS = [
  { type: "danger", icon: "🚨", text: "ICU occupancy at 94% — 3 beds remaining. Initiate discharge planning.", rule: "Bed occupancy > 90% critical threshold", actual: 94, threshold: 90 },
  { type: "warn",   icon: "⚠️", text: `${fmtNum(totalInsurancePending)} insurance claims pending. Follow up with Medi Assist TPA.`, rule: "Pending claims exceeding 30-day threshold", actual: totalInsurancePending, threshold: 100 },
  { type: "warn",   icon: "⚠️", text: "OT cancellation rate in Orthopaedics is 18% — above 10% threshold.", rule: "OT cancellation rate > 10% warning threshold", actual: 18, threshold: 10 },
  { type: "info",   icon: "💡", text: "Cardiology revenue up 22% YoY. Consider expanding capacity by 10 beds.", rule: "Top revenue growth department insight (informational)", actual: 22 },
  { type: "info",   icon: "💡", text: "Pharmacy margin 31% — highest across all units. Scale procurement efficiency.", rule: "Top margin department insight (informational)", actual: 31 },
  { type: "success",icon: "✅", text: "Patient satisfaction score: 4.6/5. Top performer: Paediatrics (4.8/5).", rule: "Monthly patient satisfaction report", actual: 4.6 },
];

// ─── MINI COMPONENTS ──────────────────────────────────────────────────────────
function Badge({ text }) {
  const map = {
    Confirmed: "badge-info", Completed: "badge-success",
    Cancelled: "badge-danger", "No-Show": "badge-warning",
    Approved: "badge-success", Pending: "badge-warning", Rejected: "badge-danger",
    compliant: "badge-success", partial: "badge-warning", "non-compliant": "badge-danger",
    "Govt Scheme": "badge-info"
  };
  return (
    <span style={{ padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600, display: "inline-block" }}
      className={`${map[text] || "badge-neutral"}`}>
      {text}
    </span>
  );
}

function SectionHeader({ title, subtitle, icon }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 20 }}>{icon}</span>
        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: "var(--gray-900)" }}>{title}</h2>
      </div>
      {subtitle && <p style={{ margin: "4px 0 0 28px", fontSize: 12, color: "var(--gray-400)" }}>{subtitle}</p>}
    </div>
  );
}

function Spinner() {
  return <div style={{ width: 16, height: 16, border: "2px solid #e2e8f0", borderTopColor: "var(--primary-500)", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />;
}

// ─── KPI CARD ──────────────────────────────────────────────────────────────────
function KPICard({ title, value, sub, trend, sparkData, color, icon }) {
  const up = trend >= 0;
  return (
    <div className="card fade-in" style={{ display: "flex", flexDirection: "column", gap: 10, transition: "transform 0.2s, box-shadow 0.2s" }}
      onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "var(--shadow-md)"; }}
      onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = ""; }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 11, color: "var(--gray-400)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>{title}</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: "var(--gray-900)", marginTop: 4, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>{value}</div>
          {sub && <div style={{ fontSize: 11, color: "var(--gray-400)", marginTop: 3 }}>{sub}</div>}
        </div>
        <div style={{ width: 42, height: 42, borderRadius: 12, background: color + "1a", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, flexShrink: 0 }}>{icon}</div>
      </div>
      {sparkData && <SparkLine data={sparkData} color={color} />}
      {trend !== undefined && (
        <div style={{ fontSize: 11, color: up ? "var(--success)" : "var(--danger)", fontWeight: 600, display: "flex", alignItems: "center", gap: 3 }}>
          {up ? "▲" : "▼"} {Math.abs(trend)}% vs last month
        </div>
      )}
    </div>
  );
}

function SparkLine({ data, color }) {
  return (
    <ResponsiveContainer width="100%" height={36}>
      <AreaChart data={data.map((v, i) => ({ v, i }))} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={`sg-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={2} fill={`url(#sg-${color})`} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ─── ALERTS PANEL ─────────────────────────────────────────────────────────────
function AlertsPanel({ showExplain = false }) {
  const [expanded, setExpanded] = useState(null);
  const colors = { danger: "#fee2e2", warn: "#fef3c7", info: "#dbeafe", success: "#d1fae5" };
  const borders = { danger: "#fca5a5", warn: "#fcd34d", info: "#93c5fd", success: "#6ee7b7" };
  const texts  = { danger: "#991b1b", warn: "#92400e", info: "#1e40af", success: "#065f46" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {ALERTS.map((a, i) => (
        <div key={i} style={{ background: colors[a.type], border: `1px solid ${borders[a.type]}`, borderRadius: 10, padding: "10px 14px" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <span style={{ fontSize: 15, flexShrink: 0 }}>{a.icon}</span>
            <div style={{ flex: 1 }}>
              <p style={{ margin: 0, fontSize: 12.5, color: texts[a.type], lineHeight: 1.5 }}>{a.text}</p>
              {showExplain && (
                <button onClick={() => setExpanded(expanded === i ? null : i)}
                  style={{ marginTop: 4, fontSize: 11, color: texts[a.type], background: "none", border: "none", padding: 0, textDecoration: "underline", cursor: "pointer" }}>
                  {expanded === i ? "Hide" : "Why this alert?"} ℹ️
                </button>
              )}
              {expanded === i && (
                <div style={{ marginTop: 6, padding: "6px 10px", background: "rgba(255,255,255,0.6)", borderRadius: 6, fontSize: 11, color: texts[a.type] }}>
                  <strong>Rule:</strong> {a.rule}<br />
                  {a.threshold && <><strong>Threshold:</strong> {a.threshold} | <strong>Actual:</strong> {a.actual}</>}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── TABLE ────────────────────────────────────────────────────────────────────
function DataTable({ cols, rows, maxH = 320 }) {
  return (
    <div style={{ overflowY: "auto", maxHeight: maxH, borderRadius: 10, border: "1px solid var(--gray-200)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
        <thead>
          <tr style={{ background: "var(--gray-50)", position: "sticky", top: 0, zIndex: 1 }}>
            {cols.map(c => (
              <th key={c.key} style={{ padding: "10px 12px", textAlign: c.right ? "right" : "left", fontWeight: 600, color: "var(--gray-500)", borderBottom: "1px solid var(--gray-200)", whiteSpace: "nowrap", fontSize: 11, letterSpacing: "0.04em", textTransform: "uppercase" }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? "#fff" : "var(--gray-50)", transition: "background 0.12s" }}
              onMouseEnter={e => e.currentTarget.style.background = "var(--primary-50)"}
              onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? "#fff" : "var(--gray-50)"}>
              {cols.map(c => (
                <td key={c.key} style={{ padding: "9px 12px", borderBottom: "1px solid var(--gray-100)", textAlign: c.right ? "right" : "left", whiteSpace: "nowrap", color: "var(--gray-700)" }}>
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

// ─── BED OCCUPANCY GRID ───────────────────────────────────────────────────────
function BedOccupancyGrid() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: 10 }}>
      {DATA.bedOccupancy.map(b => {
        const pct = Math.round((b.occupied / b.totalBeds) * 100);
        const status = pct > 90 ? "var(--danger)" : pct > 75 ? "var(--warning)" : "var(--success)";
        return (
          <div key={b.dept} className="fade-in" style={{ background: "white", border: "1px solid var(--gray-200)", borderRadius: 10, padding: "12px 14px", borderLeft: `4px solid ${status}`, transition: "transform 0.15s" }}
            onMouseEnter={e => e.currentTarget.style.transform = "scale(1.02)"}
            onMouseLeave={e => e.currentTarget.style.transform = ""}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--gray-700)", marginBottom: 6 }}>{b.dept}</div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: "var(--gray-400)" }}>{b.occupied}/{b.totalBeds} beds</span>
              <span style={{ fontSize: 14, fontWeight: 700, color: status }}>{pct}%</span>
            </div>
            <div style={{ background: "var(--gray-100)", borderRadius: 4, height: 8, overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, background: status, height: "100%", borderRadius: 4, transition: "width 0.8s ease" }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── AI CONCIERGE ─────────────────────────────────────────────────────────────
const AI_CTX = {
  revenue: `Total revenue: ${fmt(totalRevenue)}. Net profit: ${fmt(netProfit)}. Margin: ${((netProfit / totalRevenue) * 100).toFixed(1)}%.`,
  patients: `Total patients: ${fmtNum(totalPatients)}. Avg monthly inpatients: ${Math.round(DATA.patients.reduce((a, b) => a + b.inpatient, 0) / 12)}.`,
  staff: `Total staff: ${fmtNum(totalStaff)}.`,
  beds: `Bed occupancy: 78% avg. Highest: ICU at 94%.`,
  insurance: `Claims: ${fmtNum(totalInsuranceClaims)}. Pending: ${fmtNum(totalInsurancePending)}.`,
  ot: `OT utilization avg: ${Math.round(DATA.ot.reduce((a, b) => a + b.utilization, 0) / DATA.ot.length)}%.`,
};

const SYSTEM_PROMPT = `You are the AI Concierge for ${HOSPITAL.name}, Chennai. 
Hospital data: ${JSON.stringify(AI_CTX)}
Answer in 2-3 sentences using Indian number formatting. Give actionable CEO-level insights. 
Never reveal individual patient PHI. Comply with India's DPDP Act 2023.`;

const QUICK_PROMPTS = [
  "Which department is most profitable?",
  "What is our current OT utilization?",
  "Insurance claims status?",
  "Staff headcount breakdown?",
  "What are the key risks this month?",
  "Which alerts need my immediate action?",
];

function AIConcierge() {
  const [messages, setMessages] = useState([
    { role: "ai", text: `Namaste! 🙏 I am your AI Concierge for ${HOSPITAL.name}. Ask me about revenue, patients, staff, OT, insurance, or any department. I'm connected to live hospital data and comply with India's DPDP Act 2023.`, sources: [] },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const chatRef = useRef(null);
  const recogRef = useRef(null);

  const sendMsg = useCallback(async (q) => {
    if (!q.trim()) return;
    setMessages(m => [...m, { role: "user", text: q }]);
    setInput("");
    setLoading(true);

    try {
      // All AI calls go through the backend proxy (/api/ai/chat)
      // Backend uses OpenRouter (free LLMs) → RAG → intent-match fallback
      if (USE_BACKEND) {
        const token = localStorage.getItem("access_token");
        const res = await fetch(`${API_BASE}/api/ai/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...(token ? { "Authorization": `Bearer ${token}` } : {}) },
          body: JSON.stringify({ question: q }),
        });
        if (res.ok) {
          const data = await res.json();
          const sourceLabel = data.source === "claude_api" ? "OpenRouter" : data.source === "rag_local" ? "Local RAG" : "Local";
          setMessages(m => [...m, { role: "ai", text: data.answer, sources: data.sources_cited || [], source_type: sourceLabel }]);
          setLoading(false);
          return;
        }
      }
    } catch (e) { console.warn("Backend AI call failed:", e); }

    // Fallback: local intent matching
    setMessages(m => [...m, { role: "ai", text: _intentMatch(q), sources: [], source_type: "local" }]);
    setLoading(false);
  }, []);

  function _intentMatch(q) {
    const lq = q.toLowerCase();
    if (lq.includes("profit") || lq.includes("revenue") || lq.includes("financial")) return `${AI_CTX.revenue} Most profitable dept: ${DATA.deptFinancials.reduce((a,b) => b.profit > a.profit ? b : a).dept} (${DATA.deptFinancials.reduce((a,b) => b.profit > a.profit ? b : a).margin}% margin).`;
    if (lq.includes("patient") || lq.includes("admission")) return AI_CTX.patients;
    if (lq.includes("staff") || lq.includes("hr") || lq.includes("nurse")) return AI_CTX.staff;
    if (lq.includes("bed") || lq.includes("occupancy")) return AI_CTX.beds;
    if (lq.includes("insurance") || lq.includes("claim") || lq.includes("tpa")) return AI_CTX.insurance;
    if (lq.includes("ot") || lq.includes("surgery") || lq.includes("operation")) return AI_CTX.ot;
    if (lq.includes("alert") || lq.includes("risk")) return "Key alerts: ICU at 94% occupancy (critical), OT cancellations in Orthopaedics 18% (above threshold), 23 insurance claims pending >30 days.";
    if (lq.includes("hello") || lq.includes("hi")) return `Namaste! I'm your AI Concierge. I can help with revenue (${fmt(totalRevenue)}), patients (${fmtNum(totalPatients)}), staff, beds, insurance, OT. What would you like to know?`;
    return "I have data on revenue, patients, staff, beds, insurance claims, OT utilization, and department P&L. Could you be more specific about what you'd like to know?";
  }

  const startVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert("Voice recognition not supported in this browser. Please use Chrome."); return; }
    if (listening) { recogRef.current?.stop(); setListening(false); return; }
    const r = new SR();
    r.lang = "en-IN";
    r.onresult = e => { sendMsg(e.results[0][0].transcript); setListening(false); };
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
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ background: "linear-gradient(135deg, #1e3a8a, #2563eb)", padding: "14px 18px", display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ width: 38, height: 38, borderRadius: "50%", background: "rgba(255,255,255,0.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>🤖</div>
        <div>
          <div style={{ color: "#fff", fontWeight: 700, fontSize: 14 }}>AI Hospital Concierge</div>
          <div style={{ color: "#bfdbfe", fontSize: 11 }}>OpenRouter LLM · RAG-powered · DPDP Act 2023 compliant · Voice-enabled</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#4ade80", animation: "pulse 2s infinite" }} />
          <span style={{ color: "#bfdbfe", fontSize: 11 }}>Online</span>
        </div>
      </div>
      <div ref={chatRef} style={{ height: 300, overflowY: "auto", padding: 14, display: "flex", flexDirection: "column", gap: 10, background: "var(--gray-50)" }}>
        {messages.map((m, i) => (
          <div key={i} className="fade-in" style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{ maxWidth: "84%", padding: "10px 14px", borderRadius: m.role === "user" ? "14px 14px 2px 14px" : "14px 14px 14px 2px", background: m.role === "user" ? "var(--primary-700)" : "white", color: m.role === "user" ? "white" : "var(--gray-700)", fontSize: 13, lineHeight: 1.55, boxShadow: "var(--shadow-sm)", border: m.role === "ai" ? "1px solid var(--gray-200)" : "none" }}>
              {m.text}
              {m.sources && m.sources.length > 0 && (
                <div style={{ marginTop: 6, fontSize: 10, color: "var(--gray-400)", borderTop: "1px solid var(--gray-100)", paddingTop: 4 }}>
                  📚 Sources: {m.sources.join(", ")}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", gap: 5, padding: "10px 14px", background: "white", borderRadius: "14px 14px 14px 2px", width: "fit-content", border: "1px solid var(--gray-200)" }}>
            {[0,1,2].map(i => <div key={i} style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--gray-300)", animation: `pulse 1.2s ${i*0.2}s infinite` }} />)}
          </div>
        )}
      </div>
      <div style={{ padding: "8px 12px", display: "flex", gap: 6, flexWrap: "wrap", borderTop: "1px solid var(--gray-100)", background: "white" }}>
        {QUICK_PROMPTS.map(q => (
          <button key={q} onClick={() => sendMsg(q)} style={{ padding: "4px 10px", borderRadius: 20, border: "1px solid var(--gray-200)", background: "var(--gray-50)", fontSize: 11, color: "var(--gray-600)", transition: "all 0.15s" }}
            onMouseEnter={e => { e.currentTarget.style.background = "var(--primary-50)"; e.currentTarget.style.borderColor = "var(--primary-500)"; e.currentTarget.style.color = "var(--primary-700)"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "var(--gray-50)"; e.currentTarget.style.borderColor = "var(--gray-200)"; e.currentTarget.style.color = "var(--gray-600)"; }}>
            {q}
          </button>
        ))}
      </div>
      <div style={{ padding: 12, borderTop: "1px solid var(--gray-200)", display: "flex", gap: 8, background: "white" }}>
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && sendMsg(input)} placeholder="Ask about revenue, patients, OT, staff, insurance…" style={{ flex: 1 }} />
        <button onClick={startVoice} style={{ padding: "8px 12px", borderRadius: "var(--radius-md)", border: `1px solid ${listening ? "var(--danger)" : "var(--gray-200)"}`, background: listening ? "#fee2e2" : "var(--gray-50)", fontSize: 16, transition: "all 0.2s" }}>🎤</button>
        <button onClick={() => sendMsg(input)} disabled={!input.trim() || loading} style={{ padding: "8px 16px", borderRadius: "var(--radius-md)", border: "none", background: "var(--primary-700)", color: "white", fontWeight: 600, fontSize: 13, opacity: (!input.trim() || loading) ? 0.6 : 1 }}>
          {loading ? <Spinner /> : "Send"}
        </button>
      </div>
    </div>
  );
}

// ─── NABH COMPLIANCE TAB ──────────────────────────────────────────────────────
function NABHComplianceTab() {
  const domains = [...new Set(DATA.nabh.map(c => c.domain))];
  const total = DATA.nabh.length;
  const compliant = DATA.nabh.filter(c => c.status === "compliant").length;
  const partial = DATA.nabh.filter(c => c.status === "partial").length;
  const nonCompliant = DATA.nabh.filter(c => c.status === "non-compliant").length;
  const score = Math.round(compliant / total * 100);
  const [selectedDomain, setSelectedDomain] = useState("All");

  const filtered = selectedDomain === "All" ? DATA.nabh : DATA.nabh.filter(c => c.domain === selectedDomain);

  const statusColor = score >= 85 ? "var(--success)" : score >= 60 ? "var(--warning)" : "var(--danger)";
  const nabh_status = score >= 85 ? "NABH Ready ✅" : score >= 60 ? "In Progress ⚠️" : "Needs Attention 🚨";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Score overview */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 14 }}>
        <KPICard title="Compliance Score" value={`${score}%`} sub={nabh_status} color={statusColor} icon="🏆" sparkData={[60,65,68,70,72,74,76,78,79,80,score,score]} trend={2} />
        <KPICard title="Compliant" value={compliant} sub={`of ${total} checkpoints`} color="var(--success)" icon="✅" sparkData={[10,11,12,13,13,12,13,14,14,15,15,compliant]} trend={3} />
        <KPICard title="Partial" value={partial} sub="Needs improvement" color="var(--warning)" icon="⚠️" sparkData={[5,5,5,5,5,5,5,5,5,5,5,partial]} trend={0} />
        <KPICard title="Non-Compliant" value={nonCompliant} sub="Action required" color="var(--danger)" icon="🚨" sparkData={[5,4,4,3,3,3,3,3,2,2,2,nonCompliant]} trend={-1} />
      </div>

      {/* Domain filter */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {["All", ...domains].map(d => (
          <button key={d} onClick={() => setSelectedDomain(d)}
            style={{ padding: "6px 14px", borderRadius: 20, border: "1px solid", fontSize: 12, fontWeight: 500, borderColor: selectedDomain === d ? "var(--primary-500)" : "var(--gray-200)", background: selectedDomain === d ? "var(--primary-50)" : "white", color: selectedDomain === d ? "var(--primary-700)" : "var(--gray-500)" }}>
            {d}
          </button>
        ))}
      </div>

      {/* Checklist */}
      <div className="card">
        <SectionHeader title="NABH Compliance Checklist" subtitle="NABH 5th Edition standards tracking" icon="📋" />
        <DataTable
          cols={[
            { key: "domain", label: "Domain" },
            { key: "code", label: "Code" },
            { key: "desc", label: "Checkpoint Description" },
            { key: "status", label: "Status", right: true, render: v => <Badge text={v} /> },
          ]}
          rows={filtered}
          maxH={420}
        />
      </div>

      {/* Progress bars by domain */}
      <div className="card">
        <SectionHeader title="Compliance by Domain" subtitle="Percentage of checkpoints met per domain" icon="📊" />
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {domains.map(domain => {
            const checks = DATA.nabh.filter(c => c.domain === domain);
            const pct = Math.round(checks.filter(c => c.status === "compliant").length / checks.length * 100);
            const color = pct >= 80 ? "var(--success)" : pct >= 50 ? "var(--warning)" : "var(--danger)";
            return (
              <div key={domain}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
                  <span style={{ color: "var(--gray-700)", fontWeight: 500 }}>{domain}</span>
                  <span style={{ color, fontWeight: 700 }}>{pct}%</span>
                </div>
                <div style={{ background: "var(--gray-100)", borderRadius: 6, height: 10, overflow: "hidden" }}>
                  <div style={{ width: `${pct}%`, background: color, height: "100%", borderRadius: 6, transition: "width 1s ease" }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── MAIN TABS ─────────────────────────────────────────────────────────────────
const TABS = [
  { id: "overview",     label: "📊 Overview" },
  { id: "finance",      label: "💰 Finance & P&L" },
  { id: "patients",     label: "🏥 Patients" },
  { id: "departments",  label: "🔬 Departments" },
  { id: "hr",           label: "👥 HR & Payroll" },
  { id: "ot",           label: "🔪 OT & Surgeries" },
  { id: "insurance",    label: "📋 Insurance" },
  { id: "appointments", label: "📅 Appointments" },
  { id: "nabh",         label: "✅ NABH Compliance" },
  { id: "ai",           label: "🤖 AI Concierge" },
];

// ─── MAIN APP ──────────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState("overview");
  const [deptFilter, setDeptFilter] = useState("");
  const [aptFilter, setAptFilter] = useState("");
  const [wsConnected, setWsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [dateRange, setDateRange] = useState([new Date("2024-04-01"), new Date("2025-03-31")]);
  const [startDate, endDate] = dateRange;
  const [token, setToken] = useState(localStorage.getItem("access_token") || null);
  const [loginForm, setLoginForm] = useState({ username: "", password: "", error: "", loading: false });
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const wsRef = useRef(null);

  // WebSocket live KPI updates
  useEffect(() => {
    if (!USE_BACKEND) return;
    try {
      const ws = new WebSocket(`${API_BASE.replace("http", "ws")}/ws/live-kpis`);
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => setWsConnected(false);
      ws.onerror = () => setWsConnected(false);
      ws.onmessage = e => {
        const data = JSON.parse(e.data);
        if (data.type === "kpi_update") setLastUpdate(new Date().toLocaleTimeString());
      };
      wsRef.current = ws;

      if (USE_BACKEND) {
        // Fetch Graph Data
        fetch(`${API_BASE}/api/graph/patients?limit=50`, {
          headers: { "Authorization": `Bearer ${token}` }
        })
          .then(res => res.json())
          .then(data => {
            if (data && data.nodes && data.nodes.length > 0) {
              setGraphData({ nodes: data.nodes, links: data.edges });
            } else {
              // Fallback synthetic graph if Neo4j is empty/offline
              const nodes = [{ id: "DEPT_1", label: "Cardiology", group: 1 }];
              const links = [];
              for (let i = 1; i <= 10; i++) {
                nodes.push({ id: `D${i}`, label: `Dr. ${i}`, group: 2 });
                links.push({ source: `D${i}`, target: "DEPT_1" });
                for (let j = 1; j <= 3; j++) {
                  nodes.push({ id: `P${i}_${j}`, label: `Patient`, group: 3 });
                  links.push({ source: `P${i}_${j}`, target: `D${i}` });
                }
              }
              setGraphData({ nodes, links });
            }
          })
          .catch(err => console.error("Neo4j fetch error:", err));
      } else {
        // Fallback synthetic graph
        const nodes = [{ id: "DEPT_1", label: "Cardiology", group: 1 }];
        const links = [];
        for (let i = 1; i <= 10; i++) {
          nodes.push({ id: `D${i}`, label: `Dr. ${i}`, group: 2 });
          links.push({ source: `D${i}`, target: "DEPT_1" });
          for (let j = 1; j <= 3; j++) {
            nodes.push({ id: `P${i}_${j}`, label: `Patient`, group: 3 });
            links.push({ source: `P${i}_${j}`, target: `D${i}` });
          }
        }
        setGraphData({ nodes, links });
      }

      return () => ws.close();
    } catch {}
  }, []);

  const filteredApts = DATA.appointments.filter(a =>
    a.dept.toLowerCase().includes(aptFilter.toLowerCase()) ||
    a.doctor.toLowerCase().includes(aptFilter.toLowerCase()) ||
    a.status.toLowerCase().includes(aptFilter.toLowerCase())
  );

  const TOOLTIP_STYLE = { background: "white", border: "1px solid var(--gray-200)", borderRadius: 8, fontSize: 12, boxShadow: "var(--shadow-md)", padding: "8px 12px" };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginForm(prev => ({ ...prev, error: "", loading: true }));
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: loginForm.username, password: loginForm.password }),
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem("access_token", data.access_token);
        setToken(data.access_token);
      } else {
        setLoginForm(prev => ({ ...prev, error: data.detail || "Login failed" }));
      }
    } catch (err) {
      setLoginForm(prev => ({ ...prev, error: "Network error. Is the backend running?" }));
    } finally {
      setLoginForm(prev => ({ ...prev, loading: false }));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
  };

  const handleExport = (type) => {
    if (!USE_BACKEND) {
      alert("Backend required for exports.");
      return;
    }
    const currentToken = localStorage.getItem("access_token");
    fetch(`${API_BASE}/api/export/${type}/overview`, {
      headers: { "Authorization": `Bearer ${currentToken}` }
    })
    .then(res => res.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `overview.${type === "excel" ? "xlsx" : type}`;
      a.click();
    })
    .catch(err => console.error("Export failed:", err));
  };

  if (USE_BACKEND && !token) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", background: "var(--gray-100)" }}>
        <form onSubmit={handleLogin} className="card fade-in" style={{ width: 360, padding: 32, display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ textAlign: "center", marginBottom: 10 }}>
            <div style={{ fontSize: 40, marginBottom: 10 }}>🏥</div>
            <h1 style={{ margin: 0, fontSize: 20, color: "var(--gray-900)" }}>{HOSPITAL.name}</h1>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--gray-500)" }}>CEO Dashboard Login</p>
          </div>
          {loginForm.error && <div style={{ padding: 10, background: "#fee2e2", color: "#991b1b", fontSize: 12, borderRadius: 6, border: "1px solid #fca5a5" }}>{loginForm.error}</div>}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--gray-700)" }}>Username</label>
            <input type="text" value={loginForm.username} onChange={e => setLoginForm(prev => ({ ...prev, username: e.target.value }))} placeholder="ceo" style={{ padding: "10px 12px", border: "1px solid var(--gray-300)", borderRadius: 6, fontSize: 14 }} required />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--gray-700)" }}>Password</label>
            <input type="password" value={loginForm.password} onChange={e => setLoginForm(prev => ({ ...prev, password: e.target.value }))} placeholder="••••••••" style={{ padding: "10px 12px", border: "1px solid var(--gray-300)", borderRadius: 6, fontSize: 14 }} required />
          </div>
          <button type="submit" disabled={loginForm.loading} style={{ background: "var(--primary-600)", color: "white", border: "none", padding: "12px", borderRadius: 6, fontSize: 14, fontWeight: 600, marginTop: 10, cursor: loginForm.loading ? "not-allowed" : "pointer" }}>
            {loginForm.loading ? "Authenticating..." : "Login"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: "var(--font-family)", background: "var(--gray-100)", minHeight: "100vh" }}>
      {/* TOP NAV */}
      <div style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1d4ed8 100%)", boxShadow: "0 2px 20px rgba(15,23,42,0.4)", position: "sticky", top: 0, zIndex: 100 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 24px 0" }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: "rgba(255,255,255,0.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, backdropFilter: "blur(8px)" }}>🏥</div>
          <div>
            <div style={{ color: "#fff", fontWeight: 800, fontSize: 16, letterSpacing: "-0.01em" }}>{HOSPITAL.name}</div>
            <div style={{ color: "#93c5fd", fontSize: 11 }}>{HOSPITAL.location} · Est. {HOSPITAL.established} · {HOSPITAL.beds} Beds · CEO Dashboard</div>
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
            {USE_BACKEND && (
              <div style={{ display: "flex", alignItems: "center", gap: 5, background: "rgba(255,255,255,0.1)", borderRadius: 8, padding: "4px 10px" }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: wsConnected ? "#4ade80" : "#f87171" }} />
                <span style={{ color: "#bfdbfe", fontSize: 11 }}>{wsConnected ? "Live" : "Offline"}</span>
              </div>
            )}
            <div style={{ background: "rgba(255,255,255,0.1)", borderRadius: 8, padding: "5px 12px", fontSize: 11, color: "#e0f2fe", display: "flex", alignItems: "center", gap: 5 }}>
              FY {HOSPITAL.fy} {lastUpdate && `· Updated ${lastUpdate}`}
              <DatePicker
                selectsRange={true}
                startDate={startDate}
                endDate={endDate}
                onChange={(update) => setDateRange(update)}
                dateFormat="MMM d, yyyy"
                className="date-picker-custom"
                placeholderText="Select date range"
              />
            </div>
            {USE_BACKEND && (
              <div style={{ display: "flex", gap: 5 }}>
                <button onClick={() => handleExport("pdf")} style={{ background: "rgba(255,255,255,0.15)", border: "none", borderRadius: 8, padding: "6px 12px", color: "white", fontSize: 11, cursor: "pointer" }}>PDF</button>
                <button onClick={() => handleExport("excel")} style={{ background: "rgba(255,255,255,0.15)", border: "none", borderRadius: 8, padding: "6px 12px", color: "white", fontSize: 11, cursor: "pointer" }}>Excel</button>
                <button onClick={handleLogout} style={{ background: "rgba(255,255,255,0.15)", border: "none", borderRadius: 8, padding: "6px 12px", color: "white", fontSize: 11, cursor: "pointer" }}>Logout</button>
              </div>
            )}
            <div style={{ width: 36, height: 36, borderRadius: "50%", background: "rgba(255,255,255,0.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15 }}>👤</div>
          </div>
        </div>
        {/* TABS */}
        <div style={{ display: "flex", gap: 1, overflowX: "auto", padding: "0 12px", scrollbarWidth: "none" }} className="no-print">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{ padding: "10px 14px", border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600, background: tab === t.id ? "rgba(255,255,255,0.15)" : "transparent", color: tab === t.id ? "#fff" : "#93c5fd", borderRadius: "8px 8px 0 0", borderBottom: tab === t.id ? "2px solid #60a5fa" : "2px solid transparent", transition: "all 0.15s", whiteSpace: "nowrap" }}
              onMouseEnter={e => { if (tab !== t.id) e.currentTarget.style.color = "#fff"; }}
              onMouseLeave={e => { if (tab !== t.id) e.currentTarget.style.color = "#93c5fd"; }}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* CONTENT */}
      <div style={{ padding: 24, maxWidth: 1440, margin: "0 auto" }} className="fade-in">

        {/* ── OVERVIEW ── */}
        {tab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
              <KPICard title="Annual Revenue" value={fmt(totalRevenue)} sub={`FY ${HOSPITAL.fy}`} trend={8.4} sparkData={DATA.revenue.map(d => d.revenue)} color="#3b82f6" icon="💰" />
              <KPICard title="Net Profit" value={fmt(netProfit)} sub={`${((netProfit/totalRevenue)*100).toFixed(1)}% margin`} trend={5.2} sparkData={DATA.revenue.map(d => d.revenue - d.opex)} color="#10b981" icon="📈" />
              <KPICard title="Total Patients" value={fmtNum(totalPatients)} sub="Inpatient + Outpatient" trend={3.1} sparkData={DATA.patients.map(d => d.inpatient + d.outpatient)} color="#8b5cf6" icon="🏥" />
              <KPICard title="Bed Occupancy" value="78%" sub={`${Math.round(0.78*HOSPITAL.beds)}/${HOSPITAL.beds} beds occupied`} trend={2.0} sparkData={[72,74,77,76,78,80,78,79,77,76,79,78]} color="#f59e0b" icon="🛏️" />
              <KPICard title="Total Staff" value={fmtNum(totalStaff)} sub="Across all departments" trend={1.5} sparkData={[700,710,718,720,722,725,720,718,722,725,728,720]} color="#ec4899" icon="👥" />
              <KPICard title="Insurance Claims" value={fmtNum(totalInsuranceClaims)} sub={`${fmtNum(totalInsurancePending)} pending`} trend={-2.1} sparkData={DATA.insurance.map(d => d.claims)} color="#ef4444" icon="📋" />
            </div>
            <div className="grid-2">
              <div className="card">
                <SectionHeader title="Revenue vs Expenditure" subtitle="Monthly trend — FY 2024-25" icon="📊" />
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={DATA.revenue} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient>
                      <linearGradient id="opexGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ef4444" stopOpacity={0.2}/><stop offset="95%" stopColor="#ef4444" stopOpacity={0}/></linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: "var(--gray-400)" }} />
                    <YAxis tickFormatter={v => `₹${(v/1e6).toFixed(0)}M`} tick={{ fontSize: 10, fill: "var(--gray-400)" }} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, n) => [fmt(v), n === "revenue" ? "Revenue" : "Expenses"]} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Area type="monotone" dataKey="revenue" stroke="#3b82f6" strokeWidth={2.5} fill="url(#revGrad)" name="Revenue" />
                    <Area type="monotone" dataKey="opex" stroke="#ef4444" strokeWidth={2} fill="url(#opexGrad)" name="Expenses" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="card">
                <SectionHeader title="AI Alerts & Insights" subtitle="Priority actions for CEO — click 'Why this alert?' for explanation" icon="🔔" />
                <AlertsPanel showExplain={true} />
              </div>
            </div>
            <div className="card">
              <SectionHeader title="Department P&L at a Glance" subtitle="Revenue, cost, and profit by department" icon="🔬" />
              <DataTable
                cols={[
                  { key: "dept", label: "Department" },
                  { key: "revenue", label: "Revenue", right: true, render: v => fmt(v) },
                  { key: "cost", label: "Cost", right: true, render: v => fmt(v) },
                  { key: "profit", label: "Profit/Loss", right: true, render: v => <span style={{ color: v > 0 ? "var(--success)" : "var(--danger)", fontWeight: 700 }}>{fmt(v)}</span> },
                  { key: "margin", label: "Margin %", right: true, render: v => <span style={{ color: v > 20 ? "var(--success)" : v > 0 ? "var(--warning)" : "var(--danger)", fontWeight: 600 }}>{v}%</span> },
                ]}
                rows={DATA.deptFinancials}
              />
            </div>
          </div>
        )}

        {/* ── FINANCE ── */}
        {tab === "finance" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <div className="grid-kpi">
              <KPICard title="Gross Revenue" value={fmt(totalRevenue)} trend={8.4} color="#3b82f6" icon="💰" sparkData={DATA.revenue.map(d => d.revenue)} />
              <KPICard title="Operating Costs" value={fmt(totalOpex)} trend={4.1} color="#ef4444" icon="📤" sparkData={DATA.revenue.map(d => d.opex)} />
              <KPICard title="Net Profit" value={fmt(netProfit)} sub={`Margin: ${((netProfit/totalRevenue)*100).toFixed(1)}%`} trend={5.2} color="#10b981" icon="📈" sparkData={DATA.revenue.map(d => d.revenue - d.opex)} />
              <KPICard title="Insurance Revenue" value={fmt(DATA.revenue.reduce((a,b)=>a+b.insurance,0))} trend={6.5} color="#8b5cf6" icon="🏦" sparkData={DATA.revenue.map(d => d.insurance)} />
              <KPICard title="OOP Revenue" value={fmt(DATA.revenue.reduce((a,b)=>a+b.outOfPocket,0))} trend={3.0} color="#f59e0b" icon="💳" sparkData={DATA.revenue.map(d => d.outOfPocket)} />
            </div>
            <div className="card">
              <SectionHeader title="Monthly Revenue Breakdown" subtitle="Insurance vs Out-of-Pocket vs Total Revenue" icon="📊" />
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={DATA.revenue} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: "var(--gray-400)" }} />
                  <YAxis tickFormatter={v => `₹${(v/1e6).toFixed(0)}M`} tick={{ fontSize: 10, fill: "var(--gray-400)" }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, n) => [fmt(v), n]} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="revenue" fill="#3b82f6" name="Total Revenue" radius={[3,3,0,0]} />
                  <Bar dataKey="insurance" fill="#8b5cf6" name="Insurance" radius={[3,3,0,0]} />
                  <Bar dataKey="outOfPocket" fill="#f59e0b" name="Out of Pocket" radius={[3,3,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="card">
              <SectionHeader title="Department-wise P&L" subtitle="Profit, cost, and margin by unit" icon="🏦" />
              <DataTable
                cols={[
                  { key: "dept", label: "Department" },
                  { key: "revenue", label: "Revenue", right: true, render: v => fmt(v) },
                  { key: "cost", label: "Cost", right: true, render: v => fmt(v) },
                  { key: "profit", label: "Profit/Loss", right: true, render: v => <span style={{ color: v > 0 ? "var(--success)" : "var(--danger)", fontWeight: 700 }}>{fmt(v)}</span> },
                  { key: "margin", label: "Net Margin %", right: true, render: v => <span style={{ color: v > 20 ? "var(--success)" : v > 0 ? "var(--warning)" : "var(--danger)" }}>{v}%</span> },
                ]}
                rows={DATA.deptFinancials} maxH={400}
              />
            </div>
          </div>
        )}

        {/* ── PATIENTS ── */}
        {tab === "patients" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <div className="grid-kpi">
              <KPICard title="Total Inpatients" value={fmtNum(DATA.patients.reduce((a,b)=>a+b.inpatient,0))} trend={3.5} color="#3b82f6" icon="🛏️" sparkData={DATA.patients.map(d=>d.inpatient)} />
              <KPICard title="Total Outpatients" value={fmtNum(DATA.patients.reduce((a,b)=>a+b.outpatient,0))} trend={4.2} color="#10b981" icon="🚶" sparkData={DATA.patients.map(d=>d.outpatient)} />
              <KPICard title="Emergency Cases" value={fmtNum(DATA.patients.reduce((a,b)=>a+b.emergency,0))} trend={-1.2} color="#ef4444" icon="🚑" sparkData={DATA.patients.map(d=>d.emergency)} />
              <KPICard title="Surgeries Done" value={fmtNum(DATA.patients.reduce((a,b)=>a+b.surgeries,0))} trend={6.1} color="#8b5cf6" icon="🔪" sparkData={DATA.patients.map(d=>d.surgeries)} />
              <KPICard title="Avg LOS" value="4.2 days" sub="Avg length of stay (target: <5)" trend={-0.8} color="#f59e0b" icon="📅" sparkData={[4.5,4.3,4.1,4.4,4.2,4.0,4.3,4.2,4.1,4.3,4.2,4.0]} />
            </div>
            <div className="card">
              <SectionHeader title="Patient Volume Trend" subtitle="Monthly inpatient, outpatient, emergency, and surgeries" icon="📈" />
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={DATA.patients} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: "var(--gray-400)" }} />
                  <YAxis tick={{ fontSize: 10, fill: "var(--gray-400)" }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, n) => [fmtNum(v), n]} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="inpatient" stroke="#3b82f6" strokeWidth={2.5} dot={false} name="Inpatient" />
                  <Line type="monotone" dataKey="outpatient" stroke="#10b981" strokeWidth={2.5} dot={false} name="Outpatient" />
                  <Line type="monotone" dataKey="emergency" stroke="#ef4444" strokeWidth={2} dot={false} name="Emergency" />
                  <Line type="monotone" dataKey="surgeries" stroke="#8b5cf6" strokeWidth={2} dot={false} name="Surgeries" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="card">
              <SectionHeader title="Bed Occupancy by Department" subtitle="Green <75% · Amber 75-90% · Red >90%" icon="🛏️" />
              <BedOccupancyGrid />
            </div>
            <div className="card">
              <SectionHeader title="Patient Readmission Risk" subtitle="Top at-risk patients (Scikit-Learn Model)" icon="⚠️" />
              <DataTable
                cols={[
                  { key: "id", label: "Patient ID" },
                  { key: "name", label: "Patient Name" },
                  { key: "dept", label: "Department" },
                  { key: "los", label: "LOS (Days)", right: true },
                  { key: "risk", label: "Readmission Risk", right: true, render: v => {
                    const status = v >= 70 ? "High" : v >= 40 ? "Medium" : "Low";
                    const color = v >= 70 ? "badge-danger" : v >= 40 ? "badge-warning" : "badge-success";
                    return <span className={color} style={{ padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600 }}>{status} ({v}%)</span>;
                  }}
                ]}
                rows={[
                  { id: "PT101", name: "Ramesh Kumar", dept: "Cardiology", los: 12, risk: 85 },
                  { id: "PT102", name: "Sita Sharma", dept: "Orthopaedics", los: 5, risk: 45 },
                  { id: "PT103", name: "Abdul Rehman", dept: "Neurology", los: 18, risk: 72 },
                  { id: "PT104", name: "Priya Nair", dept: "Gynaecology", los: 3, risk: 20 },
                ]}
              />
            </div>
          </div>
        )}

        {/* ── DEPARTMENTS ── */}
        {tab === "departments" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader title="Department Command Centre" subtitle="Department-wise stats, financials, and performance" icon="🔬" />
            <input value={deptFilter} onChange={e => setDeptFilter(e.target.value)} placeholder="Search department…" style={{ maxWidth: 320 }} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
              {DEPARTMENTS.filter(d => d.name.toLowerCase().includes(deptFilter.toLowerCase())).map(dept => {
                const fin = DATA.deptFinancials.find(f => f.dept === dept.name);
                const occ = DATA.bedOccupancy.find(b => b.dept === dept.name);
                return (
                  <div key={dept.id} className="card fade-in" style={{ borderTop: `4px solid ${dept.color}`, transition: "transform 0.2s, box-shadow 0.2s" }}
                    onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = "var(--shadow-lg)"; }}
                    onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = ""; }}>
                    <div style={{ fontWeight: 700, fontSize: 15, color: "var(--gray-900)", marginBottom: 2 }}>{dept.name}</div>
                    <div style={{ fontSize: 12, color: "var(--gray-400)", marginBottom: 12 }}>{dept.head}</div>
                    {fin && (
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
                        <div style={{ background: "var(--gray-50)", borderRadius: 8, padding: "8px 10px" }}>
                          <div style={{ fontSize: 10, color: "var(--gray-400)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Revenue</div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--gray-900)" }}>{fmt(fin.revenue)}</div>
                        </div>
                        <div style={{ background: "var(--gray-50)", borderRadius: 8, padding: "8px 10px" }}>
                          <div style={{ fontSize: 10, color: "var(--gray-400)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Profit</div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: fin.profit > 0 ? "var(--success)" : "var(--danger)" }}>{fmt(fin.profit)}</div>
                        </div>
                      </div>
                    )}
                    {occ && (
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
                          <span style={{ color: "var(--gray-500)" }}>Bed Occupancy</span>
                          <span style={{ fontWeight: 600 }}>{Math.round((occ.occupied/occ.totalBeds)*100)}%</span>
                        </div>
                        <div style={{ background: "var(--gray-100)", borderRadius: 4, height: 8, overflow: "hidden" }}>
                          <div style={{ width: `${Math.round((occ.occupied/occ.totalBeds)*100)}%`, background: dept.color, height: "100%", borderRadius: 4, transition: "width 0.8s" }} />
                        </div>
                      </div>
                    )}
                    {!occ && <div style={{ fontSize: 12, color: "var(--gray-400)", fontStyle: "italic" }}>No inpatient beds (support dept)</div>}
                  </div>
                );
              })}
            </div>
            
            <div className="card">
              <SectionHeader title="AI Bed Demand Forecast (30 Days)" subtitle="Prophet ML Model with Confidence Intervals" icon="🔮" />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                {DATA.bedForecast.slice(0, 2).map((fc, i) => (
                  <div key={i} style={{ border: "1px solid var(--gray-200)", borderRadius: 10, padding: 14 }}>
                    <div style={{ fontWeight: 600, marginBottom: 10, color: "var(--gray-700)" }}>{fc.dept}</div>
                    <ResponsiveContainer width="100%" height={200}>
                      <AreaChart data={fc.forecast} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--gray-100)" />
                        <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
                        <YAxis domain={[40, 100]} tick={{ fontSize: 10 }} />
                        <Tooltip contentStyle={TOOLTIP_STYLE} />
                        <Area type="monotone" dataKey="upper" stroke="none" fill="var(--primary-100)" opacity={0.6} />
                        <Area type="monotone" dataKey="lower" stroke="none" fill="#fff" opacity={1} />
                        <Area type="monotone" dataKey="predicted" stroke="var(--primary-600)" strokeWidth={2} fill="none" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <SectionHeader title="Patient-Doctor Network (Neo4j)" subtitle="Visualizing treatment pathways and workload" icon="🕸️" />
              <div style={{ border: "1px solid var(--gray-200)", borderRadius: 10, height: 400, overflow: "hidden", background: "#fafafa", display: "flex", justifyContent: "center" }}>
                <ForceGraph2D
                  graphData={graphData}
                  nodeLabel="label"
                  nodeColor={node => node.group === 1 || node.type === "Department" ? "#ef4444" : node.group === 2 || node.type === "Doctor" ? "#3b82f6" : "#10b981"}
                  nodeRelSize={6}
                  linkColor={() => "rgba(148, 163, 184, 0.4)"}
                  width={800}
                  height={400}
                />
              </div>
            </div>
          </div>
        )}

        {/* ── HR ── */}
        {tab === "hr" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="grid-kpi">
              <KPICard title="Total Workforce" value={fmtNum(totalStaff)} trend={1.5} color="#3b82f6" icon="👥" sparkData={[690,700,705,710,712,718,715,718,720,722,724,720]} />
              <KPICard title="Present Today" value={fmtNum(DATA.hr.reduce((a,b)=>a+b.present,0))} sub="Attendance rate" trend={0.5} color="#10b981" icon="✅" sparkData={[640,650,655,660,658,665,662,660,665,668,665,662]} />
              <KPICard title="On Leave" value={fmtNum(DATA.hr.reduce((a,b)=>a+b.onLeave,0))} trend={-2.0} color="#f59e0b" icon="📅" sparkData={[45,42,40,38,42,39,41,40,38,37,39,41]} />
              <KPICard title="Monthly Payroll" value={fmt(DATA.hr.reduce((a,b)=>a+b.count*b.salary,0))} trend={2.1} color="#8b5cf6" icon="💸" sparkData={[4.2,4.3,4.25,4.28,4.3,4.32,4.3,4.28,4.32,4.35,4.32,4.3].map(v=>v*1e7)} />
              <KPICard title="Avg Attrition" value={`${(DATA.hr.reduce((a,b)=>a+b.attrition,0)/DATA.hr.length).toFixed(1)}%`} trend={-0.3} color="#ef4444" icon="🚪" sparkData={[5,4.8,4.6,4.8,4.5,4.6,4.4,4.3,4.5,4.4,4.2,4.3]} />
            </div>
            <div className="card">
              <SectionHeader title="Staff Roster & Payroll" subtitle="Headcount, attendance, salary, and attrition by role" icon="👥" />
              <DataTable
                cols={[
                  { key: "role", label: "Role" },
                  { key: "count", label: "Headcount", right: true, render: v => fmtNum(v) },
                  { key: "present", label: "Present", right: true },
                  { key: "onLeave", label: "On Leave", right: true },
                  { key: "salary", label: "Monthly CTC", right: true, render: v => `₹${v.toLocaleString("en-IN")}` },
                  { key: "count", label: "Total Payroll", right: true, render: (v, row) => fmt(v * row.salary) },
                  { key: "attrition", label: "Attrition %", right: true, render: v => <span style={{ color: v > 5 ? "var(--danger)" : "var(--success)" }}>{v}%</span> },
                  { key: "overtimeHrs", label: "OT Hrs/mo", right: true, render: v => <span style={{ color: v > 25 ? "var(--danger)" : "var(--gray-500)" }}>{v}h</span> },
                ]}
                rows={DATA.hr} maxH={420}
              />
            </div>
          </div>
        )}

        {/* ── OT ── */}
        {tab === "ot" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="grid-kpi">
              <KPICard title="Total Surgeries" value={fmtNum(DATA.ot.reduce((a,b)=>a+b.completed,0))} trend={5.0} color="#8b5cf6" icon="🔪" sparkData={DATA.ot.map(d=>d.completed)} />
              <KPICard title="OT Utilization" value={`${Math.round(DATA.ot.reduce((a,b)=>a+b.utilization,0)/DATA.ot.length)}%`} sub="Target: >80%" trend={2.5} color="#3b82f6" icon="⏱️" sparkData={DATA.ot.map(d=>d.utilization)} />
              <KPICard title="Cancellations" value={fmtNum(DATA.ot.reduce((a,b)=>a+b.cancelled,0))} trend={-3.0} color="#ef4444" icon="❌" sparkData={DATA.ot.map(d=>d.cancelled)} />
              <KPICard title="Avg Duration" value={`${Math.round(DATA.ot.reduce((a,b)=>a+b.avgDuration,0)/DATA.ot.length)} min`} trend={-1.2} color="#10b981" icon="⏰" sparkData={DATA.ot.map(d=>d.avgDuration)} />
            </div>
            <div className="card">
              <SectionHeader title="OT Performance by Department" subtitle="Scheduled, completed, cancelled, and utilization" icon="🏥" />
              <DataTable
                cols={[
                  { key: "dept", label: "Department" },
                  { key: "scheduled", label: "Scheduled", right: true },
                  { key: "completed", label: "Completed", right: true, render: v => <span style={{ color: "var(--success)", fontWeight: 600 }}>{v}</span> },
                  { key: "cancelled", label: "Cancelled", right: true, render: v => <span style={{ color: v > 8 ? "var(--danger)" : "var(--gray-500)" }}>{v}</span> },
                  { key: "avgDuration", label: "Avg Duration", right: true, render: v => `${v} min` },
                  { key: "utilization", label: "OT Utilization", right: true, render: v => (
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <div style={{ width: 60, background: "var(--gray-100)", borderRadius: 4, height: 7 }}>
                        <div style={{ width: `${v}%`, background: v > 85 ? "var(--danger)" : v > 70 ? "var(--warning)" : "var(--success)", height: "100%", borderRadius: 4 }} />
                      </div>
                      <span style={{ color: v > 85 ? "var(--danger)" : v > 70 ? "var(--warning)" : "var(--success)", fontWeight: 600 }}>{v}%</span>
                    </div>
                  )},
                ]}
                rows={DATA.ot} maxH={400}
              />
            </div>
          </div>
        )}

        {/* ── INSURANCE ── */}
        {tab === "insurance" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="grid-kpi">
              <KPICard title="Total Claims" value={fmtNum(totalInsuranceClaims)} trend={6.1} color="#3b82f6" icon="📋" sparkData={DATA.insurance.map(d=>d.claims)} />
              <KPICard title="Approved Claims" value={fmtNum(DATA.insurance.reduce((a,b)=>a+b.approved,0))} trend={5.5} color="#10b981" icon="✅" sparkData={DATA.insurance.map(d=>d.approved)} />
              <KPICard title="Pending Claims" value={fmtNum(totalInsurancePending)} trend={-3.0} color="#f59e0b" icon="⏳" sparkData={DATA.insurance.map(d=>d.pending)} />
              <KPICard title="Rejected Claims" value={fmtNum(DATA.insurance.reduce((a,b)=>a+b.rejected,0))} trend={-4.2} color="#ef4444" icon="❌" sparkData={DATA.insurance.map(d=>d.rejected)} />
              <KPICard title="Total Claim Value" value={fmt(DATA.insurance.reduce((a,b)=>a+b.amount,0))} trend={7.0} color="#8b5cf6" icon="💰" sparkData={DATA.insurance.map(d=>d.amount)} />
              <KPICard title="Avg TAT" value={`${Math.round(DATA.insurance.reduce((a,b)=>a+b.avgDays,0)/DATA.insurance.length)} days`} sub="Target: <21 days" trend={-5.0} color="#ec4899" icon="📅" sparkData={DATA.insurance.map(d=>d.avgDays)} />
            </div>
            <div className="card">
              <SectionHeader title="Insurance & TPA Performance" subtitle="Claims status and turnaround by insurer" icon="🏦" />
              <DataTable
                cols={[
                  { key: "insurer", label: "Insurer / TPA", render: v => (
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {v}
                      {["CGHS", "ECHS"].includes(v) && <Badge text="Govt Scheme" />}
                    </div>
                  )},
                  { key: "claims", label: "Claims", right: true },
                  { key: "approved", label: "Approved", right: true, render: v => <span style={{ color: "var(--success)" }}>{v}</span> },
                  { key: "pending", label: "Pending", right: true, render: v => <span style={{ color: "var(--warning)" }}>{v}</span> },
                  { key: "rejected", label: "Rejected", right: true, render: v => <span style={{ color: "var(--danger)" }}>{v}</span> },
                  { key: "amount", label: "Total Value", right: true, render: v => fmt(v) },
                  { key: "avgDays", label: "Avg TAT", right: true, render: v => <span style={{ color: v > 30 ? "var(--danger)" : v > 21 ? "var(--warning)" : "var(--success)", fontWeight: 600 }}>{v} days</span> },
                ]}
                rows={DATA.insurance} maxH={380}
              />
            </div>
          </div>
        )}

        {/* ── APPOINTMENTS ── */}
        {tab === "appointments" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="grid-kpi">
              {["Confirmed", "Completed", "Cancelled", "No-Show"].map(s => {
                const cnt = DATA.appointments.filter(a => a.status === s).length;
                const colors2 = { Confirmed: "#3b82f6", Completed: "#10b981", Cancelled: "#ef4444", "No-Show": "#f59e0b" };
                const icons2 = { Confirmed: "📅", Completed: "✅", Cancelled: "❌", "No-Show": "👤" };
                return <KPICard key={s} title={s} value={fmtNum(cnt)} color={colors2[s]} icon={icons2[s]} trend={0} sparkData={[8,10,9,11,8,10,9,10,11,10,9,cnt]} />;
              })}
            </div>
            <div className="card">
              <SectionHeader title="Appointment Records" subtitle="Filter and view all appointments" icon="📅" />
              <input value={aptFilter} onChange={e => setAptFilter(e.target.value)} placeholder="Filter by department, doctor, or status…" style={{ marginBottom: 12, width: "100%" }} />
              <DataTable
                cols={[
                  { key: "id", label: "Appt ID" },
                  { key: "patient", label: "Patient" },
                  { key: "doctor", label: "Doctor" },
                  { key: "dept", label: "Department" },
                  { key: "date", label: "Date" },
                  { key: "time", label: "Time" },
                  { key: "type", label: "Type" },
                  { key: "status", label: "Status", render: v => <Badge text={v} /> },
                ]}
                rows={filteredApts} maxH={420}
              />
            </div>
          </div>
        )}

        {/* ── NABH COMPLIANCE ── */}
        {tab === "nabh" && <NABHComplianceTab />}

        {/* ── AI CONCIERGE ── */}
        {tab === "ai" && (
          <div className="grid-2" style={{ alignItems: "start" }}>
            <div>
              <SectionHeader title="AI Hospital Concierge" subtitle="RAG-powered · Voice-enabled · DPDP Act 2023 compliant · Ask anything" icon="🤖" />
              <AIConcierge />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div className="card">
                <SectionHeader title="Live Alerts" subtitle="Explainable rule-based alerts requiring CEO attention" icon="🔔" />
                <AlertsPanel showExplain={true} />
              </div>
              <div className="card">
                <SectionHeader title="Hospital Snapshot" subtitle="Key metrics at a glance" icon="📊" />
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {[
                    { l: "Annual Revenue", v: fmt(totalRevenue), c: "#3b82f6" },
                    { l: "Net Profit", v: fmt(netProfit), c: "#10b981" },
                    { l: "Total Patients", v: fmtNum(totalPatients), c: "#8b5cf6" },
                    { l: "Bed Occupancy", v: "78%", c: "#f59e0b" },
                    { l: "Total Staff", v: fmtNum(totalStaff), c: "#ec4899" },
                    { l: "Pending Claims", v: fmtNum(totalInsurancePending), c: "#ef4444" },
                  ].map(({ l, v, c }) => (
                    <div key={l} style={{ background: "var(--gray-50)", borderRadius: 10, padding: "10px 12px", borderLeft: `3px solid ${c}` }}>
                      <div style={{ fontSize: 10, color: "var(--gray-400)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{l}</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: "var(--gray-900)", marginTop: 2 }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* FOOTER */}
      <div style={{ textAlign: "center", padding: "16px 24px", color: "var(--gray-400)", fontSize: 11, borderTop: "1px solid var(--gray-200)", background: "white", marginTop: 8 }}>
        {HOSPITAL.name} · CEO Business Intelligence Dashboard · FY {HOSPITAL.fy} ·{" "}
        <span style={{ color: "var(--primary-500)" }}>DPDP Act 2023 Compliant</span> ·{" "}
        <span style={{ color: "var(--success)" }}>NABH Accreditation Track</span>
      </div>
    </div>
  );
}
