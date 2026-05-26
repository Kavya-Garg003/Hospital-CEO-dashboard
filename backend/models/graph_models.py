"""
backend/models/graph_models.py
-------------------------------
Neo4j graph schema definitions and query functions.

Node types: Patient, Doctor, Department, Diagnosis, Insurer, Procedure
Relationship types: TREATED_BY, ADMITTED_TO, DIAGNOSED_WITH, HAS_CLAIM,
                    UNDERWENT, WORKS_IN, REFERRED_TO, COMORBID_WITH

All queries use parameterized Cypher to prevent injection.
"""

from typing import Optional
from models.schemas import GraphData, GraphNode, GraphEdge


def init_graph_schema(driver):
    """Create constraints and indexes for Neo4j schema."""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Patient) REQUIRE p.patient_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Doctor) REQUIRE d.staff_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (dept:Department) REQUIRE dept.dept_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (diag:Diagnosis) REQUIRE diag.icd_code IS UNIQUE",
        "CREATE INDEX IF NOT EXISTS FOR (p:Patient) ON (p.risk_score)",
        "CREATE INDEX IF NOT EXISTS FOR (d:Doctor) ON (d.specialty)",
    ]
    with driver.session() as session:
        for stmt in constraints:
            try:
                session.run(stmt)
            except Exception as e:
                pass  # Constraint may already exist


def sync_patient_to_neo4j(driver, patient_data: dict):
    """
    Sync a patient record to Neo4j graph.
    Only non-PHI fields are stored in Neo4j.
    """
    cypher = """
    MERGE (p:Patient {patient_id: $patient_id})
    SET p.age = $age,
        p.gender = $gender,
        p.patient_type = $patient_type,
        p.status = $status,
        p.risk_score = $risk_score

    MERGE (dept:Department {dept_id: $dept_id})
    SET dept.name = $dept_name

    MERGE (p)-[r:ADMITTED_TO]->(dept)
    SET r.date = $admission_date,
        r.los_days = $los_days
    """
    with driver.session() as session:
        session.run(cypher, **patient_data)


def get_patient_graph(driver, limit: int = 100) -> GraphData:
    """
    Return patient-doctor-department graph for visualisation.
    Uses non-PHI data only (patient_id, not name).
    """
    cypher = """
    MATCH (p:Patient)-[r:TREATED_BY]->(d:Doctor)-[w:WORKS_IN]->(dept:Department)
    RETURN p, r, d, w, dept
    LIMIT $limit
    """
    nodes = {}
    edges = []

    try:
        with driver.session() as session:
            result = session.run(cypher, limit=limit)
            for record in result:
                p = record["p"]
                d = record["d"]
                dept = record["dept"]

                pid = f"P{p['patient_id']}"
                did = f"D{d['staff_id']}"
                deptid = f"DEPT_{dept['dept_id']}"

                if pid not in nodes:
                    nodes[pid] = GraphNode(id=pid, label=f"Patient #{p['patient_id']}", type="Patient",
                                           properties={"age": p.get("age"), "risk_score": p.get("risk_score", 0)})
                if did not in nodes:
                    nodes[did] = GraphNode(id=did, label=d.get("name", "Doctor"), type="Doctor",
                                           properties={"specialty": d.get("specialty", "")})
                if deptid not in nodes:
                    nodes[deptid] = GraphNode(id=deptid, label=dept.get("name", "Dept"), type="Department",
                                              properties={})

                edges.append(GraphEdge(source=pid, target=did, relationship="TREATED_BY"))
                edges.append(GraphEdge(source=did, target=deptid, relationship="WORKS_IN"))

    except Exception as e:
        return GraphData(nodes=[], edges=[], total_nodes=0, total_edges=0)

    node_list = list(nodes.values())
    return GraphData(nodes=node_list, edges=edges, total_nodes=len(node_list), total_edges=len(edges))


def get_department_graph(driver, dept_name: str) -> GraphData:
    """Department-centric subgraph showing all doctors and patient volume."""
    cypher = """
    MATCH (dept:Department {name: $dept_name})<-[:WORKS_IN]-(d:Doctor)
    OPTIONAL MATCH (p:Patient)-[:TREATED_BY]->(d)
    RETURN dept, d, count(p) as patient_count
    LIMIT 50
    """
    nodes = {}
    edges = []
    try:
        with driver.session() as session:
            result = session.run(cypher, dept_name=dept_name)
            for record in result:
                dept = record["dept"]
                d = record["d"]
                pcount = record["patient_count"]

                deptid = f"DEPT_{dept['dept_id']}"
                did = f"D{d['staff_id']}"

                if deptid not in nodes:
                    nodes[deptid] = GraphNode(id=deptid, label=dept.get("name"), type="Department")
                if did not in nodes:
                    nodes[did] = GraphNode(id=did, label=d.get("name", "Doctor"), type="Doctor",
                                           properties={"patient_count": pcount})
                edges.append(GraphEdge(source=did, target=deptid, relationship="WORKS_IN"))
    except Exception:
        return GraphData(nodes=[], edges=[], total_nodes=0, total_edges=0)

    node_list = list(nodes.values())
    return GraphData(nodes=node_list, edges=edges, total_nodes=len(node_list), total_edges=len(edges))


def get_readmission_pathway(driver, patient_id: int) -> GraphData:
    """Trace the care pathway for a patient to understand readmission risk factors."""
    cypher = """
    MATCH path = (p:Patient {patient_id: $patient_id})-[*1..4]->(n)
    WHERE NOT n:Patient
    RETURN nodes(path) as nodes, relationships(path) as rels
    """
    nodes_map = {}
    edges = []
    try:
        with driver.session() as session:
            result = session.run(cypher, patient_id=patient_id)
            for record in result:
                for node in record["nodes"]:
                    nid = str(node.id)
                    label = list(node.labels)[0] if node.labels else "Unknown"
                    nodes_map[nid] = GraphNode(id=nid, label=label, type=label, properties=dict(node))
                for rel in record["rels"]:
                    edges.append(GraphEdge(
                        source=str(rel.start_node.id),
                        target=str(rel.end_node.id),
                        relationship=rel.type,
                    ))
    except Exception:
        return GraphData(nodes=[], edges=[], total_nodes=0, total_edges=0)

    node_list = list(nodes_map.values())
    return GraphData(nodes=node_list, edges=edges, total_nodes=len(node_list), total_edges=len(edges))
