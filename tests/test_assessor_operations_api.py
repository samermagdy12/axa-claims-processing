import unittest

from fastapi import HTTPException

from app.main import assessor_review_queue, operations_overview, submit_assessor_decision
from app.schemas import AssessorDecisionRequest


class Result:
    def __init__(self, rows): self.rows = rows
    def mappings(self): return self
    def all(self): return self.rows


class ReadOnlyDb:
    def __init__(self, rows): self.rows = rows
    def execute(self, *args, **kwargs): return Result(self.rows)


class AssessorOperationsApiTests(unittest.TestCase):
    def test_human_review_claims_are_returned_in_queue(self):
        rows = [{"claim_id": "c-1", "claim_type": "Collision", "claimed_amount": 12000, "incident_date": "2026-01-01", "submission_date": "2026-01-02", "status": "UNDER_HUMAN_REVIEW", "customer_name": "Mona", "policy_number": "P-1", "product_line": "MOTOR", "final_decision": "route_to_human", "reason": "Amount limit", "risk_detected": True, "human_decision": None}]
        result = assessor_review_queue({"role_name": "Assessor"}, ReadOnlyDb(rows))
        self.assertEqual(result[0]["claim_id"], "c-1")
        self.assertEqual(result[0]["risk_level"], "HIGH")

    def test_operations_overview_is_read_only_aggregation(self):
        result = operations_overview({"role_name": "Operations"}, ReadOnlyDb([{"product_line": "MOTOR", "processed": 3, "approved": 1, "routed": 1, "rejected": 1, "risk_flagged": 1}]))
        self.assertEqual(result["product_lines"][0]["processed"], 3)

    def test_reject_and_override_require_reasons_before_database_work(self):
        with self.assertRaises(HTTPException) as rejected:
            submit_assessor_decision("c-1", AssessorDecisionRequest(action="reject"), {"role_name": "Assessor"}, None)
        self.assertEqual(rejected.exception.status_code, 422)
        with self.assertRaises(HTTPException) as override:
            submit_assessor_decision("c-1", AssessorDecisionRequest(action="override", reason="because"), {"role_name": "Assessor"}, None)
        self.assertEqual(override.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
