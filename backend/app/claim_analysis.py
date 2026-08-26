"""Claim context assembly and RAG-grounded claim analysis orchestration."""
from __future__ import annotations

from typing import Any

from app.claim_analysis_llm import analyze_claim_with_fallback
from app.handbook_retrieval import HandbookRetriever


def build_claim_context(claim: dict[str, Any], policy: dict[str, Any], documents: list[dict[str, Any]], processing: dict[str, Any]) -> dict[str, Any]:
    """Pass useful evidence, not an unbounded raw-document dump, to RAG/LLM."""
    evidence_documents = []
    for document in documents:
        extraction = document.get("extraction") or {}
        evidence_documents.append({
            "document_id": str(document.get("document_id", "")),
            "document_type": document.get("document_type"),
            "structured_data": extraction.get("structured_data") or {},
            "normalized_data": extraction.get("normalized_data") or {},
            "validation": extraction.get("document_validation") or document.get("validation") or {},
            "relevant_text": (extraction.get("extracted_text") or "")[:4000],
        })
    return {
        "claim": {key: claim.get(key) for key in ("claim_id", "claim_type", "incident_date", "submission_date", "claimed_amount", "description", "status")},
        "policy": {key: policy.get(key) for key in ("policy_id", "policy_number", "product_line", "status", "start_date", "end_date", "annual_limit", "remaining_limit", "deductible", "riders")},
        "documents": evidence_documents,
        "processing": processing,
    }


def analyze_claim_context(claim_context: dict[str, Any], retriever: HandbookRetriever | None = None) -> dict[str, Any]:
    retriever = retriever or HandbookRetriever.from_settings()
    retrieval = retriever.retrieve(claim_context)
    analysis = analyze_claim_with_fallback(claim_context, retrieval)
    return {**analysis, "retrieved_handbook_references": [_reference(result) for result in retrieval["results"]], "retrieval": retrieval}


def _reference(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata") or {}
    return {"chunk_id": result.get("chunk_id"), "rule_identifier": metadata.get("rule_identifier"), "section": metadata.get("section"), "source": metadata.get("source"), "score": result.get("score")}
