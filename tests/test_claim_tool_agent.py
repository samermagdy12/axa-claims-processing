import json
import unittest
from unittest.mock import patch

from app.claim_analysis_agent import _run_provider_loop, analyze_claim_with_tools
from app.claim_analysis_llm import ClaimAnalysisError
from app.claim_tools import ClaimToolExecutor, TOOL_SCHEMAS, SubmitRecommendation


class FakeExecutor:
    claim_id = "claim-1"
    provider = "openrouter"
    retrieved = {}
    submission = None
    def __init__(self): self.calls = []
    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "approve_or_route_claim":
            self.submission = {"recommendation": "route_to_human", "confidence": .5, "summary": "Review", "reasoning": [], "retrieved_handbook_references": []}
        return {"ok": True, "result": {"accepted": True}}


class Response:
    def __init__(self, message): self.message = message
    def raise_for_status(self): pass
    def json(self): return {"choices": [{"message": self.message}]}


class ClaimToolAgentTests(unittest.TestCase):
    def test_schemas_expose_all_expected_real_tools(self):
        self.assertEqual({item["function"]["name"] for item in TOOL_SCHEMAS}, {"extract_claim", "lookup_policy", "search_policy_docs", "validate_claim", "approve_or_route_claim"})

    def test_loop_sends_tools_executes_calls_and_returns_submission(self):
        executor = FakeExecutor()
        responses = iter([Response({"content": None, "tool_calls": [{"id": "1", "function": {"name": "approve_or_route_claim", "arguments": json.dumps({"claim_id": "claim-1", "recommendation": "route_to_human"})}}]}), Response({"content": "Submitted."})])
        with patch("app.claim_analysis_agent.httpx.post", side_effect=lambda *a, **k: next(responses)) as post:
            result = _run_provider_loop("url", "key", "model", executor)
        self.assertEqual(result["recommendation"], "route_to_human")
        self.assertEqual(executor.calls[0][0], "approve_or_route_claim")
        self.assertIn("tools", post.call_args.kwargs["json"])
        self.assertEqual(post.call_args.kwargs["json"]["tool_choice"], "auto")

    def test_loop_rejects_completion_without_final_tool(self):
        with patch("app.claim_analysis_agent.httpx.post", return_value=Response({"content": "settle"})):
            with self.assertRaises(ClaimAnalysisError): _run_provider_loop("url", "key", "model", FakeExecutor())

    def test_provider_failure_falls_back_to_groq_adapter(self):
        executor = FakeExecutor()
        with patch("app.claim_analysis_agent.settings.OPENROUTER_API_KEY", "a"), patch("app.claim_analysis_agent.settings.OPENROUTER_LLM_MODEL", "a"), patch("app.claim_analysis_agent.settings.GROQ_API_KEY", "b"), patch("app.claim_analysis_agent.settings.GROQ_LLM_MODEL", "b"), patch("app.claim_analysis_agent._run_provider_loop", side_effect=[ClaimAnalysisError("primary failed"), {"recommendation": "route_to_human"}]) as loop:
            self.assertEqual(analyze_claim_with_tools(executor)["recommendation"], "route_to_human")
        self.assertEqual(loop.call_count, 2)

    def test_executor_rejects_cross_claim_arguments_before_database_access(self):
        executor = ClaimToolExecutor("claim-1", {"user_id": "u", "role_name": "Customer"}, None)
        result = executor.execute("extract_claim", {"claim_id": "claim-2"})
        self.assertFalse(result["ok"])

    def test_hallucinated_handbook_reference_is_rejected(self):
        executor = ClaimToolExecutor("claim-1", {"user_id": "u", "role_name": "Customer"}, None)
        executor._claim_policy = lambda: {"claimed_amount": 5000, "policy_status": "ACTIVE", "product_line": "MOTOR", "remaining_limit": 50000}
        executor._processing = lambda: {"missing_documents": [], "invalid_documents": [], "duplicate_documents": [], "manual_review_required": False, "consistency": {"has_conflicts": False}}
        executor._validate_claim = lambda _: {"policy_valid": True, "duplicate_claim": False, "risk_signals": []}
        args = SubmitRecommendation(claim_id="claim-1", recommendation="reject", confidence=.8, reasoning=[{"finding": "Excluded", "handbook_references": [{"chunk_id": "invented"}]}])
        with self.assertRaises(ValueError): executor._approve_or_route_claim(args)

    def test_settlement_submission_is_overridden_by_deterministic_limit(self):
        executor = ClaimToolExecutor("claim-1", {"user_id": "u", "role_name": "Customer"}, None)
        executor.retrieved = {"cover": {"chunk_id": "cover", "score": .9, "metadata": {"rule_identifier": "2.1", "rule_category": "COVERAGE", "applies_to_products": "MOTOR"}}, "authority": {"chunk_id": "authority", "score": .9, "metadata": {"rule_identifier": "0.2", "rule_category": "SETTLEMENT", "applies_to_products": "ALL"}}}
        executor._claim_policy = lambda: {"claimed_amount": 12000, "policy_status": "ACTIVE", "product_line": "MOTOR", "remaining_limit": 50000}
        executor._processing = lambda: {"missing_documents": [], "invalid_documents": [], "duplicate_documents": [], "manual_review_required": False, "consistency": {"has_conflicts": False}}
        executor._validate_claim = lambda _: {"policy_valid": True, "duplicate_claim": False, "risk_signals": []}
        args = SubmitRecommendation(claim_id="claim-1", recommendation="settle", confidence=.9, reasoning=[{"finding": "Covered", "handbook_references": [{"chunk_id": "cover"}, {"chunk_id": "authority"}]}])
        self.assertEqual(executor._approve_or_route_claim(args)["deterministic_preview"]["final_decision"], "route_to_human")
