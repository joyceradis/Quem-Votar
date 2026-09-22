import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CandidateProfileDataContractTest(unittest.TestCase):
    def test_generated_candidates_keep_displayable_tse_facts(self):
        required = (
            "party_name",
            "coalition",
            "coalition_composition",
            "education",
            "occupation",
        )
        for filename in (
            "candidates-federal.json",
            "candidates-estadual.json",
        ):
            rows = json.loads(
                (ROOT / "data" / "generated" / filename).read_text(encoding="utf-8")
            )
            self.assertTrue(rows, filename)
            for row in rows:
                for field in required:
                    self.assertTrue(
                        row.get(field),
                        f"{filename}: {row.get('tse_id')} sem {field}",
                    )
                self.assertIsInstance(
                    row.get("registration_status"),
                    str,
                    f"{filename}: {row.get('tse_id')} registration_status não explícito",
                )
                self.assertTrue(
                    row["registration_status"].strip(),
                    f"{filename}: {row.get('tse_id')} registration_status vazio",
                )

    def test_profile_surfaces_facts_and_explicit_unresolved_registration(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "styles.css").read_text(encoding="utf-8")

        for token in (
            "Dados eleitorais do TSE",
            "candidate.party_name",
            "candidate.coalition_composition",
            "candidate.education",
            "candidate.occupation",
            "registrationStatusLabel(candidate.registration_status)",
            "candidate.totalization_status",
            "Ainda não disponível na fonte atual",
            ".filter(item=>item.value)",
        ):
            self.assertIn(token, app)

        self.assertIn("electoral-data-grid", css)
        self.assertIn("electoral-data-item", css)

    def test_registration_status_metadata_documents_explicit_absence(self):
        meta = json.loads(
            (ROOT / "data" / "generated" / "meta.json").read_text(
                encoding="utf-8"
            )
        )
        note = meta.get("data_quality", {}).get("registration_status", "")
        self.assertIn("not_available", note)
        self.assertNotIn("publica null", note)


if __name__ == "__main__":
    unittest.main()
