"""Create the minimal internal development accounts without changing customer data.

Set ASSESSOR_SEED_PASSWORD and OPERATIONS_SEED_PASSWORD in the environment before
running this script. Passwords are never stored in source control or printed.
"""

import os
import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIRECTORY)
sys.path.insert(0, str(BACKEND_DIRECTORY))

from sqlalchemy import text

from app.auth import ASSESSOR_ROLE, OPERATIONS_ROLE, hash_password
from app.database import SessionLocal

INTERNAL_USERS = (
    ("AXA Assessor", "assessor@axa.local", "INTERNAL-ASSESSOR", ASSESSOR_ROLE, "ASSESSOR_SEED_PASSWORD"),
    ("AXA Operations", "operations@axa.local", "INTERNAL-OPERATIONS", OPERATIONS_ROLE, "OPERATIONS_SEED_PASSWORD"),
)


def main() -> None:
    passwords = {environment_name: os.environ.get(environment_name) for *_, environment_name in INTERNAL_USERS}
    missing = [name for name, password in passwords.items() if not password]
    if missing:
        raise SystemExit(f"Missing required environment variable(s): {', '.join(missing)}")

    db = SessionLocal()
    try:
        for full_name, email, national_id, role_name, environment_name in INTERNAL_USERS:
            role = db.execute(text("SELECT role_id FROM roles WHERE role_name = :role_name"), {"role_name": role_name}).mappings().first()
            if role is None:
                raise RuntimeError(f"{role_name} role is not configured")
            user = db.execute(text("SELECT user_id FROM users WHERE email = :email"), {"email": email}).mappings().first()
            if user is None:
                user = db.execute(
                    text("""
                        INSERT INTO users (full_name, email, password_hash, national_id, status)
                        VALUES (:full_name, :email, :password_hash, :national_id, 'active')
                        RETURNING user_id
                    """),
                    {"full_name": full_name, "email": email, "password_hash": hash_password(passwords[environment_name]), "national_id": national_id},
                ).mappings().one()
            db.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id) ON CONFLICT DO NOTHING"), {"user_id": user["user_id"], "role_id": role["role_id"]})
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
