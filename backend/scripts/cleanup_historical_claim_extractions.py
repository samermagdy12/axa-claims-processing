import os
import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIRECTORY)
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.claim_import import cleanup_historical_import_extractions
from app.database import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        removed = cleanup_historical_import_extractions(db)
        db.commit()
        print(f"Removed {removed} historical import metadata extraction row(s).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
