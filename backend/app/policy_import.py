import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session


DEFAULT_POLICY_SOURCE = Path(__file__).resolve().parents[2] / "data" / "AXA_capstone_data" / "policies.json"
IMPORTED_EMAIL_DOMAIN = "policy-import.local"


@dataclass
class ImportResult:
    source_count: int
    imported_policies: int
    provisioned_users: int


def load_source_policies(source_path: Path = DEFAULT_POLICY_SOURCE) -> list[dict]:
    with source_path.open(encoding="utf-8") as source_file:
        return json.load(source_file)


def import_policies(db: Session, source_path: Path = DEFAULT_POLICY_SOURCE) -> ImportResult:
    source_policies = load_source_policies(source_path)
    customer_role = db.execute(text("SELECT role_id FROM roles WHERE role_name = 'Customer'")).mappings().first()
    if customer_role is None:
        raise RuntimeError("Customer role is not configured")

    imported_policies = 0
    provisioned_users = 0
    try:
        for source_policy in source_policies:
            user = db.execute(
                text("SELECT user_id FROM users WHERE national_id = :national_id"),
                {"national_id": source_policy["national_id"]},
            ).mappings().first()
            if user is None:
                user = db.execute(
                    text("""
                        INSERT INTO users (full_name, email, password_hash, national_id, status)
                        VALUES (:full_name, :email, :password_hash, :national_id, 'inactive')
                        RETURNING user_id
                    """),
                    {
                        "full_name": source_policy["holder_name"],
                        "email": f"policy-{source_policy['national_id']}@{IMPORTED_EMAIL_DOMAIN}",
                        "password_hash": "!",
                        "national_id": source_policy["national_id"],
                    },
                ).mappings().one()
                provisioned_users += 1

            db.execute(
                text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id) ON CONFLICT DO NOTHING"),
                {"user_id": user["user_id"], "role_id": customer_role["role_id"]},
            )
            result = db.execute(
                text("""
                    INSERT INTO policies (
                        policy_id, user_id, policy_number, product_line, status,
                        start_date, end_date, annual_limit, remaining_limit, deductible, riders
                    )
                    VALUES (
                        :policy_id, :user_id, :policy_number, :product_line, :status,
                        :start_date, :end_date, :annual_limit, :remaining_limit, :deductible,
                        CAST(:riders AS JSONB)
                    )
                    ON CONFLICT (policy_id) DO NOTHING
                """),
                {
                    "policy_id": source_policy["policy_id"],
                    "user_id": user["user_id"],
                    "policy_number": source_policy["policy_id"],
                    "product_line": source_policy["line"].upper(),
                    "status": source_policy["status"].upper(),
                    "start_date": source_policy["start_date"],
                    "end_date": source_policy["end_date"],
                    "annual_limit": source_policy["annual_limit"],
                    "remaining_limit": source_policy["remaining_limit"],
                    "deductible": source_policy["deductible"],
                    "riders": json.dumps(source_policy["riders"]),
                },
            )
            imported_policies += result.rowcount
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ImportResult(len(source_policies), imported_policies, provisioned_users)
