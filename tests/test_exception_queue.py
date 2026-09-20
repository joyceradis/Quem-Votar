#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "build_exception_queue.py"
SPEC = importlib.util.spec_from_file_location("build_exception_queue", MODULE)
queue = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(queue)


class ExceptionQueueTests(unittest.TestCase):
    def candidates(self):
        return {
            "123": {
                "tse_id": "123",
                "ballot_name": "MARIA SILVA",
                "full_name": "MARIA SILVA",
            }
        }

    def test_timeout_is_retryable_not_human(self):
        payload = queue.build_queue(
            candidates=self.candidates(),
            discovery_payload={"rejections": []},
            processing_payload={
                "failures": [
                    {
                        "failure_id": "f1",
                        "candidate_id": "123",
                        "source_url": "https://example.org/x",
                        "stage": "collection",
                        "error": "timeout ao coletar",
                    }
                ]
            },
            drafts_payload={"drafts": []},
            observed_at="2026-09-20T10:00:00+00:00",
        )
        row = payload["exceptions"][0]
        self.assertEqual("transient_fetch_failure", row["reason"])
        self.assertEqual("retryable", row["queue_class"])
        self.assertFalse(row["requires_human"])
        self.assertEqual(0, payload["metrics"]["human_review_open"])

    def test_candidate_not_mentioned_goes_to_human_review(self):
        payload = queue.build_queue(
            candidates=self.candidates(),
            discovery_payload={"rejections": []},
            processing_payload={"failures": []},
            drafts_payload={
                "drafts": [
                    {
                        "draft_id": "d1",
                        "candidate_id": "123",
                        "candidate_name": "MARIA SILVA",
                        "source_url": "https://example.org/proposta",
                        "candidate_mentioned": False,
                        "published_at": "2026-09-01",
                    }
                ]
            },
            observed_at="2026-09-20T10:00:00+00:00",
        )
        row = payload["exceptions"][0]
        self.assertEqual("ambiguous_attribution", row["reason"])
        self.assertEqual("human_review", row["queue_class"])
        self.assertTrue(row["requires_human"])

    def test_missing_date_is_human_review(self):
        payload = queue.build_queue(
            candidates=self.candidates(),
            discovery_payload={"rejections": []},
            processing_payload={"failures": []},
            drafts_payload={
                "drafts": [
                    {
                        "draft_id": "d1",
                        "candidate_id": "123",
                        "source_url": "https://example.org/proposta",
                        "candidate_mentioned": True,
                        "published_at": "",
                    }
                ]
            },
            observed_at="2026-09-20T10:00:00+00:00",
        )
        self.assertEqual("unclear_publication_date", payload["exceptions"][0]["reason"])

    def test_non_normalizable_declared_seed_is_data_quality(self):
        payload = queue.build_queue(
            candidates=self.candidates(),
            discovery_payload={
                "rejections": [
                    {
                        "rejection_id": "r1",
                        "candidate_id": "123",
                        "reason": "declared_seed_not_normalizable",
                        "raw_value": "@maria",
                    }
                ]
            },
            processing_payload={"failures": []},
            drafts_payload={"drafts": []},
            observed_at="2026-09-20T10:00:00+00:00",
        )
        row = payload["exceptions"][0]
        self.assertEqual("invalid_declared_seed", row["reason"])
        self.assertEqual("data_quality", row["queue_class"])
        self.assertFalse(row["requires_human"])

    def test_resolved_exception_reopens_if_seen_again(self):
        first = queue.build_queue(
            candidates=self.candidates(),
            discovery_payload={"rejections": []},
            processing_payload={
                "failures": [
                    {
                        "candidate_id": "123",
                        "source_url": "https://example.org/x",
                        "error": "HTTP 404",
                    }
                ]
            },
            drafts_payload={"drafts": []},
            observed_at="2026-09-20T10:00:00+00:00",
        )
        eid = first["exceptions"][0]["exception_id"]
        resolved = queue.resolve_exception(
            first,
            exception_id_value=eid,
            resolver="joyceradis",
            note="fonte substituída",
            resolved_at="2026-09-20T11:00:00+00:00",
        )
        second = queue.build_queue(
            candidates=self.candidates(),
            discovery_payload={"rejections": []},
            processing_payload={
                "failures": [
                    {
                        "candidate_id": "123",
                        "source_url": "https://example.org/x",
                        "error": "HTTP 404",
                    }
                ]
            },
            drafts_payload={"drafts": []},
            previous_payload=resolved,
            observed_at="2026-09-20T12:00:00+00:00",
        )
        row = next(x for x in second["exceptions"] if x["exception_id"] == eid)
        self.assertEqual("open", row["status"])
        self.assertEqual(2, row["occurrences"])
        self.assertTrue(any(x["event"] == "reopened" for x in row["history"]))

    def test_missing_exception_is_cleared_on_recheck(self):
        first = queue.build_queue(
            candidates=self.candidates(),
            discovery_payload={
                "rejections": [
                    {
                        "candidate_id": "123",
                        "reason": "declared_seed_not_normalizable",
                        "raw_value": "@maria",
                    }
                ]
            },
            processing_payload={"failures": []},
            drafts_payload={"drafts": []},
            observed_at="2026-09-20T10:00:00+00:00",
        )
        second = queue.build_queue(
            candidates=self.candidates(),
            discovery_payload={"rejections": []},
            processing_payload={"failures": []},
            drafts_payload={"drafts": []},
            previous_payload=first,
            observed_at="2026-09-20T11:00:00+00:00",
        )
        self.assertEqual("cleared", second["exceptions"][0]["status"])
        self.assertEqual("pipeline", second["exceptions"][0]["resolved_by"])


if __name__ == "__main__":
    unittest.main()
