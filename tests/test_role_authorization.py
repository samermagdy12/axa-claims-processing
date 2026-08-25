from uuid import uuid4
import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from jose import jwt

from app.auth import ASSESSOR_ROLE, CUSTOMER_ROLE, OPERATIONS_ROLE, create_access_token, require_roles
from app.config import settings
from app.schemas import LoginRequest, RegisterRequest


class RoleAuthorizationTests(unittest.TestCase):
    def test_customer_registration_rejects_internal_role_input(self):
        payload = {
            "full_name": "Customer User",
            "email": "customer@example.com",
            "password": "secure-password",
            "national_id": "12345678901234",
        }
        self.assertEqual(RegisterRequest(**payload).model_dump()["national_id"], payload["national_id"])
        for role in (ASSESSOR_ROLE, OPERATIONS_ROLE):
            with self.subTest(role=role), self.assertRaises(ValidationError):
                RegisterRequest(**payload, role=role)

    def test_customer_cannot_access_internal_roles(self):
        customer = {"role_name": CUSTOMER_ROLE}
        for role in (ASSESSOR_ROLE, OPERATIONS_ROLE):
            with self.subTest(role=role), self.assertRaises(HTTPException) as error:
                require_roles(role)(customer)
            self.assertEqual(error.exception.status_code, 403)

    def test_internal_roles_only_access_their_own_area(self):
        self.assertEqual(require_roles(ASSESSOR_ROLE)({"role_name": ASSESSOR_ROLE})["role_name"], ASSESSOR_ROLE)
        self.assertEqual(require_roles(OPERATIONS_ROLE)({"role_name": OPERATIONS_ROLE})["role_name"], OPERATIONS_ROLE)
        with self.assertRaises(HTTPException) as error:
            require_roles(ASSESSOR_ROLE)({"role_name": OPERATIONS_ROLE})
        self.assertEqual(error.exception.status_code, 403)

    def test_existing_jwt_subject_authentication_format_is_preserved(self):
        user_id = uuid4()
        token = create_access_token(user_id)
        claims = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        self.assertEqual(claims["sub"], str(user_id))
        self.assertNotIn("role", claims)

    def test_controlled_internal_email_domain_can_sign_in(self):
        self.assertEqual(LoginRequest(email="assessor@axa.local", password="password").email, "assessor@axa.local")


if __name__ == "__main__":
    unittest.main()
