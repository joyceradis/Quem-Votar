import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "evidence_coverage_report.py"
spec = importlib.util.spec_from_file_location("evidence_coverage_report", MODULE_PATH)
reporter = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(reporter)


class EvidenceCoverageReportTests(unittest.TestCase):
    def test_states_and_metrics_are_candidate_based(self):
        candidates = [
            {"tse_id": "1", "ballot_name": "A", "office": "DEPUTADO FEDERAL", "party": "X"},
            {"tse_id": "2", "ballot_name": "B", "office": "DEPUTADO ESTADUAL", "party": "Y"},
            {"tse_id": "3", "ballot_name": "C", "office": "DEPUTADO ESTADUAL", "party": "Z"},
        ]
        sources = [
            {"candidate_id": "1", "discovery_status": "seed"},
            {"candidate_id": "2", "discovery_status": "exact_content"},
        ]
        drafts = [{"draft_id": "d2", "candidate_id": "2"}]
        reviews = [{"draft_id": "d2", "status": "approved"}]
        canonical = []

        result = reporter.build_report(candidates, sources, drafts, reviews, canonical)
        ledger = {x["candidate_id"]: x for x in result["ledger"]}

        self.assertEqual("discovery_only", ledger["1"]["state"])
        self.assertEqual("approved_not_canonical", ledger["2"]["state"])
        self.assertEqual("not_started", ledger["3"]["state"])
        self.assertEqual(3, result["metrics"]["candidate_universe"])
        self.assertEqual(1, result["metrics"]["candidates_with_seed"])
        self.assertEqual(1, result["metrics"]["candidates_with_exact_content"])

    def test_unknown_candidate_fails_closed(self):
        candidates = [{"tse_id": "1", "ballot_name": "A"}]
        with self.assertRaisesRegex(RuntimeError, "unknown candidate"):
            reporter.build_report(
                candidates,
                [{"candidate_id": "999", "discovery_status": "seed"}],
                [],
                [],
                [],
            )


if __name__ == "__main__":
    unittest.main()
