import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.claim_analysis import analyze_claim_context, build_claim_context
from app.claim_analysis_llm import ClaimAnalysisError, analyze_claim_with_fallback, parse_claim_analysis_response
from app.handbook_knowledge import HandbookChunk, load_handbook_chunks
from app.handbook_retrieval import HandbookRetriever, build_retrieval_query


class FakeEmbedder:
    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeStore:
    def __init__(self):
        self.items = []

    def upsert(self, chunks, embeddings):
        self.items = list(zip(chunks, embeddings))

    def query(self, embedding, limit):
        return [{"chunk_id": "handbook-clause-0-2", "content": "Claims at or below EGP 10,000 may be auto-approved only when all conditions hold.", "score": 0.95, "metadata": {"rule_identifier": "0.2", "section": "General Rules", "source": "handbook.md"}}][:limit]


class HandbookRagTests(unittest.TestCase):
    def test_ingestion_preserves_heading_and_clause_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "handbook.md"
            path.write_text("# Handbook\n## General Rules\n\n**Clause 0.2 — Approval.**\nAll required documents must be present.", encoding="utf-8")
            chunks = load_handbook_chunks(path)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].metadata["chapter"], "Handbook")
        self.assertEqual(chunks[0].metadata["section"], "General Rules")
        self.assertEqual(chunks[0].metadata["rule_identifier"], "0.2")

    def test_retrieval_uses_focused_claim_context(self):
        context = {"claim": {"claim_type": "Collision", "claimed_amount": "7500", "description": "rear bumper damage"}, "policy": {"product_line": "Motor", "riders": []}, "documents": [{"document_type": "Repair Estimate"}], "processing": {"outcome": "ready_for_processing", "missing_documents": []}}
        retrieved = HandbookRetriever(FakeStore(), FakeEmbedder()).retrieve(context)
        self.assertIn("claim type: Collision", retrieved["query"])
        self.assertEqual(retrieved["results"][0]["metadata"]["rule_identifier"], "0.2")

    def test_analysis_response_parses_fenced_json_and_rejects_bad_json(self):
        parsed = parse_claim_analysis_response("```json\n{\"recommendation\": \"route_to_human\", \"confidence\": 0.5}\n```")
        self.assertEqual(parsed["recommendation"], "route_to_human")
        self.assertEqual(parsed["reasoning"], [])
        with self.assertRaises(ClaimAnalysisError):
            parse_claim_analysis_response("not json")

    def test_openrouter_success_and_groq_fallback_are_independent_of_ocr_models(self):
        response = {"recommendation": "settle", "confidence": 0.9}
        with patch("app.claim_analysis_llm._openrouter_claim_analysis", return_value=response) as primary, patch("app.claim_analysis_llm._groq_claim_analysis") as fallback:
            result = analyze_claim_with_fallback({}, {"results": []})
        self.assertEqual(result["provider"], "openrouter")
        fallback.assert_not_called()
        with patch("app.claim_analysis_llm._openrouter_claim_analysis", side_effect=ClaimAnalysisError("down")), patch("app.claim_analysis_llm._groq_claim_analysis", return_value={"recommendation": "route_to_human", "confidence": 0.4}) as fallback:
            result = analyze_claim_with_fallback({}, {"results": []})
        self.assertEqual(result["provider"], "groq")
        fallback.assert_called_once()
        with patch("app.claim_analysis_llm._openrouter_claim_analysis", side_effect=ClaimAnalysisError("down")), patch("app.claim_analysis_llm._groq_claim_analysis", side_effect=ClaimAnalysisError("down")):
            with self.assertRaises(ClaimAnalysisError):
                analyze_claim_with_fallback({}, {"results": []})

    def test_analysis_provider_uses_llm_model_not_vision_model(self):
        from app.claim_analysis_llm import _openrouter_claim_analysis
        from app.config import settings

        with patch.object(settings, "OPENROUTER_API_KEY", "analysis-key"), patch.object(settings, "OPENROUTER_LLM_MODEL", "reasoning-model"), patch.object(settings, "OPENROUTER_VISION_MODEL", "vision-model"), patch("app.claim_analysis_llm._request_analysis", return_value={"recommendation": "route_to_human", "confidence": 0.2}) as request:
            _openrouter_claim_analysis({}, {"results": []})
        self.assertEqual(request.call_args.args[2], "reasoning-model")

    def test_claim_analysis_receives_retrieved_rules_and_returns_structured_result(self):
        claim = {"claim_id": "claim-1", "claim_type": "Collision", "claimed_amount": 7500, "description": "rear bumper", "incident_date": "2026-06-01", "submission_date": "2026-06-02", "status": "PROCESSING"}
        policy = {"policy_id": "P-1", "product_line": "Motor", "status": "active", "riders": []}
        context = build_claim_context(claim, policy, [{"document_id": "d1", "document_type": "Repair Estimate", "extraction": {"structured_data": {"total": 7500}, "extracted_text": "Estimate total EGP 7,500", "document_validation": {"validation_passed": True}}}], {"outcome": "ready_for_processing", "missing_documents": []})
        with patch("app.claim_analysis.analyze_claim_with_fallback", return_value={"recommendation": "route_to_human", "confidence": 0.7, "summary": "Rule requires assessor confirmation.", "reasoning": [], "missing_information": [], "validation_issues": [], "consistency_issues": [], "recommended_next_actions": [], "provider": "openrouter"}):
            result = analyze_claim_context(context, HandbookRetriever(FakeStore(), FakeEmbedder()))
        self.assertEqual(result["recommendation"], "route_to_human")
        self.assertEqual(result["retrieved_handbook_references"][0]["rule_identifier"], "0.2")
