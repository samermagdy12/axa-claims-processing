from uuid import uuid4
import unittest

from fastapi import HTTPException
from pydantic import ValidationError

from app.main import get_my_policies, get_policy, register, verify_policies
from app.policy_import import DEFAULT_POLICY_SOURCE, import_policies, load_source_policies
from app.schemas import PolicyVerificationRequest, RegisterRequest


class Result:
    def __init__(self, value=None, rowcount=0):
        self.value = value
        self.rowcount = rowcount

    def mappings(self):
        return self

    def first(self):
        return self.value

    def one(self):
        return self.value

    def all(self):
        return self.value


class ImportDatabase:
    def __init__(self):
        self.customer_role = {"role_id": uuid4()}
        self.users = {}
        self.policies = {}
        self.committed = False

    def execute(self, statement, params=None):
        sql = str(statement)
        if "SELECT role_id FROM roles" in sql:
            return Result(self.customer_role)
        if "SELECT user_id FROM users WHERE national_id" in sql:
            return Result(self.users.get(params["national_id"]))
        if "INSERT INTO users" in sql:
            user = {"user_id": uuid4()}
            self.users[params["national_id"]] = user
            return Result(user)
        if "INSERT INTO user_roles" in sql:
            return Result()
        if "INSERT INTO policies" in sql:
            if params["policy_id"] in self.policies:
                return Result(rowcount=0)
            self.policies[params["policy_id"]] = dict(params)
            return Result(rowcount=1)
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.committed = True

    def rollback(self):
        raise AssertionError("Import should not roll back")


class AssociationDatabase:
    def __init__(self, owner_id, other_id):
        self.owner_id = owner_id
        self.other_id = other_id
        self.provisioned_user = {"user_id": owner_id, "email": "policy-29001011200345@policy-import.local", "status": "inactive"}
        self.updated_user = {"user_id": owner_id, "full_name": "Mona Adel", "email": "mona@example.com"}
        self.policies = [
            {"policy_id": "P-1001", "policy_number": "P-1001", "product_line": "HEALTH", "status": "ACTIVE", "start_date": "2025-01-10", "end_date": "2026-01-10", "annual_limit": 200000, "remaining_limit": 150000, "deductible": 250, "riders": []},
        ]

    def execute(self, statement, params=None):
        sql = str(statement)
        if "FROM policies p" in sql:
            return Result(self.policies if params["national_id"] == "29001011200345" else [])
        if "SELECT user_id FROM users WHERE email" in sql:
            return Result(None)
        if "SELECT user_id, email, status FROM users" in sql:
            return Result(self.provisioned_user)
        if "SELECT role_id FROM roles" in sql:
            return Result({"role_id": uuid4()})
        if "UPDATE users SET" in sql:
            return Result(self.updated_user)
        if "INSERT INTO user_roles" in sql:
            return Result()
        if "FROM policies WHERE user_id" in sql:
            return Result(self.policies if params["user_id"] == self.owner_id else [])
        if "FROM policies WHERE policy_id" in sql:
            return Result(self.policies[0] if params["user_id"] == self.owner_id and params["policy_id"] == "P-1001" else None)
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        pass

    def rollback(self):
        raise AssertionError("Registration should not roll back")


class PolicyImportTests(unittest.TestCase):
    def test_imports_the_source_dataset_and_is_idempotent(self):
        db = ImportDatabase()
        first = import_policies(db, DEFAULT_POLICY_SOURCE)
        second = import_policies(db, DEFAULT_POLICY_SOURCE)

        self.assertEqual(first.source_count, 150)
        self.assertEqual(first.imported_policies, 150)
        self.assertEqual(second.imported_policies, 0)
        self.assertEqual(len(db.policies), 150)
        self.assertIn("P-1001", db.policies)
        self.assertEqual(db.policies["P-1001"]["product_line"], "HEALTH")

    def test_registered_policy_holder_receives_only_own_policies(self):
        owner_id, other_id = uuid4(), uuid4()
        db = AssociationDatabase(owner_id, other_id)
        session = register(RegisterRequest(full_name="Mona Adel", email="mona@example.com", password="secure-password", national_id="29001011200345"), db)

        self.assertEqual(session["user"]["user_id"], owner_id)
        self.assertEqual([policy["policy_id"] for policy in get_my_policies({"user_id": owner_id}, db)], ["P-1001"])
        self.assertEqual(get_my_policies({"user_id": other_id}, db), [])
        with self.assertRaises(HTTPException) as error:
            get_policy("P-1001", {"user_id": other_id}, db)
        self.assertEqual(error.exception.status_code, 403)

    def test_verifies_only_policies_matching_the_provided_national_id(self):
        owner_id, other_id = uuid4(), uuid4()
        db = AssociationDatabase(owner_id, other_id)

        policies = verify_policies(PolicyVerificationRequest(national_id="29001011200345"), db)
        no_policies = verify_policies(PolicyVerificationRequest(national_id="29999999999999"), db)

        self.assertEqual([policy["policy_id"] for policy in policies], ["P-1001"])
        self.assertEqual(no_policies, [])
        with self.assertRaises(ValidationError):
            PolicyVerificationRequest(national_id="")

    def test_registration_rejects_a_national_id_without_imported_policies(self):
        db = AssociationDatabase(uuid4(), uuid4())

        with self.assertRaises(HTTPException) as error:
            register(
                RegisterRequest(
                    full_name="No Policy",
                    email="no-policy@example.com",
                    password="secure-password",
                    national_id="29999999999999",
                ),
                db,
            )

        self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
