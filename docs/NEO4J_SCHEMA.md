# 🔗 Neo4j Graph Database Schema

## Why a Graph Database?

Hospital data has complex many-to-many relationships that relational databases handle poorly:
- A patient may be treated by multiple doctors across multiple departments
- A doctor works in one department but refers to specialists in others
- Readmission patterns require multi-hop traversal (Patient → Doctor → Department → Diagnosis)
- Insurance fraud detection requires "path" queries across claim networks

Neo4j answers these in milliseconds with Cypher, vs. complex JOINs in SQL.

---

## Node Types

```cypher
(:Patient {
  patient_id: INT,          -- Internal ID (not PHI)
  age: INT,
  gender: STRING,
  patient_type: STRING,     -- inpatient / outpatient / emergency
  status: STRING,
  risk_score: INT           -- 0-100 readmission risk (ML output)
})

(:Doctor {
  staff_id: INT,
  name: STRING,             -- Doctor name (non-PHI, staff identity)
  specialty: STRING,
  department_id: INT
})

(:Department {
  dept_id: INT,
  name: STRING,
  total_beds: INT
})

(:Diagnosis {
  icd_code: STRING,         -- e.g. "I21" (Acute MI)
  name: STRING,
  category: STRING          -- ICD-10 chapter
})

(:Insurer {
  name: STRING,
  tpa_id: STRING
})

(:Procedure {
  code: STRING,
  name: STRING,             -- e.g. "Coronary bypass"
  avg_duration_min: INT
})
```

---

## Relationship Types

```cypher
-- Patient treated by Doctor (with date context)
(:Patient)-[:TREATED_BY {date: DATE, ward: STRING}]->(:Doctor)

-- Patient admitted to Department (with LOS)
(:Patient)-[:ADMITTED_TO {date: DATE, los_days: INT}]->(:Department)

-- Patient diagnosed with Diagnosis
(:Patient)-[:DIAGNOSED_WITH {severity: STRING}]->(:Diagnosis)

-- Patient has insurance claim with Insurer
(:Patient)-[:HAS_CLAIM {claim_id: INT, status: STRING, amount: FLOAT}]->(:Insurer)

-- Patient underwent Procedure
(:Patient)-[:UNDERWENT {date: DATE, ot_id: INT}]->(:Procedure)

-- Doctor works in Department
(:Doctor)-[:WORKS_IN {join_date: DATE}]->(:Department)

-- Doctor refers to another Doctor
(:Doctor)-[:REFERRED_TO {date: DATE}]->(:Doctor)

-- Diagnoses that commonly co-occur
(:Diagnosis)-[:COMORBID_WITH {frequency: FLOAT}]->(:Diagnosis)
```

---

## Schema Initialization

```cypher
-- Run once after Neo4j is started
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Patient) REQUIRE p.patient_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Doctor) REQUIRE d.staff_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (dept:Department) REQUIRE dept.dept_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (diag:Diagnosis) REQUIRE diag.icd_code IS UNIQUE;

CREATE INDEX IF NOT EXISTS FOR (p:Patient) ON (p.risk_score);
CREATE INDEX IF NOT EXISTS FOR (d:Doctor) ON (d.specialty);
CREATE INDEX IF NOT EXISTS FOR (p:Patient) ON (p.status);
```

---

## CEO-Level Query Examples

### 1. Which departments have highest readmission rates?
```cypher
MATCH (p:Patient)-[:ADMITTED_TO]->(dept:Department)
WHERE p.risk_score > 70
RETURN dept.name, count(p) as high_risk_patients
ORDER BY high_risk_patients DESC
```

### 2. Patient care pathway analysis
```cypher
MATCH path = (p:Patient {patient_id: 123})-[*1..5]->(n)
WHERE NOT n:Patient
RETURN nodes(path), relationships(path)
```

### 3. Referral network — who refers to whom?
```cypher
MATCH (d1:Doctor)-[r:REFERRED_TO]->(d2:Doctor)
RETURN d1.name as from_doctor, d2.name as to_doctor, count(r) as referrals
ORDER BY referrals DESC
LIMIT 20
```

### 4. Insurance fraud detection — patients with many insurers
```cypher
MATCH (p:Patient)-[c:HAS_CLAIM]->(ins:Insurer)
WITH p, count(DISTINCT ins) as insurer_count, sum(c.amount) as total_amount
WHERE insurer_count > 2
RETURN p.patient_id, insurer_count, total_amount
ORDER BY total_amount DESC
```

### 5. Comorbidity map — most common diagnosis pairs
```cypher
MATCH (p:Patient)-[:DIAGNOSED_WITH]->(d1:Diagnosis),
      (p)-[:DIAGNOSED_WITH]->(d2:Diagnosis)
WHERE d1.icd_code < d2.icd_code
RETURN d1.name, d2.name, count(p) as co_occurrences
ORDER BY co_occurrences DESC
LIMIT 10
```

### 6. Department-wise doctor performance (by completed OT cases)
```cypher
MATCH (p:Patient)-[:UNDERWENT]->(proc:Procedure)
MATCH (p)-[:TREATED_BY]->(d:Doctor)-[:WORKS_IN]->(dept:Department)
RETURN dept.name, d.name as doctor, count(proc) as surgeries
ORDER BY dept.name, surgeries DESC
```

---

## Graceful Degradation

If Neo4j is not running:
- `get_neo4j_driver()` returns `None`
- Graph endpoints return empty `GraphData` (no crash)
- All other non-graph features work normally
- Warning logged: "Neo4j unavailable — Graph features will return empty data"

---

## Starting Neo4j Community Server (Windows)

```bash
# Download: https://neo4j.com/deployment-center/ (Community, Windows ZIP)
# Extract to: C:\neo4j\

# Start:
C:\neo4j\bin\neo4j console

# Or as a Windows service:
C:\neo4j\bin\neo4j install-service
C:\neo4j\bin\neo4j start

# Default: http://localhost:7474 (browser)
# Bolt: bolt://localhost:7687
# Default credentials: neo4j / neo4j (change on first login)
```
