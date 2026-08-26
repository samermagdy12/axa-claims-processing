import unittest

from app.decision_engine import decide_claim


def decide(**overrides):
    inputs = {
        "claim": {"claimed_amount": 5000}, "policy": {"status": "ACTIVE"},
        "processing": {"missing_documents": [], "invalid_documents": [], "duplicate_documents": [], "manual_review_required": False, "consistency": {"has_conflicts": False}},
        "analysis": {"recommendation": "settle", "retrieved_handbook_references": [{"chunk_id": "0.2", "rule_identifier": "0.2"}], "summary": "Covered under clause 0.2.", "reasoning": []},
    }
    inputs.update(overrides)
    return decide_claim(**inputs)


class DecisionEngineTests(unittest.TestCase):
    def test_missing_documents_win_but_all_rules_are_recorded(self):
        result = decide(claim={"claimed_amount": 15000}, processing={"missing_documents": ["Police Report"], "invalid_documents": [], "duplicate_documents": [], "manual_review_required": False, "consistency": {"has_conflicts": False}})
        self.assertEqual(result["final_decision"], "request_documents")
        self.assertEqual([rule["rule_id"] for rule in result["triggered_rules"]], ["MISSING_REQUIRED_DOCUMENTS", "AMOUNT_OVER_AUTO_SETTLEMENT_LIMIT"])

    def test_invalid_document_requests_replacement(self):
        self.assertEqual(decide(processing={"missing_documents": [], "invalid_documents": [{"document_id": "x"}], "duplicate_documents": [], "manual_review_required": True, "consistency": {"has_conflicts": False}})["final_decision"], "request_documents")

    def test_evidence_backed_exclusion_rejects(self):
        self.assertEqual(decide(analysis={"recommendation": "reject", "retrieved_handbook_references": [{"chunk_id": "50-1", "rule_identifier": "50.1"}], "summary": "This event is excluded from cover.", "reasoning": []})["final_decision"], "reject")

    def test_conflict_duplicate_and_risk_route_to_human(self):
        processing = {"missing_documents": [], "invalid_documents": [], "duplicate_documents": [], "manual_review_required": False, "consistency": {"has_conflicts": True}}
        self.assertEqual(decide(processing=processing)["final_decision"], "route_to_human")
        self.assertEqual(decide(duplicate_detection={"duplicate_detected": True})["final_decision"], "route_to_human")
        self.assertEqual(decide(risk_signals=["high risk"])["final_decision"], "route_to_human")

    def test_amount_over_limit_overrides_settle(self):
        self.assertEqual(decide(claim={"claimed_amount": 10000.01})["final_decision"], "route_to_human")

    def test_eligible_claim_settles(self):
        result = decide()
        self.assertEqual(result["final_decision"], "settle")
        self.assertTrue(result["auto_processed"])

    def test_unsupported_rejection_is_safe(self):
        self.assertEqual(decide(analysis={"recommendation": "reject", "retrieved_handbook_references": [], "summary": "Not covered", "reasoning": []})["final_decision"], "route_to_human")
