"""Document validation and claim workflow summaries built from existing extractions."""
from __future__ import annotations

from collections import defaultdict
import re
from typing import Any


VISUAL_EVIDENCE_DOCUMENT_TYPES = {"Photos of Damage", "Spare Key"}
_TYPE_HINTS = {
    "Driver's Licence": ("driver", "licence", "license", "date of birth"),
    "Vehicle Registration": ("vehicle registration", "registration number", "vin", "chassis"),
    "Medical Report": ("medical report", "clinical", "diagnosis", "patient"),
    "Repair Estimate": ("repair estimate", "estimate number", "garage", "repair shop"),
    "Police Report": ("police report", "report number", "incident"),
    "Itemised Invoice": ("invoice", "subtotal", "total amount", "vat"),
    "Member ID": ("member id", "member number", "policy number"),
}
_FIELD_ALIASES = {
    "full_name": ("full_name", "name", "patient_name", "member_name", "owner_name", "customer_name", "insured_name"),
    "policy_number": ("policy_number", "policy_no"),
    "claim_number": ("claim_number", "claim_reference", "claim_no"),
    "licence_number": ("licence_number", "license_number"),
    "registration_number": ("registration_number", "plate_number"),
    "vehicle_information": ("vehicle_information", "vehicle", "vehicle_make", "vehicle_model"),
    "issue_date": ("issue_date", "issued_date", "registration_issue_date"),
    "expiry_date": ("expiry_date", "registration_expiry_date"),
    "amount": ("total", "total_amount", "total_estimated_repair_cost", "claimed_amount"),
}


def validate_document(expected_document_type: str, raw_text: str, structured_data: dict[str, Any] | None) -> dict[str, Any]:
    if expected_document_type in VISUAL_EVIDENCE_DOCUMENT_TYPES:
        return {"expected_document_type": expected_document_type, "detected_document_type": expected_document_type, "validation_passed": True, "confidence": None, "reason": "Visual evidence is preserved without document-type classification."}
    haystack = " ".join((raw_text or "", " ".join(str(key).replace("_", " ") for key in (structured_data or {})))).lower()
    scores = {document_type: sum(hint in haystack for hint in hints) for document_type, hints in _TYPE_HINTS.items()}
    detected_type, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        return {"expected_document_type": expected_document_type, "detected_document_type": None, "validation_passed": None, "confidence": None, "reason": "The extracted content does not provide reliable document-type evidence; manual review may be required."}
    expected_profile = _document_profile(expected_document_type)
    expected_score = scores.get(expected_profile, 0) if expected_profile else 0
    passed = detected_type == expected_profile and expected_score > 0
    return {"expected_document_type": expected_document_type, "detected_document_type": expected_document_type if passed else detected_type, "validation_passed": passed, "confidence": min(1.0, score / 3), "reason": "Document content is consistent with the expected upload field." if passed else f"Document content appears to be {detected_type}, not {expected_document_type}."}


def normalize_document_data(document_type: str, structured_data: dict[str, Any] | None) -> dict[str, Any]:
    data = structured_data if isinstance(structured_data, dict) else {}
    normalized: dict[str, Any] = {"document_type": document_type, "fields": {}}
    for canonical, aliases in _FIELD_ALIASES.items():
        value = next((data[key] for key in aliases if data.get(key) not in (None, "", [], {})), None)
        normalized["fields"][canonical] = value
    return normalized


def check_cross_document_consistency(documents: list[dict[str, Any]]) -> dict[str, Any]:
    checks = []
    for field in _FIELD_ALIASES:
        values: dict[str, list[str]] = defaultdict(list)
        for document in documents:
            value = ((document.get("normalized_data") or {}).get("fields") or {}).get(field)
            if value in (None, "", [], {}):
                continue
            values[_comparison_value(value)].append(str(document.get("document_id") or document.get("document_type") or "unknown"))
        conflict = len(values) > 1
        checks.append({"field": field, "values": [{"value": value, "document_ids": ids} for value, ids in values.items()], "matches": None if len(values) < 2 else not conflict, "conflict": conflict})
    conflicts = [check for check in checks if check["conflict"]]
    return {"checks": checks, "has_conflicts": bool(conflicts), "conflicts": conflicts}


def build_claim_processing_summary(required_documents: list[dict[str, Any]], documents: list[dict[str, Any]]) -> dict[str, Any]:
    required_types = [item["document_type"] for item in required_documents if item.get("is_required", True)]
    uploaded_types = [item.get("document_type") for item in documents]
    missing = [document_type for document_type in required_types if document_type not in uploaded_types]
    duplicates = sorted({document_type for document_type in uploaded_types if document_type and uploaded_types.count(document_type) > 1})
    invalid = [item for item in documents if (item.get("validation") or {}).get("validation_passed") is False]
    consistency = check_cross_document_consistency(documents)
    if invalid:
        outcome, manual_review = "invalid_document_detected", True
    elif missing:
        outcome, manual_review = "incomplete", False
    elif consistency["has_conflicts"]:
        outcome, manual_review = "conflicting_information", True
    elif any((item.get("validation") or {}).get("validation_passed") is None for item in documents if item.get("document_type") not in VISUAL_EVIDENCE_DOCUMENT_TYPES):
        outcome, manual_review = "manual_review_required", True
    else:
        outcome, manual_review = "ready_for_processing", False
    return {"outcome": outcome, "complete": not missing, "manual_review_required": manual_review, "required_documents": required_types, "uploaded_documents": uploaded_types, "missing_documents": missing, "invalid_documents": invalid, "duplicate_documents": duplicates, "consistency": consistency}


def _comparison_value(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def _document_profile(document_type: str) -> str | None:
    if document_type in _TYPE_HINTS:
        return document_type
    lowered = document_type.casefold()
    if "invoice" in lowered or "receipt" in lowered:
        return "Itemised Invoice"
    if "medical" in lowered or "physician" in lowered:
        return "Medical Report"
    if "police" in lowered:
        return "Police Report"
    return None
