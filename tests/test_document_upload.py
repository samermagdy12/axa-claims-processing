import asyncio
from datetime import datetime
from io import BytesIO
from tempfile import TemporaryDirectory
from uuid import uuid4
import unittest
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.main import upload_claim_document


class Result:
    def __init__(self, value):
        self.value = value

    def mappings(self):
        return self

    def first(self):
        return self.value

    def one(self):
        return self.value

    def scalar_one(self):
        return self.value


class UploadDatabase:
    def __init__(self, owner_id, other_id):
        self.owner_id = owner_id
        self.other_id = other_id
        self.claim_id = uuid4()
        self.requirements = {
            "Driver's Licence": {"claim_required_document_id": uuid4(), "document_type": "Driver's Licence", "is_required": True, "status": "MISSING"},
            "Vehicle Registration": {"claim_required_document_id": uuid4(), "document_type": "Vehicle Registration", "is_required": True, "status": "MISSING"},
        }
        self.documents = []
        self.claim_status = "WAITING_FOR_DOCUMENTS"
        self.committed = False

    def execute(self, statement, params=None):
        sql = str(statement)
        if "SELECT c.claim_id, p.user_id" in sql:
            return Result({"claim_id": self.claim_id, "user_id": self.owner_id} if str(params["claim_id"]) == str(self.claim_id) else None)
        if "FROM claim_required_documents WHERE claim_id" in sql and "document_type" in sql:
            return Result(self.requirements.get(params["document_type"]))
        if "INSERT INTO claim_documents" in sql:
            document = {"document_id": uuid4(), "claim_id": self.claim_id, "document_type": params["document_type"], "original_file_name": params["original_file_name"], "mime_type": params["mime_type"], "file_size_bytes": params["file_size_bytes"], "uploaded_at": datetime(2026, 8, 25, 12)}
            self.documents.append(document)
            return Result(document)
        if "UPDATE claim_required_documents" in sql:
            requirement = next(item for item in self.requirements.values() if item["claim_required_document_id"] == params["required_document_id"])
            requirement["status"] = "UPLOADED"
            return Result(requirement)
        if "SELECT COUNT(*)" in sql:
            return Result(sum(item["status"] == "MISSING" for item in self.requirements.values()))
        if "UPDATE claims SET status" in sql:
            self.claim_status = params["status"]
            return Result(None)
        if "INSERT INTO audit_logs" in sql:
            return Result(None)
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def upload_file(name: str, content: bytes) -> UploadFile:
    return UploadFile(file=BytesIO(content), filename=name, headers=Headers({"content-type": "application/pdf"}))


class DocumentUploadTests(unittest.TestCase):
    def setUp(self):
        self.owner_id, self.other_id = uuid4(), uuid4()
        self.db = UploadDatabase(self.owner_id, self.other_id)

    def upload(self, document_type, file, user_id=None):
        return asyncio.run(upload_claim_document(str(self.db.claim_id), document_type, file, {"user_id": user_id or self.owner_id, "role_name": "Customer"}, self.db))

    def test_uploads_each_required_document_and_updates_claim_status_when_complete(self):
        with TemporaryDirectory() as upload_dir, patch("app.main.settings.UPLOAD_DIR", upload_dir):
            first = self.upload("Driver's Licence", upload_file("../licence.pdf", b"licence"))
            second = self.upload("Vehicle Registration", upload_file("registration.pdf", b"registration"))

            self.assertEqual(first["required_document"]["status"], "UPLOADED")
            self.assertEqual(first["claim_status"], "WAITING_FOR_DOCUMENTS")
            self.assertEqual(second["claim_status"], "PROCESSING")
            self.assertEqual(self.db.claim_status, "PROCESSING")
            self.assertEqual([document["document_type"] for document in self.db.documents], ["Driver's Licence", "Vehicle Registration"])
            self.assertEqual(self.db.documents[0]["original_file_name"], "licence.pdf")
            self.assertTrue(any(path.is_file() for path in __import__("pathlib").Path(upload_dir).rglob("*")))

    def test_rejects_another_customers_claim_and_invalid_document_type(self):
        with TemporaryDirectory() as upload_dir, patch("app.main.settings.UPLOAD_DIR", upload_dir):
            with self.assertRaises(HTTPException) as unauthorized:
                self.upload("Driver's Licence", upload_file("licence.pdf", b"licence"), self.other_id)
            self.assertEqual(unauthorized.exception.status_code, 403)

            with self.assertRaises(HTTPException) as invalid_document:
                self.upload("Not Required", upload_file("other.pdf", b"other"))
            self.assertEqual(invalid_document.exception.status_code, 422)
            self.assertEqual(self.db.documents, [])

    def test_does_not_replace_an_uploaded_required_document(self):
        with TemporaryDirectory() as upload_dir, patch("app.main.settings.UPLOAD_DIR", upload_dir):
            self.upload("Driver's Licence", upload_file("licence.pdf", b"licence"))
            with self.assertRaises(HTTPException) as duplicate_document:
                self.upload("Driver's Licence", upload_file("replacement.pdf", b"replacement"))
            self.assertEqual(duplicate_document.exception.status_code, 409)
            self.assertEqual(len(self.db.documents), 1)

    def test_rejects_missing_claim_and_empty_file_without_creating_a_document(self):
        with TemporaryDirectory() as upload_dir, patch("app.main.settings.UPLOAD_DIR", upload_dir):
            with self.assertRaises(HTTPException) as missing_claim:
                asyncio.run(upload_claim_document(str(uuid4()), "Driver's Licence", upload_file("licence.pdf", b"licence"), {"user_id": self.owner_id, "role_name": "Customer"}, self.db))
            self.assertEqual(missing_claim.exception.status_code, 404)

            with self.assertRaises(HTTPException) as empty_file:
                self.upload("Driver's Licence", upload_file("licence.pdf", b""))
            self.assertEqual(empty_file.exception.status_code, 422)
            self.assertEqual(self.db.documents, [])


if __name__ == "__main__":
    unittest.main()
