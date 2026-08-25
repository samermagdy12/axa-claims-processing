import os
import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIRECTORY)
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.claim_import import import_claims
from app.database import SessionLocal


def main():
    db = SessionLocal()
    try:
        result = import_claims(db)
        print(f"Imported {result.imported_claims} of {result.source_count} source claims.")
        for source_claim_id, reason in result.skipped_claims.items():
            print(f"Skipped {source_claim_id}: {reason}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
