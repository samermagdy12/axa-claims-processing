import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session


DEFAULT_CLAIM_SOURCE_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "AXA_capstone_data" / "claims"

# These classifications use the existing claim-type values and are derived from
# each source narrative. They do not perform policy verification or decisions.
CLAIM_TYPE_BY_SOURCE_ID = {
    "CLM-001": "Collision", "CLM-002": "Collision", "CLM-003": "Inpatient Hospitalisation",
    "CLM-004": "Outpatient Consultation", "CLM-005": "Flood", "CLM-006": "Burst Internal Pipe",
    "CLM-007": "Collision", "CLM-008": "Collision", "CLM-009": "Collision",
    "CLM-010": "Outpatient Consultation", "CLM-011": "Collision", "CLM-012": "Collision",
    "CLM-013": "Outpatient Consultation", "CLM-014": "Theft", "CLM-015": "Maternity",
    "CLM-016": "Fire", "CLM-017": "Dental", "CLM-018": "Dental", "CLM-019": "Baggage Loss",
    "CLM-020": "Trip Cancellation", "CLM-021": "Emergency Medical", "CLM-022": "Collision",
    "CLM-023": "Accidental Damage", "CLM-024": "Windscreen / Glass", "CLM-025": "Fire",
    "CLM-026": "Medication", "CLM-027": "Baggage Delay",
}

# Historical source narratives use "accident" to describe the event.  Motor
# claims are stored under the handbook's canonical Collision category.
HISTORICAL_CLAIM_TYPE_ALIASES = {"Accident": "Collision"}

# Handbook Clause 4.5 defines the fixed benefit named by CLM-027's narrative.
DERIVED_AMOUNT_BY_SOURCE_ID = {"CLM-027": Decimal("1000")}
HEADER_PATTERN = re.compile(r"^Claim ID: (?P<claim_id>.+)\r?\nPolicy ID: (?P<policy_id>.+)\r?\nDate received: (?P<received_date>\d{4}-\d{2}-\d{2})\r?\n\r?\n(?P<description>[\s\S]+)$")
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
AMOUNT_PATTERN = re.compile(r"\bEGP\s+([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)


@dataclass
class ImportResult:
    source_count: int
    imported_claims: int
    skipped_claims: dict[str, str] = field(default_factory=dict)


def normalize_historical_claim_type(claim_type: str | None) -> str | None:
    if claim_type is None:
        return None
    return HISTORICAL_CLAIM_TYPE_ALIASES.get(claim_type, claim_type)


def cleanup_historical_import_extractions(db: Session) -> int:
    """Remove only legacy importer metadata, never document extraction results."""
    deleted = db.execute(
        text("""
            DELETE FROM claim_extractions
            WHERE jsonb_exists(extracted_data, 'source_claim_id')
              AND jsonb_exists(extracted_data, 'source_file')
              AND jsonb_exists(extracted_data, 'source_date_received')
              AND NOT jsonb_exists(extracted_data, 'document_id')
        """)
    )
    return deleted.rowcount


def parse_claim_source(source_path: Path) -> dict:
    match = HEADER_PATTERN.match(source_path.read_text(encoding="utf-8").strip())
    if match is None:
        raise ValueError("invalid source file format")
    source_claim = match.groupdict()
    description = source_claim["description"].strip()
    incident_date = DATE_PATTERN.search(description)
    amount = AMOUNT_PATTERN.search(description)
    source_claim["description"] = description
    source_claim["incident_date"] = date.fromisoformat(incident_date.group(1)) if incident_date else None
    source_claim["claimed_amount"] = Decimal(amount.group(1).replace(",", "")) if amount else DERIVED_AMOUNT_BY_SOURCE_ID.get(source_claim["claim_id"])
    source_claim["submission_date"] = date.fromisoformat(source_claim.pop("received_date"))
    source_claim["claim_type"] = normalize_historical_claim_type(CLAIM_TYPE_BY_SOURCE_ID.get(source_claim["claim_id"]))
    return source_claim


def import_claims(db: Session, source_directory: Path = DEFAULT_CLAIM_SOURCE_DIRECTORY) -> ImportResult:
    source_paths = sorted(source_directory.glob("*.txt"))
    result = ImportResult(source_count=len(source_paths), imported_claims=0)
    try:
        for source_path in source_paths:
            try:
                source_claim = parse_claim_source(source_path)
            except ValueError as error:
                result.skipped_claims[source_path.stem] = str(error)
                continue

            source_id = source_claim["claim_id"]
            if source_claim["claim_type"] is None:
                result.skipped_claims[source_id] = "claim type cannot be derived from source data"
                continue
            if source_claim["incident_date"] is None:
                result.skipped_claims[source_id] = "incident date is missing from source data"
                continue
            if source_claim["claimed_amount"] is None:
                result.skipped_claims[source_id] = "claimed amount is missing from source data"
                continue

            policy = db.execute(text("SELECT policy_id FROM policies WHERE policy_id = :policy_id"), {"policy_id": source_claim["policy_id"]}).first()
            if policy is None:
                result.skipped_claims[source_id] = f"referenced policy {source_claim['policy_id']} does not exist"
                continue

            # Historical source content is stored directly in claims.description.
            # Use the full imported claim identity to keep reruns idempotent without
            # creating a non-document record in claim_extractions.
            existing_claim = db.execute(
                text("""
                    SELECT claim_id
                    FROM claims
                    WHERE policy_id = :policy_id
                      AND claim_type = :claim_type
                      AND incident_date = :incident_date
                      AND submission_date = :submission_date
                      AND claimed_amount = :claimed_amount
                      AND description = :description
                """),
                {
                    "policy_id": source_claim["policy_id"],
                    "claim_type": source_claim["claim_type"],
                    "incident_date": source_claim["incident_date"],
                    "submission_date": source_claim["submission_date"],
                    "claimed_amount": source_claim["claimed_amount"],
                    "description": source_claim["description"],
                },
            ).first()
            if existing_claim:
                result.skipped_claims[source_id] = "already imported"
                continue

            db.execute(
                text("""
                    INSERT INTO claims (policy_id, claim_type, incident_date, submission_date, claimed_amount, description)
                    VALUES (:policy_id, :claim_type, :incident_date, :submission_date, :claimed_amount, :description)
                    RETURNING claim_id
                """),
                {
                    "policy_id": source_claim["policy_id"],
                    "claim_type": source_claim["claim_type"],
                    "incident_date": source_claim["incident_date"],
                    "submission_date": source_claim["submission_date"],
                    "claimed_amount": source_claim["claimed_amount"],
                    "description": source_claim["description"],
                },
            ).mappings().one()
            result.imported_claims += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result
