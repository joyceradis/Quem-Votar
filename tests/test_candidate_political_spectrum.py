import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "staging" / "candidate-political-spectrum.json"


class CandidatePoliticalSpectrumStagingTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(DATA.read_text(encoding="utf-8"))

    def test_future_metadata_contract_is_inert_during_freeze(self):
        self.assertEqual("staged_future_metadata", self.payload["schema_status"])
        self.assertIs(False, self.payload["public_use"])
        self.assertEqual("political_spectrum", self.payload["future_canonical_key"])
        self.assertEqual("maintainer_supplied", self.payload["classification"]["origin"])
        self.assertEqual(
            "not_independently_verified",
            self.payload["classification"]["verification_status"],
        )

    def test_entries_are_unique_valid_candidates_and_values_are_declared(self):
        candidates = {}
        for name in ("candidates-federal.json", "candidates-estadual.json"):
            for row in json.loads((ROOT / "data" / "generated" / name).read_text(encoding="utf-8")):
                candidates[str(row["tse_id"])] = row

        entries = self.payload["entries"]
        ids = [str(row["candidate_id"]) for row in entries]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.payload["source"]["candidate_count"], len(entries))

        allowed = set(self.payload["classification"]["allowed_values_observed"])
        self.assertTrue(allowed)
        all_drafts = []
        for row in entries:
            cid = str(row["candidate_id"])
            self.assertIn(cid, candidates)
            self.assertTrue(row["political_spectrum"])
            self.assertIn(row["political_spectrum"], allowed)
            self.assertEqual(
                row["source_draft_count"],
                len(row["source_draft_ids"]),
            )
            all_drafts.extend(row["source_draft_ids"])

        self.assertEqual(self.payload["source"]["draft_rows"], len(all_drafts))
        self.assertEqual(len(all_drafts), len(set(all_drafts)))

    def test_public_ui_does_not_consume_spectrum_metadata_during_freeze(self):
        public_text = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in ("index.html", "app.js")
        )
        self.assertNotIn("candidate-political-spectrum", public_text)
        self.assertNotIn("political_spectrum", public_text)
        self.assertNotIn("ESPECTRO_POLÍTICO", public_text)


if __name__ == "__main__":
    unittest.main()
