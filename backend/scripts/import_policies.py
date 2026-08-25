import os
import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIRECTORY)
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.database import SessionLocal
from app.policy_import import import_policies


def main():
    db = SessionLocal()
    try:
        result = import_policies(db)
        print(f"Imported {result.imported_policies} of {result.source_count} source policies; provisioned {result.provisioned_users} users.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
