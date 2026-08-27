import unittest

from app.decision_engine import decide_claim


def decide(**overrides):
    inputs = {
        "claim": {"claimed_amount": 5000}, "policy": {"status": "ACTIVE", "validation_passed": True, "remaining_limit": 50000, "product_line": "MOTOR"},
        "processing": {"missing_documents": [], "invalid_documents": [], "duplicate_documents": [], "manual_review_required": False, "consistency": {"has_conflicts": False}},
        "analysis": {"recommendation": "settle", "retrieved_handbook_references": [{"chunk_id": "0.2", "rule_identifier": "0.2", "rule_category": "SETTLEMENT", "applies_to_products": "ALL"}, {"chunk_id": "2.1", "rule_identifier": "2.1", "rule_category": "COVERAGE", "applies_to_products": "MOTOR"}], "summary": "Covered under applicable clauses.", "reasoning": [{"finding": "Collision is a covered motor peril and meets the automatic settlement authority.", "evidence": "Claim facts match the supplied rules.", "handbook_references": [{"chunk_id": "0.2"}, {"chunk_id": "2.1"}]}]},
    }
    inputs.update(overrides)
    return decide_claim(**inputs)


class DecisionEngineTests(unittest.TestCase):
    def test_missing_documents_win_but_all_rules_are_recorded(self):
        result = decide(claim={"claimed_amount": 15000}, processing={"missing_documents": ["Police Report"], "invalid_documents": [], "duplicate_documents": [], "manual_review_required": False, "consistency": {"has_conflicts": False}})
        self.assertEqual(result["final_decision"], "request_documents")
        self.assertEqual([rule["rule_id"] for rule in result["triggered_rules"]], ["MISSING_REQUIRED_DOCUMENT", "CLAIM_AMOUNT_ABOVE_AUTO_APPROVAL_LIMIT"])
        self.assertEqual(result["reason_code"], "MISSING_REQUIRED_DOCUMENT")
        self.assertIn("Police Report", result["reason"])

    def test_invalid_document_requests_replacement(self):
        self.assertEqual(decide(processing={"missing_documents": [], "invalid_documents": [{"document_id": "x"}], "duplicate_documents": [], "manual_review_required": True, "consistency": {"has_conflicts": False}})["final_decision"], "request_documents")

    def test_evidence_backed_exclusion_rejects(self):
        self.assertEqual(decide(analysis={"recommendation": "reject", "retrieved_handbook_references": [{"chunk_id": "50-1", "rule_identifier": "5.1", "rule_category": "EXCLUSION", "applies_to_products": "ALL"}], "summary": "This event is excluded from cover.", "reasoning": [{"finding": "War-related loss is excluded.", "evidence": "The reported event is war-related.", "handbook_references": [{"chunk_id": "50-1"}]}]})["final_decision"], "reject")

    def test_conflict_duplicate_and_risk_route_to_human(self):
        processing = {"missing_documents": [], "invalid_documents": [], "duplicate_documents": [], "manual_review_required": False, "consistency": {"has_conflicts": True}}
        self.assertEqual(decide(processing=processing)["final_decision"], "route_to_human")
        self.assertEqual(decide(duplicate_detection={"duplicate_detected": True})["final_decision"], "route_to_human")
        self.assertEqual(decide(risk_signals=["high risk"])["final_decision"], "route_to_human")

    def test_amount_over_limit_overrides_settle(self):
        result = decide(claim={"claimed_amount": 15000})
        self.assertEqual(result["final_decision"], "route_to_human")
        self.assertEqual(result["reason_code"], "CLAIM_AMOUNT_ABOVE_AUTO_APPROVAL_LIMIT")
        self.assertIn("15,000.00", result["reason"])

    def test_remaining_limit_and_policy_date_validation_block_auto_settlement(self):
        self.assertEqual(decide(policy={"status": "ACTIVE", "validation_passed": True, "remaining_limit": 4000})["final_decision"], "route_to_human")
        self.assertEqual(decide(policy={"status": "ACTIVE", "validation_passed": False, "remaining_limit": 50000})["final_decision"], "reject")

    def test_eligible_claim_settles(self):
        result = decide()
        self.assertEqual(result["final_decision"], "settle")
        self.assertTrue(result["auto_processed"])
        self.assertEqual(result["reason_code"], "AUTO_APPROVED")

    def test_unsupported_rejection_is_safe(self):
        self.assertEqual(decide(analysis={"recommendation": "reject", "retrieved_handbook_references": [], "summary": "Not covered", "reasoning": []})["final_decision"], "route_to_human")

    def test_document_requirement_can_never_authorize_rejection(self):
        result = decide(analysis={"recommendation": "reject", "retrieved_handbook_references": [{"chunk_id": "2.10", "rule_category": "DOCUMENT_REQUIREMENT", "applies_to_products": "MOTOR"}], "summary": "Not covered", "reasoning": [{"finding": "Required documents are not covered.", "evidence": "Police report is absent.", "handbook_references": [{"chunk_id": "2.10"}]}]})
        self.assertEqual(result["final_decision"], "route_to_human")

    def test_document_request_outranks_an_otherwise_supported_rejection(self):
        result = decide(processing={"missing_documents": ["Police Report"], "invalid_documents": [], "duplicate_documents": [], "manual_review_required": False, "consistency": {"has_conflicts": False}}, analysis={"recommendation": "reject", "retrieved_handbook_references": [{"chunk_id": "5.1", "rule_category": "EXCLUSION", "applies_to_products": "ALL"}], "summary": "Excluded", "reasoning": [{"finding": "War-related loss is excluded.", "evidence": "", "handbook_references": [{"chunk_id": "5.1"}]}]})
        self.assertEqual(result["final_decision"], "request_documents")
        self.assertEqual([rule["rule_id"] for rule in result["triggered_rules"][:2]], ["MISSING_REQUIRED_DOCUMENT", "POLICY_EXCLUSION_APPLIES"])

    def test_unrelated_or_uncited_exclusion_cannot_reject(self):
        result = decide(analysis={"recommendation": "reject", "retrieved_handbook_references": [{"chunk_id": "1.6", "rule_category": "EXCLUSION", "applies_to_products": "HEALTH"}], "summary": "Excluded", "reasoning": [{"finding": "The claim is excluded.", "evidence": "", "handbook_references": [{"chunk_id": "1.6"}]}]})
        self.assertEqual(result["final_decision"], "route_to_human")

    def test_settlement_needs_cited_coverage_and_settlement_evidence(self):
        result = decide(analysis={"recommendation": "settle", "retrieved_handbook_references": [{"chunk_id": "2.10", "rule_category": "DOCUMENT_REQUIREMENT", "applies_to_products": "MOTOR"}], "summary": "Settle", "reasoning": [{"finding": "Documents are present.", "evidence": "", "handbook_references": [{"chunk_id": "2.10"}]}]})
        self.assertEqual(result["final_decision"], "route_to_human")
