REQUIRED_DOCUMENTS: dict[str, dict[str, list[str]]] = {
    "HEALTH": {
        "Inpatient Hospitalisation": ["Medical Report", "Itemised Hospital Invoice", "Member ID"],
        "Day-Case Surgery": ["Medical Report", "Itemised Hospital Invoice", "Member ID"],
        "Diagnostics": ["Referring Physician Request", "Itemised Invoice", "Member ID"],
        "Medication": ["Prescription", "Pharmacy Invoice", "Member ID"],
        "Emergency Treatment": ["Medical Report", "Itemised Invoice", "Member ID"],
        "Outpatient Consultation": ["Medical Report", "Member ID"],
        "Maternity": ["Medical Report", "Itemised Hospital Invoice", "Member ID"],
        "Dental": ["Medical Report", "Itemised Invoice", "Member ID"],
    },
    "MOTOR": {
        "Collision": ["Photos of Damage", "Repair Estimate", "Driver's Licence", "Vehicle Registration"],
        "Fire": ["Photos of Damage", "Fire Brigade Report", "Vehicle Registration"],
        "Theft": ["Police Theft Report", "Driver's Licence", "Vehicle Registration", "Spare Key"],
        "Third-Party": ["Police Report", "Photos of Damage", "Repair Estimate", "Driver's Licence", "Vehicle Registration"],
        "Windscreen / Glass": ["Photos of Damage", "Repair Estimate", "Vehicle Registration"],
    },
    "PROPERTY": {
        "Fire": ["Photos of Damage", "Itemised List", "Repair / Replacement Quotations"],
        "Lightning": ["Photos of Damage", "Itemised List", "Repair / Replacement Quotations"],
        "Explosion": ["Photos of Damage", "Itemised List", "Repair / Replacement Quotations"],
        "Accidental Damage": ["Photos of Damage", "Itemised List", "Repair / Replacement Quotations"],
        "Theft": ["Police Report (Forced Entry)", "Itemised List", "Proof of Ownership"],
        "Burst Internal Pipe": ["Photos of Damage", "Plumber Report", "Itemised List"],
        "Flood": ["Photos of Damage", "Itemised List", "Repair / Replacement Quotations"],
    },
    "TRAVEL": {
        "Emergency Medical": ["Physician Report", "Itemised Invoices"],
        "Trip Cancellation": ["Proof of Covered Reason"],
        "Baggage Loss": ["Airline PIR or Police Report", "Receipts / Proof of Ownership"],
        "Baggage Delay": ["Airline Property Irregularity Report", "Receipts for Essentials"],
        "Travel Document Replacement": ["Police Report", "Embassy / Consulate Statement"],
    },
}


def get_required_documents(product_line: str, claim_type: str) -> list[str] | None:
    return REQUIRED_DOCUMENTS.get(product_line, {}).get(claim_type)
