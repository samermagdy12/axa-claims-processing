"""Configurable embeddings for handbook retrieval, independent from OCR and LLM analysis."""
from __future__ import annotations

from typing import Protocol

import httpx

from app.config import settings
from app.handbook_knowledge import HandbookKnowledgeError


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenRouterEmbedder:
    def __init__(self, api_key: str | None = None, model: str | None = None, url: str | None = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_EMBEDDING_MODEL
        self.url = url or settings.OPENROUTER_EMBEDDING_URL

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key or not self.model:
            raise HandbookKnowledgeError("OpenRouter embeddings are not configured")
        try:
            response = httpx.post(self.url, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json={"model": self.model, "input": texts}, timeout=settings.CLAIM_ANALYSIS_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
            embeddings = [item["embedding"] for item in sorted(payload["data"], key=lambda item: item.get("index", 0))]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise HandbookKnowledgeError("OpenRouter embeddings request failed") from exc
        if len(embeddings) != len(texts) or not all(isinstance(vector, list) and vector for vector in embeddings):
            raise HandbookKnowledgeError("OpenRouter returned invalid embeddings")
        return embeddings
