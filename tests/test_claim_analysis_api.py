import unittest
from unittest.mock import patch

from app.main import analyze_claim


class Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class AnalysisDatabase:
    def execute(self, statement, params):
        sql = str(statement)
        if "p.status AS policy_status" in sql:
            return Result([{
                "claim_id": "claim-1", "policy_id": "P-1", "claim_type": "Collision", "incident_date": "2026-06-01",
                "submission_date": "2026-06-02", "claimed_amount": 7500, "description": "rear bumper damage", "status": "PROCESSING",
                "user_id": "customer-1", "policy_number": "POL-1", "product_line": "Motor", "policy_status": "active",
                "start_date": "2026-01-01", "end_date": "2026-12-31", "annual_limit": 50000, "remaining_limit": 50000, "deductible": 500, "riders": [],
            }])
        if "FROM claim_required_documents" in sql:
            return Result([{"document_type": "Repair Estimate", "is_required": True, "status": "UPLOADED"}])
        if "FROM claim_documents" in sql:
            return Result([{"document_id": "document-1", "document_type": "Repair Estimate"}])
        if "FROM claim_extractions" in sql:
            return Result([{"extracted_data": {"document_id": "document-1", "document_type": "Repair Estimate", "extracted_text": "Estimate total EGP 7,500", "structured_data": {"total": 7500}, "normalized_data": {"document_type": "Repair Estimate", "fields": {"amount": 7500}}, "document_validation": {"validation_passed": True}}}])
        raise AssertionError(sql)


class ClaimAnalysisApiTests(unittest.TestCase):
    def test_endpoint_returns_rag_grounded_structured_recommendation(self):
        analysis = {
            "recommendation": "route_to_human", "confidence": 0.72, "summary": "A handbook rule requires review.",
            "reasoning": [{"finding": "Amount needs assessment.", "evidence": "Estimate total EGP 7,500", "handbook_references": [{"chunk_id": "handbook-0-2"}]}],
            "missing_information": [], "validation_issues": [], "consistency_issues": [], "recommended_next_actions": ["Assign an assessor"],
            "retrieved_handbook_references": [{"chunk_id": "handbook-0-2", "rule_identifier": "0.2"}], "retrieval": {"query": "motor collision", "results": [{"chunk_id": "handbook-0-2"}]}, "provider": "openrouter",
        }
        with patch("app.main.analyze_claim_with_tools", return_value=analysis) as run_analysis:
            result = analyze_claim("claim-1", {"user_id": "customer-1", "role_name": "Customer"}, AnalysisDatabase())
        self.assertEqual(result["claim_id"], "claim-1")
        self.assertEqual(result["recommendation"], "route_to_human")
        self.assertEqual(result["retrieved_handbook_references"][0]["rule_identifier"], "0.2")
        executor = run_analysis.call_args.args[0]
        self.assertEqual(executor.claim_id, "claim-1")
