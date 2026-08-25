from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
import unittest

from app.claim_import import DEFAULT_CLAIM_SOURCE_DIRECTORY, import_claims


class Result:
    def __init__(self, value=None):
        self.value = value

    def mappings(self):
        return self

    def first(self):
        return self.value

    def one(self):
        return self.value


class ImportDatabase:
    def __init__(self, policy_ids):
        self.policy_ids = set(policy_ids)
        self.claims = []
        self.extractions = {}
        self.committed = False

    def execute(self, statement, params=None):
        sql = str(statement)
        if "FROM policies" in sql:
            return Result({"policy_id": params["policy_id"]} if params["policy_id"] in self.policy_ids else None)
        if "FROM claim_extractions" in sql:
            source_id = params["source_claim_id"]
            return Result({"claim_id": self.extractions[source_id]["claim_id"]} if source_id in self.extractions else None)
        if "INSERT INTO claims" in sql:
            claim = {"claim_id": uuid4(), **params}
            self.claims.append(claim)
            return Result({"claim_id": claim["claim_id"]})
        if "INSERT INTO claim_extractions" in sql:
            import json

            extracted_data = json.loads(params["extracted_data"])
            self.extractions[extracted_data["source_claim_id"]] = {
                "claim_id": params["claim_id"],
                "extracted_data": extracted_data,
            }
            return Result()
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.committed = True

    def rollback(self):
        raise AssertionError("Import should not roll back")


class ClaimImportTests(unittest.TestCase):
    def setUp(self):
        policy_ids = {
            line.split(": ", 1)[1]
            for source_path in DEFAULT_CLAIM_SOURCE_DIRECTORY.glob("*.txt")
            for line in source_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("Policy ID:")
        }
        self.db = ImportDatabase(policy_ids)

    def test_imports_complete_dataset_with_clean_descriptions_and_source_tracing(self):
        result = import_claims(self.db)

        self.assertEqual(result.source_count, 27)
        self.assertEqual(result.imported_claims, 25)
        self.assertEqual(
            result.skipped_claims,
            {
                "CLM-014": "claimed amount is missing from source data",
                "CLM-023": "incident date is missing from source data",
            },
        )
        self.assertTrue(self.db.committed)
        self.assertEqual(len(self.db.claims), 25)
        self.assertEqual(len(self.db.extractions), 25)
        self.assertEqual(self.db.claims[0]["description"].splitlines()[0], "My car was hit from behind at a traffic light in Nasr City on 2026-06-18. The rear bumper and boot are damaged. I've attached photos, the garage repair estimate, my driving licence and the car registration. The repair estimate is EGP 7,500.")
        self.assertEqual(self.db.extractions["CLM-001"]["extracted_data"]["source_file"], "CLM-001.txt")

    def test_rerun_does_not_duplicate_historical_or_application_claims(self):
        application_claim = {"claim_id": uuid4(), "description": "Created through the application."}
        self.db.claims.append(application_claim)

        first = import_claims(self.db)
        second = import_claims(self.db)

        self.assertEqual(first.imported_claims, 25)
        self.assertEqual(second.imported_claims, 0)
        self.assertEqual(len(self.db.claims), 26)
        self.assertIn(application_claim, self.db.claims)
        self.assertEqual(
            second.skipped_claims,
            {
                **{f"CLM-{number:03d}": "already imported" for number in range(1, 28) if number not in {14, 23}},
                "CLM-014": "claimed amount is missing from source data",
                "CLM-023": "incident date is missing from source data",
            },
        )

    def test_missing_policy_is_skipped_without_creating_a_claim(self):
        with TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "CLM-001.txt"
            source_path.write_text(
                "Claim ID: CLM-001\nPolicy ID: P-MISSING\nDate received: 2026-07-01\n\n"
                "A collision happened on 2026-06-20. Claiming EGP 500.",
                encoding="utf-8",
            )
            result = import_claims(ImportDatabase(set()), Path(temporary_directory))

        self.assertEqual(result.imported_claims, 0)
        self.assertEqual(result.skipped_claims, {"CLM-001": "referenced policy P-MISSING does not exist"})


if __name__ == "__main__":
    unittest.main()
