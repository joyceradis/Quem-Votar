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
    def test_q2_distinguishes_staging_history_and_sync_gap(self):
        candidates = [
            {"tse_id": "1", "topic_evidence": [{"evidence_type": "atuação"}]},
            {"tse_id": "2", "topic_evidence": []},
            {"tse_id": "3", "topic_evidence": [{"evidence_type": "proposta"}]},
            {"tse_id": "4", "topic_evidence": []},
        ]
        canonical = [
            {"candidate_id": "1", "evidence_type": "atuação"},
            {"candidate_id": "2", "evidence_type": "declaração"},
            {"candidate_id": "3", "evidence_type": "proposta"},
        ]
        staged = [{"candidate_id": "1", "evidence_type": "proposta", "review_status": "pending"}]
        result = reporter.build_report(candidates, [], [], [], canonical, staged_drafts=staged)
        rows = {x["candidate_id"]: x for x in result["ledger"]}
        self.assertEqual("staged_not_promoted", rows["1"]["q2"]["state"])
        self.assertEqual(0, rows["1"]["q2"]["canonical_prospective"])
        self.assertEqual("canonical_not_in_snapshot", rows["2"]["q2"]["state"])
        self.assertEqual("published", rows["3"]["q2"]["state"])
        self.assertEqual("no_published_prospective_evidence", rows["4"]["q2"]["state"])
        self.assertEqual(1, result["metrics"]["candidates_with_public_q2"])
        self.assertEqual(1, result["metrics"]["candidates_with_staged_q2_not_published"])
        self.assertEqual(1, result["metrics"]["candidates_with_canonical_q2_not_in_snapshot"])

    def test_orphan_staged_draft_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "unknown candidate"):
            reporter.build_report([{"tse_id": "1"}], [], [], [], [],
                                  staged_drafts=[{"candidate_id": "999", "evidence_type": "proposta"}])

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

    def test_negative_discovery_outcome_is_scoped_and_timestamped(self):
        candidates = [{"tse_id": "1", "ballot_name": "A", "office": "DEPUTADO ESTADUAL", "party": "X"}]
        result = reporter.build_report(
            candidates, [], [], [], [],
            discovery_checked_at="2026-09-20T14:00:00+00:00",
            discovery_candidate_ids=["1"],
        )
        row = result["ledger"][0]
        self.assertEqual(
            "no_seed_or_exact_content_found_in_checked_sources",
            row["discovery"]["outcome"],
        )
        self.assertEqual(
            "2026-09-20T14:00:00+00:00",
            row["discovery"]["checked_at"],
        )
        self.assertIn("tse_declared_channels", row["discovery"]["sources_checked"])
        self.assertIn("não implica ausência exaustiva", row["discovery"]["scope_note"])

    def test_global_timestamp_does_not_claim_new_candidates_were_checked(self):
        result = reporter.build_report(
            [{"tse_id": "1"}, {"tse_id": "2", "office": "SENADOR"}],
            [], [], [], [], discovery_checked_at="2026-09-20T14:00:00+00:00",
            discovery_candidate_ids=["1"],
        )
        rows = {x["candidate_id"]: x for x in result["ledger"]}
        self.assertEqual("not_checked", rows["2"]["discovery"]["outcome"])
        self.assertEqual("", rows["2"]["discovery"]["checked_at"])
        self.assertEqual([], rows["2"]["discovery"]["sources_checked"])
        self.assertEqual(1, result["metrics"]["candidates_discovery_checked"])

    def test_processing_and_exception_counts_are_candidate_scoped(self):
        candidates = [{"tse_id": "1", "ballot_name": "A", "office": "DEPUTADO ESTADUAL", "party": "X"}]
        result = reporter.build_report(
            candidates, [], [], [], [],
            processing_state={"sources": {"s1": {"candidate_id": "1", "status": "failed"}}},
            exception_queue={
                "exceptions": [
                    {
                        "candidate_id": "1",
                        "status": "open",
                        "queue_class": "retryable",
                    }
                ]
            },
        )
        row = result["ledger"][0]
        self.assertEqual(1, row["processing_failed"])
        self.assertEqual(1, row["exceptions_retryable"])

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
