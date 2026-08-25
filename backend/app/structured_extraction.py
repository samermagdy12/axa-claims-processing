"""Deterministic, document-type-specific parsing layered over raw OCR text."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Callable


def extract_structured_data(document_type: str, text: str) -> dict:
    """Return only values evidenced by the supplied raw text.

    New document parsers can be registered in ``STRUCTURED_EXTRACTORS`` without
    changing the OCR pipeline or its storage contract.
    """
    extractor = STRUCTURED_EXTRACTORS.get(document_type)
    return extractor(text) if extractor and text.strip() else {}


def _first(pattern: str, text: str, flags: int = re.IGNORECASE) -> str | None:
    match = re.search(pattern, text, flags)
    value = match.group(1) if match else None
    return value.strip(" :#") if value else None


def _date(value: str | None, *, month_first: bool = False) -> str | None:
    if not value:
        return None
    value = value.strip()
    for fmt in (("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%d-%m-%Y") if month_first else ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y")):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _amount(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _labelled_date(text: str, label: str, *, month_first: bool = False) -> str | None:
    value = _first(rf"(?:{label})\s*(?:date)?\s*[:#-]?\s*(\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}})", text)
    return _date(value, month_first=month_first)


def _driver_licence(text: str) -> dict:
    data = {
        "full_name": _first(r"(?:name|customer)\s*[:#-]?\s*([A-Z][A-Z .'-]{2,})", text),
        "licence_number": _first(r"(?:licen[cs]e|dl|id)\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{5,})", text),
        "date_of_birth": _labelled_date(text, r"(?:dob|date of birth|birth date)", month_first=True),
        "address": _first(r"address\s*[:#-]?\s*([^\n]+)", text),
        "licence_class": _first(r"(?:class)\s*[:#-]?\s*([A-Z0-9]+)", text),
        "restrictions": _first(r"restrictions?\s*[:#-]?\s*([^\n]+)", text),
        "issue_date": _labelled_date(text, r"(?:issue|issued)", month_first=True),
        "expiry_date": _labelled_date(text, r"(?:expiry|expiration|expires?)", month_first=True),
        "issuing_authority": _first(r"(?:issuing authority|issuer|state)\s*[:#-]?\s*([^\n]+)", text),
    }
    if not data["issuing_authority"]:
        state = _first(r"\b(South Carolina|North Carolina|Cairo|Egypt)\b", text)
        data["issuing_authority"] = state.title() if state else None
    return _without_none(data)


def _vehicle_registration(text: str) -> dict:
    return _without_none({
        "owner_name": _first(r"(?:owner|registered to)\s*[:#-]?\s*([^\n]+)", text),
        "registration_number": _first(r"(?:registration|reg\.?)(?: number| no\.?| #)?\s*[:#-]?\s*([A-Z0-9-]{4,})", text),
        "plate_number": _first(r"(?:plate|licen[cs]e plate)\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{3,})", text),
        "vehicle_make": _first(r"make\s*[:#-]?\s*([^\n]+)", text),
        "vehicle_model": _first(r"model\s*[:#-]?\s*([^\n]+)", text),
        "vehicle_year": _as_int(_first(r"(?:year|model year)\s*[:#-]?\s*((?:19|20)\d{2})", text)),
        "vin": _first(r"\bVIN\s*[:#-]?\s*([A-HJ-NPR-Z0-9]{11,17})", text),
        "registration_expiry_date": _labelled_date(text, r"(?:registration )?(?:expiry|expiration|expires?)"),
    })


def _repair_estimate(text: str) -> dict:
    currency, total = _currency_amount(text, r"\b(?:grand )?total(?: estimated)?|\btotal estimate")
    items = []
    for line in text.splitlines():
        match = re.match(r"\s*(?:[-*]|\d+[.)])\s*(.+?)\s+(?:EGP|USD|EUR)\s*([\d,]+(?:\.\d{1,2})?)\s*$", line, re.IGNORECASE)
        if match:
            amount = _amount(match.group(2))
            if amount is not None:
                items.append({"item": match.group(1).strip(), "cost": float(amount)})
    data = {
        "garage_name": _first(r"(?:garage|workshop|repairer)\s*[:#-]?\s*([^\n]+)", text),
        "estimate_number": _first(r"(?:estimate|quotation)\s*(?:number|no\.?|#)\s*[:#-]?\s*([A-Z0-9-]{3,})", text),
        "estimate_date": _labelled_date(text, r"(?:estimate|quotation) date"),
        "customer_name": _first(r"(?:customer|client)\s*[:#-]?\s*([^\n]+)", text),
        "vehicle": _first(r"vehicle\s*[:#-]?\s*([^\n]+)", text),
        "vehicle_year": _as_int(_first(r"vehicle year\s*[:#-]?\s*((?:19|20)\d{2})", text)),
        "registration_number": _first(r"(?:registration|plate)\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{3,})", text),
        "claim_reference": _first(r"(?:claim reference|claim (?:number|no\.?|#))\s*[:#-]?\s*([A-Z0-9-]{3,})", text),
        "damage_description": _labelled_list(text, r"(?:damage|description)"),
        "repair_items": items or None,
        "total_estimated_cost": float(total) if total is not None else None,
        "currency": currency,
    }
    return _without_none(data)


def _invoice(text: str) -> dict:
    currency, total = _currency_amount(text, r"\b(?:grand )?total(?: amount)?|\bamount due")
    return _without_none({
        "provider_name": _first(r"(?:provider|hospital|clinic|pharmacy)\s*[:#-]?\s*([^\n]+)", text),
        "invoice_number": _first(r"invoice\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{3,})", text),
        "invoice_date": _labelled_date(text, r"invoice date|date"),
        "customer_name": _first(r"(?:customer|patient|member)\s*[:#-]?\s*([^\n]+)", text),
        "subtotal": _decimal_value(_first(r"subtotal\s*[:#-]?\s*(?:EGP|USD|EUR)?\s*([\d,]+(?:\.\d{1,2})?)", text)),
        "tax": _decimal_value(_first(r"(?:tax|vat)\s*[:#-]?\s*(?:EGP|USD|EUR)?\s*([\d,]+(?:\.\d{1,2})?)", text)),
        "total_amount": float(total) if total is not None else None,
        "currency": currency,
    })


def _medical_report(text: str) -> dict:
    return _without_none({
        "patient_name": _first(r"(?:patient|member)\s*(?:name)?\s*[:#-]?\s*([^\n]+)", text),
        "provider_name": _first(r"(?:provider|hospital|clinic|physician|doctor)\s*[:#-]?\s*([^\n]+)", text),
        "report_date": _labelled_date(text, r"(?:report )?date"),
        "diagnosis": _first(r"diagnosis\s*[:#-]?\s*([^\n]+)", text),
        "treatment": _first(r"treatment\s*[:#-]?\s*([^\n]+)", text),
        "admission_date": _labelled_date(text, r"admission"),
        "discharge_date": _labelled_date(text, r"discharge"),
    })


def _police_report(text: str) -> dict:
    return _without_none({
        "report_number": _first(r"(?:police )?report\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{3,})", text),
        "incident_date": _labelled_date(text, r"(?:incident|accident) date"),
        "incident_location": _first(r"(?:incident|accident) location\s*[:#-]?\s*([^\n]+)", text),
        "reporting_authority": _first(r"(?:reporting authority|police station|authority)\s*[:#-]?\s*([^\n]+)", text),
        "involved_parties": _labelled_list(text, r"(?:involved parties|parties)"),
        "vehicle_information": _first(r"vehicle\s*[:#-]?\s*([^\n]+)", text),
    })


def _member_id(text: str) -> dict:
    return _without_none({
        "member_name": _first(r"(?:member|name)\s*(?:name)?\s*[:#-]?\s*([^\n]+)", text),
        "member_id": _first(r"member\s*(?:id|number|no\.?|#)\s*[:#-]?\s*([A-Z0-9-]{3,})", text),
        "policy_number": _first(r"policy\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{3,})", text),
        "expiry_date": _labelled_date(text, r"(?:expiry|expiration|expires?)"),
    })


def _currency_amount(text: str, label: str) -> tuple[str | None, Decimal | None]:
    match = re.search(rf"(?:{label})\s*[:#-]?\s*(EGP|USD|EUR)?\s*([\d,]+(?:\.\d{{1,2}})?)", text, re.IGNORECASE)
    return ((match.group(1).upper() if match and match.group(1) else None), _amount(match.group(2)) if match else None)


def _labelled_list(text: str, label: str) -> list[str] | None:
    value = _first(rf"{label}\s*[:#-]?\s*([^\n]+)", text)
    return [item.strip() for item in re.split(r";|,", value) if item.strip()] if value else None


def _as_int(value: str | None) -> int | None:
    return int(value) if value else None


def _decimal_value(value: str | None) -> float | None:
    amount = _amount(value)
    return float(amount) if amount is not None else None


def _without_none(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


STRUCTURED_EXTRACTORS: dict[str, Callable[[str], dict]] = {
    "Driver's Licence": _driver_licence,
    "Vehicle Registration": _vehicle_registration,
    "Repair Estimate": _repair_estimate,
    "Itemised Hospital Invoice": _invoice,
    "Itemised Invoice": _invoice,
    "Pharmacy Invoice": _invoice,
    "Itemised Invoices": _invoice,
    "Medical Report": _medical_report,
    "Physician Report": _medical_report,
    "Police Report": _police_report,
    "Police Theft Report": _police_report,
    "Police Report (Forced Entry)": _police_report,
    "Member ID": _member_id,
}
