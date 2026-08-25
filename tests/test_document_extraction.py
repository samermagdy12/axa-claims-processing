import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
import unittest

from fastapi import HTTPException
from docx import Document
from PIL import Image

from app.document_extraction import DocumentExtractionError, extract_document_content
from app.main import extract_claim_document


class Result:
    def __init__(self, value):
        self.value = value

    def mappings(self):
        return self

    def first(self):
        return self.value

    def one(self):
        return self.value


class ExtractionDatabase:
    def __init__(self, owner_id, upload_root):
        self.owner_id = owner_id
        self.claim_id = uuid4()
        self.document_id = uuid4()
        self.document = {
            "document_id": self.document_id,
            "claim_id": self.claim_id,
            "document_type": "Repair Estimate",
            "document_url": "claims/test/estimate.txt",
            "original_file_name": "estimate.txt",
            "mime_type": "text/plain",
        }
        destination = upload_root / self.document["document_url"]
        destination.parent.mkdir(parents=True)
        destination.write_text("Repair estimate: EGP 7,500", encoding="utf-8")
        self.extraction = None
        self.committed = False

    def execute(self, statement, params=None):
        sql = str(statement)
        if "SELECT c.claim_id, p.user_id" in sql:
            return Result({"claim_id": self.claim_id, "user_id": self.owner_id} if str(params["claim_id"]) == str(self.claim_id) else None)
        if "FROM claim_documents WHERE document_id" in sql:
            return Result(self.document if str(params["document_id"]) == str(self.document_id) else None)
        if "FROM claim_extractions WHERE claim_id" in sql:
            return Result(self.extraction)
        if "INSERT INTO claim_extractions" in sql:
            self.extraction = {
                "extraction_id": uuid4(), "claim_id": self.claim_id,
                "extracted_data": json.loads(params["extracted_data"]),
                "extraction_confidence": params["extraction_confidence"],
                "extracted_at": datetime(2026, 8, 25, 12),
            }
            return Result(self.extraction)
        if "INSERT INTO audit_logs" in sql:
            return Result(None)
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class DocumentExtractionTests(unittest.TestCase):
    def test_extracts_native_docx_text(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "estimate.docx"
            document = Document()
            document.add_paragraph("Garage repair estimate: EGP 7,500")
            document.save(path)
            result = extract_document_content(path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "Repair Estimate")
        self.assertEqual(result.strategy, "native_docx_text")
        self.assertIn("EGP 7,500", result.text)
        self.assertEqual(result.confidence, 1.0)

    def test_ocr_extracts_text_from_the_documented_sample_image(self):
        sample = Path(__file__).resolve().parents[1] / "data" / "AXA_capstone_data" / "sample_documents" / "CLM-001.jpg"
        result = extract_document_content(sample, "image/jpeg", "Repair Estimate")
        self.assertEqual(result.strategy, "image_ocr")
        self.assertIn("CLM-001", result.text)
        self.assertGreater(result.confidence or 0, 0)

    def test_ocr_extracts_text_from_a_scanned_pdf(self):
        sample = Path(__file__).resolve().parents[1] / "data" / "AXA_capstone_data" / "sample_documents" / "CLM-001.jpg"
        with TemporaryDirectory() as directory:
            path = Path(directory) / "scan.pdf"
            with Image.open(sample) as image:
                image.convert("RGB").save(path, "PDF")
            result = extract_document_content(path, "application/pdf", "Repair Estimate")
        self.assertEqual(result.strategy, "scanned_pdf_ocr")
        self.assertIn("CLM-001", result.text)

    def test_visual_evidence_is_preserved_without_misrepresenting_ocr(self):
        result = extract_document_content(Path("photo.jpg"), "image/jpeg", "Photos of Damage")
        self.assertEqual(result.strategy, "visual_evidence_preserved")
        self.assertEqual(result.text, "")
        self.assertIsNone(result.confidence)

    def test_rejects_unsupported_files(self):
        with self.assertRaises(DocumentExtractionError):
            extract_document_content(Path("estimate.xlsx"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Repair Estimate")

    def test_authorized_processing_links_extraction_to_document_and_is_idempotent(self):
        owner_id = uuid4()
        with TemporaryDirectory() as directory, patch("app.main.settings.UPLOAD_DIR", directory):
            db = ExtractionDatabase(owner_id, Path(directory))
            first = extract_claim_document(str(db.claim_id), str(db.document_id), {"user_id": owner_id, "role_name": "Customer"}, db)
            second = extract_claim_document(str(db.claim_id), str(db.document_id), {"user_id": owner_id, "role_name": "Customer"}, db)
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(first["document_id"], str(db.document_id))
        self.assertEqual(db.extraction["extracted_data"]["document_id"], str(db.document_id))
        self.assertEqual(db.extraction["extracted_data"]["extracted_text"], "Repair estimate: EGP 7,500")
        self.assertTrue(db.committed)

    def test_rejects_another_customers_claim_and_missing_files(self):
        owner_id, other_id = uuid4(), uuid4()
        with TemporaryDirectory() as directory, patch("app.main.settings.UPLOAD_DIR", directory):
            db = ExtractionDatabase(owner_id, Path(directory))
            with self.assertRaises(HTTPException) as unauthorized:
                extract_claim_document(str(db.claim_id), str(db.document_id), {"user_id": other_id, "role_name": "Customer"}, db)
            self.assertEqual(unauthorized.exception.status_code, 403)
            (Path(directory) / db.document["document_url"]).unlink()
            with self.assertRaises(HTTPException) as missing:
                extract_claim_document(str(db.claim_id), str(db.document_id), {"user_id": owner_id, "role_name": "Customer"}, db)
            self.assertEqual(missing.exception.status_code, 409)
            self.assertIsNone(db.extraction)

    def test_extraction_failure_does_not_create_a_record(self):
        owner_id = uuid4()
        with TemporaryDirectory() as directory, patch("app.main.settings.UPLOAD_DIR", directory):
            db = ExtractionDatabase(owner_id, Path(directory))
            with patch("app.main.extract_document_content", side_effect=DocumentExtractionError("OCR could not read the document")):
                with self.assertRaises(HTTPException) as failed:
                    extract_claim_document(str(db.claim_id), str(db.document_id), {"user_id": owner_id, "role_name": "Customer"}, db)
        self.assertEqual(failed.exception.status_code, 422)
        self.assertIsNone(db.extraction)


if __name__ == "__main__":
    unittest.main()
