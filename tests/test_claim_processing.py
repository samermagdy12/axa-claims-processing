import unittest

from app.claim_processing import build_claim_processing_summary, check_cross_document_consistency, normalize_document_data, present_document_validation, validate_document


class ClaimProcessingTests(unittest.TestCase):
    def test_visual_slot_never_trusts_the_upload_slot_or_strategy(self):
        wrong = validate_document("Photos of Damage", "REPAIR ESTIMATE\nTotal Amount: EGP 5,000", {"total": 5000}, mime_type="application/pdf", processing_strategy="visual_evidence_preserved")
        self.assertFalse(wrong["validation_passed"])
        self.assertIn("not an image", wrong["reason"])
        uncertain = validate_document("Photos of Damage", "", {}, mime_type="image/jpeg", processing_strategy="visual_evidence_preserved")
        self.assertIsNone(uncertain["validation_passed"])
        self.assertTrue(uncertain["manual_review_required"])

    def test_visual_analysis_has_explicit_pass_fail_and_uncertain_thresholds(self):
        valid = validate_document("Photos of Damage", "", {"detected_document_type": "Photos of Damage", "content_matches_expected": True, "confidence": .95, "reason": "Vehicle collision damage is visible."}, mime_type="image/jpeg")
        self.assertTrue(valid["validation_passed"])
        invalid = validate_document("Photos of Damage", "", {"detected_document_type": "Driver's Licence", "content_matches_expected": False, "confidence": .95, "reason": "An ID card is visible."}, mime_type="image/jpeg")
        self.assertFalse(invalid["validation_passed"])
        unclear = validate_document("Photos of Damage", "", {"content_matches_expected": True, "confidence": .5}, mime_type="image/jpeg")
        self.assertIsNone(unclear["validation_passed"])

    def test_required_document_matching_uses_canonical_ids_not_display_punctuation(self):
        result = build_claim_processing_summary([{"document_type": "Driver's Licence", "is_required": True}], [{"document_id": "d", "document_type": "Driver’s   Licence", "validation": {"validation_passed": True}, "normalized_data": {"fields": {}}}])
        self.assertEqual(result["missing_documents"], [])

    def test_validation_detects_a_wrong_document_type(self):
        result = validate_document("Repair Estimate", "MEDICAL REPORT\nPatient: Mona Adel\nDiagnosis: Minor injury", {"patient_name": "Mona Adel", "diagnosis": "Minor injury"})
        self.assertFalse(result["validation_passed"])
        self.assertEqual(result["detected_document_type"], "Medical Report")

    def test_normalization_preserves_available_values_without_invention(self):
        normalized = normalize_document_data("Vehicle Registration", {"owner_name": "Mona Adel", "registration_number": "ABC-1234", "vehicle_make": "Toyota"})
        self.assertEqual(normalized["fields"]["full_name"], "Mona Adel")
        self.assertEqual(normalized["fields"]["registration_number"], "ABC-1234")
        self.assertIsNone(normalized["fields"]["claim_number"])

    def test_summary_reports_missing_invalid_and_conflicting_documents(self):
        required = [{"document_type": "Driver's Licence", "is_required": True}, {"document_type": "Vehicle Registration", "is_required": True}]
        documents = [{"document_id": "licence", "document_type": "Driver's Licence", "validation": {"validation_passed": True}, "normalized_data": {"fields": {"full_name": "Mona Adel", "registration_number": None}}}]
        incomplete = build_claim_processing_summary(required, documents)
        self.assertEqual(incomplete["outcome"], "incomplete")
        self.assertEqual(incomplete["missing_documents"], ["Vehicle Registration"])

        documents.append({"document_id": "registration", "document_type": "Vehicle Registration", "validation": {"validation_passed": False}, "normalized_data": {"fields": {"full_name": "Other Name", "registration_number": "ABC-1234"}}})
        invalid = build_claim_processing_summary(required, documents)
        self.assertEqual(invalid["outcome"], "invalid_document_detected")
        self.assertTrue(invalid["consistency"]["has_conflicts"])

    def test_complete_consistent_claim_is_ready(self):
        required = [{"document_type": "Member ID", "is_required": True}, {"document_type": "Medical Report", "is_required": True}]
        documents = [
            {"document_id": "member", "document_type": "Member ID", "validation": {"validation_passed": True}, "normalized_data": {"fields": {"full_name": "Mona Adel", "policy_number": "POL-88"}}},
            {"document_id": "medical", "document_type": "Medical Report", "validation": {"validation_passed": True}, "normalized_data": {"fields": {"full_name": "Mona Adel", "policy_number": "POL-88"}}},
        ]
        summary = build_claim_processing_summary(required, documents)
        self.assertEqual(summary["outcome"], "ready_for_processing")
        self.assertTrue(summary["complete"])

    def test_related_required_types_use_their_shared_validation_profile(self):
        result = validate_document("Itemised Hospital Invoice", "INVOICE\nSubtotal: EGP 100\nVAT: EGP 14\nTotal Amount: EGP 114", {"invoice_number": "INV-1", "total_amount": 114})
        self.assertTrue(result["validation_passed"])
        self.assertEqual(result["detected_document_type"], "Itemised Hospital Invoice")

    def test_uploaded_but_unextracted_document_requires_manual_review_not_missing(self):
        summary = build_claim_processing_summary(
            [{"document_type": "Member ID", "is_required": True}],
            [{"document_id": "member", "document_type": "Member ID", "validation": {"validation_passed": None}, "normalized_data": {"fields": {}}}],
        )
        self.assertEqual(summary["outcome"], "manual_review_required")
        self.assertEqual(summary["missing_documents"], [])

    def test_validation_presentation_is_safe_and_user_friendly(self):
        invalid = present_document_validation({"expected_document_type": "Driver's Licence", "detected_document_type": "Repair Estimate", "validation_passed": False})
        self.assertEqual(invalid["status"], "invalid")
        self.assertFalse(invalid["document_valid"])
        self.assertEqual(invalid["errors"], ["Expected: Driver's Licence", "Detected: Repair Estimate"])

        warning = present_document_validation({"expected_document_type": "Driver's Licence", "validation_passed": None, "reason": "Text could not be classified."})
        self.assertEqual(warning["status"], "warning")
        self.assertEqual(warning["warnings"], ["Text could not be classified."])

    def test_vehicle_make_and_make_model_are_compatible(self):
        result = check_cross_document_consistency([
            {"document_id": "a", "document_type": "Vehicle Registration", "normalized_data": {"fields": {"vehicle_information": "Toyota"}}},
            {"document_id": "b", "document_type": "Vehicle Registration", "normalized_data": {"fields": {"vehicle_information": {"make_model": "Toyota Corolla", "registration": "ABC-1234"}}}},
        ])
        self.assertFalse(result["has_conflicts"])

    def test_unrelated_document_expiry_dates_are_not_compared(self):
        result = check_cross_document_consistency([
            {"document_id": "licence", "document_type": "Driver's Licence", "normalized_data": {"fields": {"expiry_date": "2030-01-01"}}},
            {"document_id": "policy", "document_type": "Policy Certificate", "normalized_data": {"fields": {"expiry_date": "2026-12-31"}}},
        ])
        self.assertFalse(result["has_conflicts"])


if __name__ == "__main__":
    unittest.main()
