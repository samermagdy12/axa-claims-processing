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
from app.structured_extraction import extract_structured_data


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
    def test_structures_driver_licence_fields_and_normalizes_dates(self):
        data = extract_structured_data("Driver's Licence", """SOUTH CAROLINA
Name: SAMPLE CAROLINE
Licence Number: 1234567890
DOB: 08/27/2000
Address: 813 MAIN STREET, COLUMBIA, SC 29201
Class: C
Restrictions: NONE
Issue Date: 08/27/2025
Expiry Date: 08/27/2033""")
        self.assertEqual(data["full_name"], "SAMPLE CAROLINE")
        self.assertEqual(data["licence_number"], "1234567890")
        self.assertEqual(data["date_of_birth"], "2000-08-27")
        self.assertEqual(data["expiry_date"], "2033-08-27")
        self.assertEqual(data["issuing_authority"], "South Carolina")

    def test_structures_vehicle_registration_and_repair_estimate(self):
        registration = extract_structured_data("Vehicle Registration", """Owner: Mona Adel
Registration Number: ABC-1234
Plate Number: ABC-1234
Make: Toyota
Model: Corolla
Year: 2022
VIN: 1HGCM82633A004352
Registration Expiry: 2027-06-18""")
        self.assertEqual(registration["owner_name"], "Mona Adel")
        self.assertEqual(registration["model_year"], 2022)
        self.assertEqual(registration["registration_expiry_date"], "2027-06-18")

        estimate = extract_structured_data("Repair Estimate", """Garage: ABC Garage
Estimate Number: EST-102
Estimate Date: 2026-06-18
Customer: Mona Adel
Vehicle: Toyota Corolla
Damage: rear bumper deformation, trunk lid creasing
- Rear bumper replacement EGP 2850
- Paint work EGP 4650
Total Estimated: EGP 7,500""")
        self.assertEqual(estimate["garage_name"], "ABC Garage")
        self.assertEqual(estimate["issued_date"], "2026-06-18")
        self.assertEqual(estimate["total_estimated_repair_cost"], 7500.0)
        self.assertEqual(estimate["currency"], "EGP")
        self.assertEqual(len(estimate["repair_items"]), 0)

    def test_repair_estimate_label_value_layout_is_complete_and_never_uses_titles(self):
        data = extract_structured_data("Repair Estimate", """ABC Garage
Vehicle Repair Estimate

Estimate No.
EST-2026-0618

Issued
18 June 2026

Customer
Mona Adel

Vehicle
Toyota Corolla - 2022

Registration
ABC-1234

Claim reference
AXA-MTR-2026-00421

Damage assessment
Inspection found rear-end collision damage: rear bumper deformation, trunk lid creasing, and a cracked right tail lamp. The vehicle is safe to tow but repairs are required before normal use.

Estimated repair items

Item | Parts (EGP) | Labour (EGP) | Total (EGP)
Rear bumper cover replacement | 2,850 | 900 | 3,750
Trunk lid repair and paint | 1,250 | 1,100 | 2,350
Right tail lamp assembly | 980 | 120 | 1,100
Paint materials and alignment | 0 | 300 | 300

TOTAL ESTIMATED REPAIR COST
7,500

This estimate is valid for 30 days and is provided for insurance claim assessment.""")
        self.assertEqual(data["garage_name"], "ABC Garage")
        self.assertEqual(data["estimate_number"], "EST-2026-0618")
        self.assertEqual(data["issued_date"], "2026-06-18")
        self.assertEqual(data["customer_name"], "Mona Adel")
        self.assertEqual(data["vehicle"]["make_model"], "Toyota Corolla")
        self.assertEqual(data["vehicle"]["year"], 2022)
        self.assertEqual(data["registration_number"], "ABC-1234")
        self.assertEqual(data["claim_reference"], "AXA-MTR-2026-00421")
        self.assertEqual(data["total_estimated_repair_cost"], 7500.0)
        self.assertEqual(len(data["repair_items"]), 4)
        self.assertIn("rear-end collision damage", data["damage_description"])
        self.assertNotEqual(data["damage_description"], "assessment")
        self.assertNotEqual(data["vehicle"], "Repair Estimate")
        self.assertNotEqual(data["garage_name"], "Vehicle Repair Estimate")

    def test_visual_and_other_dedicated_parsers_do_not_invent_facts(self):
        visual = extract_structured_data("Photos of Damage", "")
        self.assertEqual(visual, {"visual_evidence_preserved": True, "structured_extraction_available": False})
        receipt = extract_structured_data("Receipts for Essentials", "Invoice Number\nREC-42\nTotal Amount\nEGP 250")
        self.assertEqual(receipt["invoice_number"], "REC-42")
        self.assertEqual(receipt["total_amount"], 250.0)
        self.assertIsNone(receipt["provider_name"])

    def test_vehicle_registration_uses_full_labels_and_validates_vin(self):
        registration = extract_structured_data("Vehicle Registration", """Registration Number
ABC-1234
Vehicle Identification Number (VIN)
JTDBR32E720123456
Owner Name
Mona Adel
Vehicle Make
Toyota
Vehicle Model
Corolla
Model Year
2022
Registration Expiry Date
31 May 2027""")
        self.assertEqual(registration["registration_number"], "ABC-1234")
        self.assertEqual(registration["vin"], "JTDBR32E720123456")
        self.assertEqual(registration["owner_name"], "Mona Adel")
        self.assertEqual(registration["vehicle_make"], "Toyota")
        self.assertEqual(registration["vehicle_model"], "Corolla")
        self.assertEqual(registration["registration_expiry_date"], "2027-05-31")

    def test_police_report_and_licence_validate_fields_and_preserve_narrative(self):
        police = extract_structured_data("Police Report", """REPORT NUMBER
PR-12345
INCIDENT DATE
18 June 2026
INCIDENT TIME
14:35
LOCATION
Nasr City, Cairo
DRIVER
Mona Adel
VEHICLE
Toyota Corolla - Registration ABC-1234
INCIDENT SUMMARY
Vehicle was hit from behind while stopped at a traffic signal.""")
        self.assertEqual(police["report_number"], "PR-12345")
        self.assertEqual(police["incident_date"], "2026-06-18")
        self.assertEqual(police["incident_time"], "14:35")
        self.assertEqual(police["incident_location"], "Nasr City, Cairo")
        self.assertEqual(police["driver_name"], "Mona Adel")
        self.assertEqual(police["registration_number"], "ABC-1234")
        self.assertIn("hit from behind", police["raw_narrative"])
        licence = extract_structured_data("Driver's Licence", "Class\n9aEnd\nLicence Number\nDL-10001")
        self.assertIsNone(licence["vehicle_class"])
        self.assertEqual(licence["licence_number"], "DL-10001")

    def test_ocr_style_labels_and_merged_values_use_the_same_document_parsers(self):
        police = extract_structured_data("Police Report", """POLICEREPORT
REPORTNUMBER
PR-12345
INCIDENTDATE
18 June 2026
INCIDENTTIME
14:35
LOCATION
Nasr City, Cairo
DRIVER
Mona Adel
VEHICLE
Toyota Corolla - Registration ABC-1234
INCIDENTSUMMARY
Vehicle was hit from behind while stopped at a traffic signal.
OFFICER NOTE
No injuries were reported at the scene.""", "image_ocr")
        self.assertEqual(police["report_number"], "PR-12345")
        self.assertEqual(police["incident_date"], "2026-06-18")
        self.assertEqual(police["incident_time"], "14:35")
        self.assertEqual(police["registration_number"], "ABC-1234")
        self.assertFalse(police["injuries_reported"])
        self.assertIn("No injuries", police["officer_notes"])

        licence = extract_structured_data("Driver's Licence", """A1234567890
3Date of bith
01/01/2000
F
8123MAINSTREET
COLUMBIA,SC29201
Class
9aEnd
D
NONE
4alssue
4bExp
08/27/202508/27/2033""", "scanned_pdf_ocr")
        self.assertEqual(licence["licence_number"], "A1234567890")
        self.assertEqual(licence["date_of_birth"], "2000-01-01")
        self.assertEqual(licence["sex"], "F")
        self.assertEqual(licence["vehicle_class"], "D")
        self.assertEqual(licence["issue_date"], "2025-08-27")
        self.assertEqual(licence["expiry_date"], "2033-08-27")

        registration = extract_structured_data("Vehicle Registration", "Engine Capacity\n1800 CC")
        self.assertEqual(registration["engine_capacity_cc"], 1800)

    def test_every_requirement_document_type_has_an_intentional_parser_or_visual_result(self):
        from app.claim_requirements import REQUIRED_DOCUMENTS

        document_types = {document_type for claim_types in REQUIRED_DOCUMENTS.values() for documents in claim_types.values() for document_type in documents}
        self.assertEqual(len(document_types), 28)
        for document_type in document_types:
            with self.subTest(document_type=document_type):
                text = "Garage: Example Garage\nEstimate Number: EST-100" if document_type == "Repair Estimate" else "Reference: REF-100\nDate: 18 June 2026"
                result = extract_structured_data(document_type, text)
                if document_type in {"Photos of Damage", "Spare Key"}:
                    self.assertEqual(result["visual_evidence_preserved"], True)
                    self.assertEqual(result["structured_extraction_available"], False)
                else:
                    self.assertNotEqual(result, {})

    def test_structures_invoice_medical_police_and_member_id_without_fabrication(self):
        invoice = extract_structured_data("Itemised Invoice", """Provider: Cairo Clinic
Invoice Number: INV-77
Invoice Date: 2026-06-18
Subtotal: EGP 1000
VAT: EGP 140
Total Amount: EGP 1140""")
        self.assertEqual(invoice["total_amount"], 1140.0)
        self.assertEqual(invoice["currency"], "EGP")
        medical = extract_structured_data("Medical Report", "Patient: Layla Mostafa\nDiagnosis: Sprained ankle\nReport Date: 2026-06-18")
        self.assertEqual(medical["diagnosis"], "Sprained ankle")
        police = extract_structured_data("Police Report", "Report Number: PR-100\nIncident Date: 2026-06-18\nIncident Location: Nasr City")
        self.assertEqual(police["report_number"], "PR-100")
        member = extract_structured_data("Member ID", "Member Name: Layla Mostafa\nMember ID: MID-123\nPolicy Number: POL-88\nExpiry: 2027-06-18")
        self.assertEqual(member["member_id"], "MID-123")
        self.assertEqual(extract_structured_data("Repair Estimate", "unreadable OCR fragments")["structured_extraction_available"], False)
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
        self.assertEqual(db.extraction["extracted_data"]["raw_extraction"]["text"], "Repair estimate: EGP 7,500")
        self.assertEqual(db.extraction["extracted_data"]["structured_data"]["structured_extraction_available"], False)
        self.assertEqual(first["raw_text"], "Repair estimate: EGP 7,500")
        self.assertEqual(first["structured_data"]["structured_extraction_available"], False)
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
