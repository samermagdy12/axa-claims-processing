"""Validated document-type parsers layered over immutable raw extraction text."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Callable


VISUAL_EVIDENCE_DOCUMENT_TYPES = {"Photos of Damage", "Spare Key"}
_CURRENCIES = "EGP|USD|EUR|GBP"
_YEAR = r"(?:19|20)\d{2}"
_COMMON_LABELS = {
    "registration number", "vehicle identification number vin", "owner name", "vehicle make", "vehicle model",
    "model year", "registration expiry date", "report number", "incident date", "incident time", "location",
    "driver", "vehicle", "incident summary", "customer", "estimate number", "damage assessment",
    "name", "full name", "licence number", "license number", "date of birth", "issue date", "expiry date",
    "address", "vehicle class", "class", "restrictions", "member id", "policy number", "invoice number",
    "invoice date", "total amount", "subtotal", "tax", "vat", "patient", "diagnosis", "treatment",
}


def extract_structured_data(document_type: str, raw_text: str) -> dict:
    """Conservatively interpret raw text without changing the raw source."""
    if document_type in VISUAL_EVIDENCE_DOCUMENT_TYPES:
        return {"visual_evidence_preserved": True, "structured_extraction_available": False}
    parser = STRUCTURED_EXTRACTORS.get(document_type)
    if parser is None or not raw_text or not raw_text.strip():
        return {"structured_extraction_available": False, "reason": "No reliable structured fields could be extracted"}
    data = parser(_normalise_for_parsing(raw_text))
    return data or {"structured_extraction_available": False, "reason": "No reliable structured fields could be extracted"}


def _normalise_for_parsing(text: str) -> list[str]:
    """Normalise a parsing copy while preserving its meaningful line boundaries."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("–", "-").replace("—", "-")
    return [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n") if line.strip()]


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _valid_value(value: str, labels: set[str]) -> bool:
    candidate = value.strip(" :#-")
    candidate_key = _key(candidate)
    if not candidate or candidate_key in labels or candidate_key in _COMMON_LABELS:
        return False
    # Avoid interpreting document titles, section headings, or table headings as values.
    forbidden = ("repair estimate", "estimate no", "estimated repair items", "parts (", "labour (", "total (", "damage assessment")
    return not any(token in candidate.lower() for token in forbidden)


def _line_value(lines: list[str], *labels: str) -> str | None:
    """Support both ``Label: value`` and a safe ``Label``/``value`` layout."""
    label_keys = {_key(label) for label in labels}
    for index, line in enumerate(lines):
        key, separator, value = line.partition(":")
        if separator and _key(key) in label_keys and _valid_value(value, label_keys):
            return value.strip()
        if _key(line) in label_keys and index + 1 < len(lines) and _valid_value(lines[index + 1], label_keys):
            return lines[index + 1]
    return None


def _date(value: str | None, *, month_first: bool = False) -> str | None:
    if not value:
        return None
    formats = ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%d-%m-%Y") if month_first else ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y")
    for fmt in (*formats, "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value.strip().rstrip("."), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _labelled_date(lines: list[str], *labels: str, month_first: bool = False) -> str | None:
    return _date(_line_value(lines, *labels), month_first=month_first)


def _amount(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = re.sub(rf"\b(?:{_CURRENCIES})\b", "", value, flags=re.I).replace(",", "").strip()
    if not re.fullmatch(r"-?\d+(?:\.\d{1,2})?", cleaned):
        return None
    try:
        return float(Decimal(cleaned))
    except InvalidOperation:
        return None


def _currency(lines: list[str]) -> str | None:
    found = re.search(rf"\b({_CURRENCIES})\b", "\n".join(lines), re.I)
    return found.group(1).upper() if found else None


def _integer(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() else None


def _vehicle_year(value: str | None) -> int | None:
    year = _integer(value)
    return year if year is not None and 1900 <= year <= datetime.now().year + 1 else None


def _vin(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"\s+", "", value).upper()
    return compact if re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", compact) else None


def _registration_number(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"\s+", "", value).upper()
    return compact if re.fullmatch(r"[A-Z0-9]{2,12}(?:-[A-Z0-9]{1,12})+|[A-Z0-9]{4,16}", compact) else None


def _licence_class(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip().upper()
    # Known licence categories; reject OCR fragments such as "9aEnd".
    return candidate if re.fullmatch(r"(?:A|A1|B|B1|C|C1|D|D1|E|M)", candidate) else None


def _time(value: str | None) -> str | None:
    if not value or not re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d", value.strip()):
        return None
    return value.strip().zfill(5)


def _empty_repair_estimate() -> dict:
    return {"garage_name": None, "estimate_number": None, "issued_date": None, "customer_name": None,
            "vehicle": {"make_model": None, "year": None}, "registration_number": None,
            "claim_reference": None, "damage_description": None, "repair_items": [],
            "total_estimated_repair_cost": None, "currency": None, "validity_days": None}


def _repair_estimate(lines: list[str]) -> dict:
    # Do not turn arbitrary OCR fragments into an all-null "estimate" record.
    recognised = {"garage", "workshop", "repairer", "estimate no", "estimate number", "issued", "issue date", "estimate date", "customer", "vehicle", "registration", "claim reference", "damage assessment", "total estimated repair cost"}
    if not any(_key(line.partition(":")[0]) in recognised or _key(line) in recognised for line in lines):
        return {}
    data = _empty_repair_estimate()
    first = lines[0] if lines else None
    data["garage_name"] = _line_value(lines, "garage", "workshop", "repairer")
    if data["garage_name"] is None and first and not re.search(r"\b(?:vehicle )?(?:repair )?(?:estimate|quotation|invoice)\b", first, re.I):
        data["garage_name"] = first
    data["estimate_number"] = _line_value(lines, "estimate no", "estimate no.", "estimate number")
    data["issued_date"] = _labelled_date(lines, "issued", "issue date", "estimate date")
    data["customer_name"] = _line_value(lines, "customer", "client")
    vehicle_value = _line_value(lines, "vehicle")
    if vehicle_value:
        vehicle = re.fullmatch(rf"(.+?)\s*-\s*({_YEAR})", vehicle_value)
        data["vehicle"] = {"make_model": vehicle.group(1).strip() if vehicle else vehicle_value,
                           "year": int(vehicle.group(2)) if vehicle else None}
    data["registration_number"] = _line_value(lines, "registration", "registration number", "plate number")
    data["claim_reference"] = _line_value(lines, "claim reference", "claim number")
    data["damage_description"] = _section(lines, "damage assessment", "estimated repair items") or _line_value(lines, "damage", "damage description", "description")
    data["repair_items"] = _repair_items(lines)
    total = _line_value(lines, "total estimated repair cost", "total estimated", "total estimate") or _inline_total(lines, r"(?:grand )?total(?: estimated(?: repair cost)?)?")
    data["total_estimated_repair_cost"] = _amount(total)
    data["currency"] = _currency(lines)
    valid = re.search(r"\bvalid\s+for\s+(\d+)\s+days?", "\n".join(lines), re.I)
    data["validity_days"] = int(valid.group(1)) if valid else None
    return data


def _section(lines: list[str], start: str, end: str) -> str | None:
    start_index = next((i for i, line in enumerate(lines) if _key(line) == _key(start)), None)
    if start_index is None:
        return None
    values: list[str] = []
    for line in lines[start_index + 1:]:
        if _key(line) == _key(end) or re.search(r"\b(?:item|parts|labour|total)\b", line, re.I):
            break
        values.append(line)
    return " ".join(values) or None


def _repair_items(lines: list[str]) -> list[dict]:
    items = []
    for line in lines:
        cells = [part.strip() for part in line.split("|")]
        if len(cells) != 4 or re.search(r"\b(?:item|parts|labour|total)\b", cells[0], re.I):
            continue
        amounts = [_amount(cell) for cell in cells[1:]]
        if cells[0] and all(amount is not None for amount in amounts):
            items.append({"item": cells[0], "parts_cost": amounts[0], "labour_cost": amounts[1], "total_cost": amounts[2]})
    return items


def _inline_total(lines: list[str], label: str) -> str | None:
    for line in lines:
        match = re.search(rf"{label}\s*:?\s*(?:{_CURRENCIES}\s*)?([\d,]+(?:\.\d{{1,2}})?)\b", line, re.I)
        if match:
            return match.group(1)
    return None


def _drivers_licence(lines: list[str]) -> dict:
    authority = _line_value(lines, "issuing authority", "issuer", "state")
    if authority is None:
        authority = next((line.title() for line in lines[:2] if re.fullmatch(r"(?:south|north) carolina|egypt|cairo", line, re.I)), None)
    return {"full_name": _line_value(lines, "name", "full name"), "licence_number": _line_value(lines, "licence number", "license number", "dl number"),
            "date_of_birth": _labelled_date(lines, "dob", "date of birth", month_first=True), "issue_date": _labelled_date(lines, "issue date", "issued", month_first=True),
            "expiry_date": _labelled_date(lines, "expiry date", "expiration date", "expires", month_first=True), "vehicle_class": _licence_class(_line_value(lines, "vehicle class", "class")),
            "issuing_authority": authority, "address": _line_value(lines, "address"), "sex": _line_value(lines, "sex", "gender"),
            "restrictions": _line_value(lines, "restrictions", "restriction")}


def _vehicle_registration(lines: list[str]) -> dict:
    return {"owner_name": _line_value(lines, "owner name", "owner", "registered to"),
            "registration_number": _registration_number(_line_value(lines, "registration number", "registration", "reg number")),
            "vin": _vin(_line_value(lines, "vehicle identification number vin", "vehicle identification number", "vin")),
            "national_id": _line_value(lines, "national id", "national identification number"),
            "vehicle_make": _line_value(lines, "vehicle make", "make"), "vehicle_model": _line_value(lines, "vehicle model", "model"),
            "model_year": _vehicle_year(_line_value(lines, "model year", "year")), "vehicle_type": _line_value(lines, "vehicle type", "type"),
            "colour": _line_value(lines, "colour", "color"), "engine_number": _line_value(lines, "engine number"),
            "engine_capacity_cc": _integer(_line_value(lines, "engine capacity cc", "engine capacity")), "fuel_type": _line_value(lines, "fuel type"),
            "number_of_seats": _integer(_line_value(lines, "number of seats", "seats")),
            "registration_issue_date": _labelled_date(lines, "registration issue date", "issue date"),
            "registration_expiry_date": _labelled_date(lines, "registration expiry date", "registration expiry", "registration expiration", "expiry date"),
            "issuing_authority": _line_value(lines, "issuing authority", "authority"), "status": _line_value(lines, "status")}


def _invoice(lines: list[str]) -> dict:
    return {"provider_name": _line_value(lines, "provider", "hospital", "clinic", "pharmacy"), "invoice_number": _line_value(lines, "invoice number", "invoice no", "invoice no."),
            "invoice_date": _labelled_date(lines, "invoice date", "date"), "customer_name": _line_value(lines, "customer", "patient", "member"),
            "subtotal": _amount(_line_value(lines, "subtotal")), "tax": _amount(_line_value(lines, "tax", "vat")),
            "total_amount": _amount(_line_value(lines, "total amount", "amount due", "grand total") or _inline_total(lines, r"(?:grand )?total(?: amount)?|amount due")), "currency": _currency(lines)}


def _medical_report(lines: list[str]) -> dict:
    return {"patient_name": _line_value(lines, "patient", "patient name", "member"), "provider_name": _line_value(lines, "provider", "hospital", "clinic", "physician", "doctor"),
            "report_date": _labelled_date(lines, "report date", "date"), "diagnosis": _line_value(lines, "diagnosis"), "treatment": _line_value(lines, "treatment"),
            "admission_date": _labelled_date(lines, "admission date"), "discharge_date": _labelled_date(lines, "discharge date")}


def _police_report(lines: list[str]) -> dict:
    vehicle = _line_value(lines, "vehicle", "vehicle information")
    registration = None
    if vehicle:
        match = re.search(r"\bregistration\s+([A-Z0-9-]{4,16})\b", vehicle, re.I)
        registration = _registration_number(match.group(1)) if match else None
    narrative = _line_value(lines, "incident summary", "summary")
    return {"report_number": _line_value(lines, "report number", "report no", "police report number"), "incident_date": _labelled_date(lines, "incident date", "accident date"),
            "incident_time": _time(_line_value(lines, "incident time", "time")), "incident_location": _line_value(lines, "incident location", "accident location", "location"),
            "reporting_authority": _line_value(lines, "reporting authority", "police station", "authority"), "driver_name": _line_value(lines, "driver", "driver name"),
            "vehicle_information": vehicle, "registration_number": registration, "incident_summary": narrative, "officer_notes": _line_value(lines, "officer notes", "notes"),
            "injuries_reported": _line_value(lines, "injuries reported", "injuries"), "raw_narrative": narrative}


def _member_id(lines: list[str]) -> dict:
    return {"member_name": _line_value(lines, "member name", "name"), "member_id": _line_value(lines, "member id", "member number"),
            "policy_number": _line_value(lines, "policy number", "policy no"), "expiry_date": _labelled_date(lines, "expiry", "expiry date", "expiration date")}


def _simple_document(lines: list[str], schema: dict[str, tuple[str, ...]]) -> dict:
    return {field: (_labelled_date(lines, *labels) if field.endswith("_date") else _line_value(lines, *labels)) for field, labels in schema.items()}


def _split_list(value: str | None) -> list[str] | None:
    return [item.strip() for item in re.split(r"[,;]", value) if item.strip()] if value else None


def _fire_brigade_report(lines: list[str]) -> dict:
    return _simple_document(lines, {"report_number": ("report number", "report no"), "incident_date": ("incident date", "date"), "location": ("location", "incident location"), "station": ("station", "fire station")})


def _itemised_list(lines: list[str]) -> dict:
    return _simple_document(lines, {"list_reference": ("list reference", "reference"), "owner_name": ("owner", "customer"), "total_value": ("total value", "total")})


def _quotation(lines: list[str]) -> dict:
    return _simple_document(lines, {"supplier_name": ("supplier", "contractor", "provider"), "quotation_number": ("quotation number", "quote number"), "quotation_date": ("quotation date", "date"), "total_amount": ("total amount", "total")}) | {"currency": _currency(lines)}


def _prescription(lines: list[str]) -> dict:
    return _simple_document(lines, {"patient_name": ("patient", "patient name"), "prescriber_name": ("prescriber", "doctor", "physician"), "prescription_date": ("prescription date", "date"), "prescription_number": ("prescription number", "rx number")})


def _proof_of_ownership(lines: list[str]) -> dict:
    return _simple_document(lines, {"owner_name": ("owner", "purchaser"), "item_description": ("item", "description"), "purchase_date": ("purchase date", "date"), "proof_reference": ("receipt number", "reference")})


def _airline_report(lines: list[str]) -> dict:
    return _simple_document(lines, {"report_reference": ("pir number", "report number", "reference"), "passenger_name": ("passenger", "passenger name"), "flight_number": ("flight number", "flight"), "report_date": ("report date", "date"), "baggage_reference": ("baggage tag", "baggage reference")})


def _official_notice(lines: list[str]) -> dict:
    return _simple_document(lines, {"issuing_authority": ("issuing authority", "authority"), "notice_reference": ("notice number", "reference"), "issued_date": ("issued date", "date"), "subject": ("subject",)})


STRUCTURED_EXTRACTORS: dict[str, Callable[[list[str]], dict]] = {
    "Repair Estimate": _repair_estimate, "Driver's Licence": _drivers_licence, "Vehicle Registration": _vehicle_registration,
    "Garage Invoice": _invoice, "Itemised Hospital Invoice": _invoice, "Itemised Invoice": _invoice, "Pharmacy Invoice": _invoice, "Itemised Invoices": _invoice, "Receipts for Essentials": _invoice,
    "Medical Report": _medical_report, "Medical Certificate": _medical_report, "Physician Report": _medical_report, "Police Report": _police_report, "Police Theft Report": _police_report, "Police Report (Forced Entry)": _police_report,
    "Member ID": _member_id, "Fire Brigade Report": _fire_brigade_report, "Itemised List": _itemised_list, "Repair / Replacement Quotations": _quotation, "Prescription": _prescription,
    "Proof of Ownership": _proof_of_ownership, "Receipts / Proof of Ownership": _proof_of_ownership, "Receipt": _invoice, "Airline PIR": _airline_report, "Airline Report": _airline_report, "Airline PIR or Police Report": _airline_report, "Airline Property Irregularity Report": _airline_report,
    "Plumber Report": lambda lines: _simple_document(lines, {"report_number": ("report number", "reference"), "inspection_date": ("inspection date", "date"), "plumber_name": ("plumber", "provider"), "findings": ("findings", "damage")}),
    "Referring Physician Request": lambda lines: _simple_document(lines, {"patient_name": ("patient", "member"), "physician_name": ("physician", "doctor"), "request_date": ("request date", "date"), "requested_service": ("requested service", "service", "procedure")}),
    "Proof of Covered Reason": lambda lines: _simple_document(lines, {"reason": ("reason", "covered reason"), "issued_date": ("issued date", "date"), "issuing_authority": ("issuing authority", "authority")}),
    "Embassy / Consulate Statement": lambda lines: _simple_document(lines, {"issuing_authority": ("embassy", "consulate", "authority"), "statement_date": ("statement date", "date"), "reference": ("reference", "statement number")}),
    "Official Notice": _official_notice, "Death Certificate": _official_notice,
}
