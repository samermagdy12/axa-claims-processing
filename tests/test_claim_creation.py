from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
import unittest

from fastapi import HTTPException
from pydantic import ValidationError

from app.main import create_claim
from app.schemas import ClaimCreateRequest


class Result:
    def __init__(self, value):
        self.value = value

    def mappings(self):
        return self

    def first(self):
        return self.value

    def one(self):
        return self.value


class FakeDatabase:
    def __init__(self, policy):
        self.policy = policy
        self.claim_id = uuid4()
        self.committed = False

    def execute(self, statement, params):
        sql = str(statement)
        if "SELECT policy_id, user_id, product_line" in sql:
            return Result(self.policy)
        if "INSERT INTO claims" in sql:
            return Result({"claim_id": self.claim_id, "policy_id": params["policy_id"], "claim_type": params["claim_type"], "incident_date": params["incident_date"], "submission_date": datetime(2026, 8, 25, 12), "claimed_amount": params["claimed_amount"], "description": params["description"], "status": "WAITING_FOR_DOCUMENTS"})
        if "INSERT INTO claim_required_documents" in sql:
            return Result({"claim_required_document_id": uuid4(), "document_type": params["document_type"], "is_required": True, "status": "MISSING"})
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class ClaimCreationTests(unittest.TestCase):
    def setUp(self):
        self.customer_id = uuid4()
        self.payload = ClaimCreateRequest(policy_id="POL-H-001", claim_type="Medication", incident_date=date(2026, 8, 1), claimed_amount=Decimal("125.50"), description="Medication prescribed after a consultation.")

    def test_creates_claim_linked_to_owned_policy_and_required_documents(self):
        db = FakeDatabase({"policy_id": "POL-H-001", "user_id": self.customer_id, "product_line": "HEALTH"})
        claim = create_claim(self.payload, {"user_id": self.customer_id, "role_name": "Customer"}, db)
        self.assertEqual(claim["policy_id"], "POL-H-001")
        self.assertEqual(claim["status"], "WAITING_FOR_DOCUMENTS")
        self.assertEqual([document["document_type"] for document in claim["required_documents"]], ["Prescription", "Pharmacy Invoice", "Member ID"])
        self.assertTrue(all(document["status"] == "MISSING" for document in claim["required_documents"]))
        self.assertTrue(db.committed)

    def test_rejects_claim_for_another_customers_policy(self):
        db = FakeDatabase({"policy_id": "POL-H-001", "user_id": uuid4(), "product_line": "HEALTH"})
        with self.assertRaises(HTTPException) as error:
            create_claim(self.payload, {"user_id": self.customer_id, "role_name": "Customer"}, db)
        self.assertEqual(error.exception.status_code, 403)

    def test_returns_not_found_for_unknown_policy(self):
        with self.assertRaises(HTTPException) as error:
            create_claim(self.payload, {"user_id": self.customer_id, "role_name": "Customer"}, FakeDatabase(None))
        self.assertEqual(error.exception.status_code, 404)

    def test_rejects_unsupported_claim_type_for_product_line(self):
        payload = ClaimCreateRequest(policy_id="POL-H-001", claim_type="Collision", incident_date=date(2026, 8, 1), claimed_amount=Decimal("125.50"), description="Collision details are long enough to be valid.")
        db = FakeDatabase({"policy_id": "POL-H-001", "user_id": self.customer_id, "product_line": "HEALTH"})
        with self.assertRaises(HTTPException) as error:
            create_claim(payload, {"user_id": self.customer_id, "role_name": "Customer"}, db)
        self.assertEqual(error.exception.status_code, 422)

    def test_accepts_each_canonical_motor_claim_type(self):
        for claim_type in ("Collision", "Fire", "Theft", "Third-Party", "Windscreen / Glass"):
            with self.subTest(claim_type=claim_type):
                payload = self.payload.model_copy(update={"policy_id": "POL-M-001", "claim_type": claim_type})
                db = FakeDatabase({"policy_id": "POL-M-001", "user_id": self.customer_id, "product_line": "MOTOR"})
                claim = create_claim(payload, {"user_id": self.customer_id, "role_name": "Customer"}, db)
                self.assertEqual(claim["claim_type"], claim_type)
                self.assertTrue(claim["required_documents"])

    def test_rejects_historical_accident_alias_for_new_motor_claims(self):
        payload = self.payload.model_copy(update={"policy_id": "POL-M-001", "claim_type": "Accident"})
        db = FakeDatabase({"policy_id": "POL-M-001", "user_id": self.customer_id, "product_line": "MOTOR"})
        with self.assertRaises(HTTPException) as error:
            create_claim(payload, {"user_id": self.customer_id, "role_name": "Customer"}, db)
        self.assertEqual(error.exception.status_code, 422)

    def test_rejects_invalid_claim_request_data(self):
        base = {"policy_id": "POL-H-001", "claim_type": "Medication", "incident_date": "2026-08-01", "claimed_amount": "1", "description": "A sufficiently detailed claim description."}
        invalid_values = [{**base, "policy_id": ""}, {**base, "claim_type": ""}, {**base, "incident_date": "not-a-date"}, {**base, "claimed_amount": "-1"}, {**base, "description": "too short"}]
        for values in invalid_values:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ClaimCreateRequest(**values)


if __name__ == "__main__":
    unittest.main()
