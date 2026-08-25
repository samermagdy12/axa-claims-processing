from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import unittest

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.auth import get_current_user
from app.config import settings
from app.main import get_claim, get_my_claims


class Result:
    def __init__(self, value):
        self.value = value

    def mappings(self):
        return self

    def all(self):
        return self.value

    def first(self):
        return self.value


class ClaimsDatabase:
    def __init__(self, owner_id, other_id):
        self.owner_id = owner_id
        self.other_id = other_id
        self.owner_claim_id = uuid4()
        self.other_claim_id = uuid4()

    def _claim(self, claim_id, policy_id):
        return {
            "claim_id": claim_id, "policy_id": policy_id, "policy_number": policy_id,
            "product_line": "MOTOR", "claim_type": "Collision", "incident_date": date(2026, 6, 18),
            "submission_date": datetime(2026, 7, 1), "claimed_amount": Decimal("7500.00"),
            "description": "Rear bumper damage", "status": "WAITING_FOR_DOCUMENTS",
        }

    def execute(self, statement, params=None):
        sql = str(statement)
        if "FROM claims c" in sql:
            user_id = params["user_id"]
            if "claim_id" not in params:
                return Result([self._claim(self.owner_claim_id, "P-1001")] if user_id == self.owner_id else [self._claim(self.other_claim_id, "P-2001")] if user_id == self.other_id else [])
            if str(params["claim_id"]) == str(self.owner_claim_id) and user_id == self.owner_id:
                return Result(self._claim(self.owner_claim_id, "P-1001"))
            if str(params["claim_id"]) == str(self.other_claim_id) and user_id == self.other_id:
                return Result(self._claim(self.other_claim_id, "P-2001"))
            return Result(None)
        raise AssertionError(f"Unexpected SQL: {sql}")


class CustomerClaimAccessTests(unittest.TestCase):
    def test_expired_token_is_rejected(self):
        expired_token = jwt.encode(
            {"sub": str(uuid4()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with self.assertRaises(HTTPException) as error:
            get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token), ClaimsDatabase(uuid4(), uuid4()))
        self.assertEqual(error.exception.status_code, 401)

    def test_claims_are_scoped_to_the_authenticated_users_policies(self):
        owner_id, other_id = uuid4(), uuid4()
        db = ClaimsDatabase(owner_id, other_id)

        self.assertEqual([claim["policy_id"] for claim in get_my_claims({"user_id": owner_id}, db)], ["P-1001"])
        self.assertEqual([claim["policy_id"] for claim in get_my_claims({"user_id": other_id}, db)], ["P-2001"])

        with self.assertRaises(HTTPException) as error:
            get_claim(str(db.other_claim_id), {"user_id": owner_id}, db)
        self.assertEqual(error.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
