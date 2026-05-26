"""
backend/rag/query_engine.py
----------------------------
LlamaIndex-style RAG pipeline using ChromaDB as vector store.
LLM synthesis uses OpenRouter (OpenAI-compatible) instead of Anthropic.

Pipeline:
  1. User question → ChromaDB semantic search → top-4 relevant chunks
  2. Chunks + hospital KPI context → OpenRouter LLM
  3. Source attribution for explainability

Fallback: If OpenRouter unavailable, returns top document excerpt.
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

_rag_collection = None


def _init_collection():
    global _rag_collection
    if _rag_collection is None:
        from rag.embedder import build_index
        _rag_collection = build_index()
    return _rag_collection


def query_rag(question: str, context: dict) -> Tuple[str, List[str]]:
    """
    Query the RAG pipeline.
    Returns (answer, source_citations).
    """
    collection = _init_collection()
    if collection is None:
        raise RuntimeError("RAG collection unavailable")

    from rag.embedder import query_collection
    chunks = query_collection(collection, question, n_results=4)

    if not chunks:
        raise RuntimeError("No relevant documents found")

    # Filter by relevance threshold
    relevant = [c for c in chunks if c["relevance_score"] > 0.3]
    if not relevant:
        raise RuntimeError("No sufficiently relevant documents found (score < 0.3)")

    # Build context text for LLM
    context_text = "\n\n".join([
        f"[Source: {c['metadata'].get('domain', 'Hospital Policy')}]\n{c['text']}"
        for c in relevant
    ])

    top = relevant[0]
    answer = _synthesize_answer(question, context_text, context, top)
    sources = list(set([c["metadata"].get("domain", "Hospital Policy") for c in relevant]))

    return answer, sources


def _synthesize_answer(question: str, context_text: str, kpi_context: dict, top_doc: dict) -> str:
    """
    Synthesize an answer using OpenRouter API.
    Falls back to document excerpt if API is unavailable.
    """
    domain = top_doc["metadata"].get("domain", "Hospital Operations")

    # Try OpenRouter
    try:
        from config import settings
        if settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY not in ("", "sk-or-...", "your-openrouter-key-here"):
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
            )

            prompt = (
                f"You are a hospital AI assistant. Using ONLY the knowledge base extracts below, "
                f"answer the CEO's question concisely (2-3 sentences). "
                f"Do not make up information not in the extracts.\n\n"
                f"Hospital Context:\n"
                f"Revenue: ₹{kpi_context.get('revenue_cr', 'N/A')} Cr | "
                f"Patients: {kpi_context.get('total_patients', 'N/A')} | "
                f"BOR: {kpi_context.get('bor', 'N/A')}%\n\n"
                f"Knowledge Base:\n{context_text}\n\n"
                f"CEO Question: {question}\n\nAnswer:"
            )

            response = client.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": settings.OPENROUTER_SITE_URL,
                    "X-Title": settings.OPENROUTER_SITE_NAME,
                },
            )
            return response.choices[0].message.content.strip()

    except Exception as exc:
        logger.warning("RAG OpenRouter synthesis failed: %s", exc)

    # Fallback: return top document excerpt
    text = top_doc["text"]
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
    answer_sentences = sentences[:3] if sentences else [text[:300]]
    return ". ".join(answer_sentences) + f". (Source: {domain})"
