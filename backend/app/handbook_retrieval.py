"""Focused claim-context retrieval over the external handbook knowledge base."""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.handbook_embeddings import Embedder, OpenRouterEmbedder
from app.handbook_knowledge import ChromaHandbookVectorStore, VectorStore


def build_retrieval_query(claim_context: dict[str, Any]) -> str:
    claim = claim_context.get("claim", {})
    policy = claim_context.get("policy", {})
    document_types = [document.get("document_type") for document in claim_context.get("documents", []) if document.get("document_type")]
    processing = claim_context.get("processing", {})
    parts = [
        f"product line: {policy.get('product_line', '')}",
        f"claim type: {claim.get('claim_type', '')}",
        f"claimed amount: {claim.get('claimed_amount', '')}",
        f"description: {claim.get('description', '')}",
        f"riders: {', '.join(policy.get('riders') or [])}",
        f"documents: {', '.join(document_types)}",
        f"missing documents: {', '.join(processing.get('missing_documents') or [])}",
        f"processing outcome: {processing.get('outcome', '')}",
    ]
    return "\n".join(part for part in parts if not part.endswith(": "))[:5000]


class HandbookRetriever:
    def __init__(self, store: VectorStore, embedder: Embedder):
        self.store = store
        self.embedder = embedder

    @classmethod
    def from_settings(cls) -> "HandbookRetriever":
        return cls(ChromaHandbookVectorStore(settings.HANDBOOK_VECTOR_DB_DIR, settings.HANDBOOK_VECTOR_COLLECTION), OpenRouterEmbedder())

    def retrieve(self, claim_context: dict[str, Any], limit: int = 6) -> dict[str, Any]:
        query = build_retrieval_query(claim_context)
        return {"query": query, "results": self.store.query(self.embedder.embed([query])[0], limit)}
