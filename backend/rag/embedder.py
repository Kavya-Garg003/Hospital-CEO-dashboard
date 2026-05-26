"""
backend/rag/embedder.py
------------------------
ChromaDB + sentence-transformers local embedding pipeline.
No external API needed for embeddings — runs fully offline.

Documents indexed:
  - Hospital SOPs (department operating procedures)
  - Financial policies
  - NABH guidelines summaries
  - Drug formulary (non-PHI)
  - CEO briefing documents

Usage:
    from rag.embedder import build_index
    index = build_index()
"""

import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def _get_chroma_client():
    import chromadb
    from config import settings
    return chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)


def _get_embedding_function():
    from chromadb.utils import embedding_functions
    from config import settings
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.EMBEDDING_MODEL
    )


def build_index(documents: List[dict] = None):
    """
    Build or update the ChromaDB vector index.
    documents: list of {"id": str, "text": str, "metadata": dict}
    If None, uses built-in synthetic hospital documents.
    """
    try:
        client = _get_chroma_client()
        ef = _get_embedding_function()

        collection = client.get_or_create_collection(
            name="hospital_knowledge",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )

        if documents is None:
            documents = _get_synthetic_documents()

        # Upsert documents (incremental — only new/changed docs)
        existing_ids = set(collection.get()["ids"])
        new_docs = [d for d in documents if d["id"] not in existing_ids]

        if new_docs:
            collection.add(
                ids=[d["id"] for d in new_docs],
                documents=[d["text"] for d in new_docs],
                metadatas=[d.get("metadata", {}) for d in new_docs],
            )
            logger.info("✅ Indexed %d new documents into ChromaDB", len(new_docs))
        else:
            logger.info("ℹ️  ChromaDB up-to-date (%d docs already indexed)", len(existing_ids))

        return collection

    except Exception as exc:
        logger.error("ChromaDB indexing failed: %s", exc)
        return None


def query_collection(collection, query: str, n_results: int = 5) -> List[dict]:
    """Semantic search over the indexed documents."""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]
        return [
            {
                "text": doc,
                "metadata": meta,
                "relevance_score": round(1 - dist, 3),
            }
            for doc, meta, dist in zip(docs, metas, distances)
        ]
    except Exception as exc:
        logger.error("ChromaDB query failed: %s", exc)
        return []


def _get_synthetic_documents() -> List[dict]:
    """Built-in hospital knowledge base documents."""
    return [
        {
            "id": "nabh-overview",
            "text": """NABH (National Accreditation Board for Hospitals) standards for Aarogya Hospital.
            Key domains: Patient Care, Infection Control, Quality Improvement, Staff Competency.
            Target compliance score: >85% for NABH accreditation.
            Current focus areas: Medication management, Patient identification, Hand hygiene compliance.""",
            "metadata": {"category": "compliance", "domain": "NABH"}
        },
        {
            "id": "bed-policy",
            "text": """Hospital Bed Management Policy. Bed Occupancy Rate (BOR) target: 75-85%.
            Critical threshold: >90% triggers automatic discharge review.
            ICU beds: 40 total. Step-down protocol: ICU → HDU → General Ward.
            Bed turnaround target: <4 hours post-discharge.""",
            "metadata": {"category": "operations", "domain": "Bed Management"}
        },
        {
            "id": "insurance-sop",
            "text": """Insurance Claims Processing SOP. TAT target: <21 days for all TPAs.
            Key TPAs: Star Health, HDFC ERGO, Bajaj Allianz, New India Assurance, Medi Assist.
            Rejection rate benchmark: <10%. Cashless claims: submit within 24h of admission.
            CGHS/ECHS claims require pre-authorization. Documentation: Discharge summary, bills, investigation reports.""",
            "metadata": {"category": "insurance", "domain": "TPA Claims"}
        },
        {
            "id": "ot-policy",
            "text": """OT (Operation Theatre) Utilization Policy. Target utilization: >80%.
            Cancellation rate benchmark: <10%. Pre-op checklist mandatory 24h before surgery.
            Emergency OT: priority over elective cases. Average case turnover time: <30 minutes.
            Key departments: Cardiology, Orthopaedics, Neurology, Gynaecology, Oncology.""",
            "metadata": {"category": "operations", "domain": "OT Management"}
        },
        {
            "id": "financial-policy",
            "text": """Financial performance targets for Aarogya Hospital FY 2024-25.
            Revenue target: ₹12 Crore per month. Net profit margin target: >25%.
            Insurance revenue mix: 60% of total revenue. OOP revenue: 40%.
            Department margin targets: Pharmacy >30%, ICU >25%, Cardiology >20%.""",
            "metadata": {"category": "finance", "domain": "Financial Targets"}
        },
        {
            "id": "hr-policy",
            "text": """HR and Staff Management Policy. Total workforce: 720 staff.
            Attrition target: <5% annually. Nurse-to-patient ratio: 1:4 in general wards, 1:2 in ICU.
            Overtime policy: max 8 hours/week. Training mandates: 40 hours/year per staff member.
            NABH requirement: 100% staff with current BLS/ACLS certification.""",
            "metadata": {"category": "hr", "domain": "Staff Management"}
        },
        {
            "id": "dpdp-policy",
            "text": """Data Protection Policy under India's Digital Personal Data Protection Act 2023.
            PHI fields encrypted: patient name, phone, Aadhaar, diagnosis.
            Consent required before data processing. Patients may request data access or erasure.
            Data retention: 7 years for medical records (NABH requirement).
            Cross-border transfer: prohibited for patient PHI.
            Data Protection Officer: dpo@aarogyahospital.in""",
            "metadata": {"category": "compliance", "domain": "DPDP Act 2023"}
        },
        {
            "id": "los-policy",
            "text": """Length of Stay (LOS) Management. Target ALOS: <5 days.
            High LOS departments: ICU (avg 7 days), Oncology (avg 6 days).
            Discharge planning initiated 48h before expected discharge.
            LOS > 14 days triggers clinical review committee.
            Weekend discharge programme reduces Monday overcrowding.""",
            "metadata": {"category": "operations", "domain": "LOS Management"}
        },
        {
            "id": "infection-control",
            "text": """Infection Control Standards (NABH IC.1 to IC.9).
            HAI rate target: <2%. Hand hygiene compliance target: >90%.
            CSSD (Central Sterile Supply Department) standard: Class A sterilization.
            Antibiotic stewardship programme: mandatory de-escalation review at 72h.
            Blood culture before antibiotic initiation in all ICU admissions.""",
            "metadata": {"category": "clinical", "domain": "Infection Control"}
        },
        {
            "id": "patient-satisfaction",
            "text": """Patient Satisfaction and Experience. Current score: 4.6/5.
            Top performer: Paediatrics (4.8/5). Areas for improvement: Waiting time, Billing clarity.
            NABH benchmark: >4.0/5. Monthly satisfaction surveys via SMS.
            Complaint resolution target: 48 hours. Patient liaison officers: 1 per floor.""",
            "metadata": {"category": "quality", "domain": "Patient Experience"}
        },
    ]
