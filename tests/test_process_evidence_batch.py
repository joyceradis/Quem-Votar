#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "process_evidence_batch.py"
SPEC = importlib.util.spec_from_file_location("process_evidence_batch", MODULE)
batch = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(batch)


def candidate():
    return {
        "tse_id": "123",
        "ballot_name": "MARIA SILVA",
        "full_name": "MARIA SILVA",
        "social_name": None,
        "office": "DEPUTADO ESTADUAL",
        "party": "ABC",
    }


def source(url="https://example.org/noticias/proposta-1"):
    return {
        "candidate_id": "123",
        "candidate_name": "MARIA SILVA",
        "source_kind": "official_candidate",
        "discovery_status": "exact_content",
        "source_url": url,
        "source_title": "Proposta",
        "source_publisher": "Portal oficial",
    }


def html_fetch(body_text: str, counter: list[int]):
    def fetch(url: str, **kwargs):
        counter[0] += 1
        body = (
            "<html><head><title>Proposta</title></head><body><p>"
            + body_text
            + "</p></body></html>"
        ).encode()
        return body, url, "text/html; charset=utf-8"
    return fetch


class ReliableBatchTests(unittest.TestCase):
    def test_section_upgrade_is_once_only_and_preserves_quarantine(self):
        item = source()
        item.update(attribution_trust="official_author_bulk", institutional_snapshot={
            "siglaTipo": "EMR", "urlInteiroTeor": "https://www.camara.leg.br/documento"})
        sid = batch.make_source_id(item)
        previous = {"status": "failed", "attempts": 3,
                    "last_error": "conteúdo institucional API insuficiente para revisão"}
        kwargs = dict(source_payload={"sources": [item]}, candidates={"123": candidate()},
                      existing_drafts=[], workers=1)
        # Even if a failed transport repeats the OLD error verbatim, no loop.
        with patch.object(batch, 'attempt_source', return_value=(None, 1, previous['last_error'])) as attempt:
            state, _, _, metrics = batch.run_batch(**kwargs, state_payload={"sources": {sid: previous}})
            self.assertEqual(metrics['queued'], 1)
            self.assertEqual(state['sources'][sid]['attempts'], 4)
            self.assertTrue(state['sources'][sid]['chamber_section_recovery_v1'])
            _, _, _, again = batch.run_batch(**kwargs, state_payload=state)
            self.assertEqual(again['queued'], 0)
            self.assertEqual(attempt.call_count, 1)
            for status in ('quarantined', 'rejected', 'collected'):
                _, _, _, metrics = batch.run_batch(**kwargs, state_payload={
                    'sources': {sid: dict(previous, status=status)}})
                self.assertEqual(metrics['queued'], 0)

    def test_resume_skips_already_collected_source(self):
        counter = [0]
        payload = {"sources": [source()]}
        state, drafts, failures, first = batch.run_batch(
            source_payload=payload,
            candidates={"123": candidate()},
            existing_drafts=[],
            fetcher=html_fetch("Maria Silva apresentou proposta de saúde para o estado.", counter),
            workers=1,
        )
        self.assertEqual(1, first["collected"])
        self.assertFalse(failures)
        self.assertEqual(1, counter[0])

        state2, drafts2, failures2, second = batch.run_batch(
            source_payload=payload,
            candidates={"123": candidate()},
            existing_drafts=drafts,
            state_payload=state,
            fetcher=html_fetch("Maria Silva apresentou proposta de saúde para o estado.", counter),
            workers=1,
        )
        self.assertEqual(1, second["skipped_collected"])
        self.assertEqual(0, second["queued"])
        self.assertEqual(1, counter[0])
        self.assertEqual(1, len(drafts2))
        self.assertFalse(failures2)

    def test_targeted_reprocess_refetches_without_duplicate(self):
        counter = [0]
        item = source()
        payload = {"sources": [item]}
        state, drafts, _, _ = batch.run_batch(
            source_payload=payload,
            candidates={"123": candidate()},
            existing_drafts=[],
            fetcher=html_fetch("Maria Silva apresentou proposta de saúde para o estado.", counter),
            workers=1,
        )
        sid = batch.make_source_id(item)
        state2, drafts2, _, metrics = batch.run_batch(
            source_payload=payload,
            candidates={"123": candidate()},
            existing_drafts=drafts,
            state_payload=state,
            reprocess_source_ids={sid},
            fetcher=html_fetch("Maria Silva apresentou proposta de saúde para o estado.", counter),
            workers=1,
        )
        self.assertEqual(2, counter[0])
        self.assertEqual(1, len(drafts2))
        self.assertEqual(1, metrics["collected"])
        self.assertEqual(1, state2["sources"][sid]["reprocess_count"])

    def test_content_change_creates_versioned_draft_and_is_observable(self):
        item = source()
        payload = {"sources": [item]}
        c1 = [0]
        state, drafts, _, _ = batch.run_batch(
            source_payload=payload,
            candidates={"123": candidate()},
            existing_drafts=[],
            fetcher=html_fetch("Maria Silva apresentou proposta antiga para a saúde estadual.", c1),
            workers=1,
        )
        sid = batch.make_source_id(item)
        c2 = [0]
        state2, drafts2, _, metrics = batch.run_batch(
            source_payload=payload,
            candidates={"123": candidate()},
            existing_drafts=drafts,
            state_payload=state,
            reprocess_source_ids={sid},
            fetcher=html_fetch("Maria Silva apresentou proposta nova para a educação estadual.", c2),
            workers=1,
        )
        self.assertEqual(2, len(drafts2))
        self.assertEqual(1, metrics["content_changed"])
        self.assertTrue(state2["sources"][sid]["content_changed"])
        self.assertTrue(state2["sources"][sid]["previous_content_sha256"])

    def test_failure_does_not_stop_other_sources(self):
        good = source("https://example.org/noticias/proposta-boa")
        bad = source("https://example.org/noticias/proposta-ruim")
        counter = [0]

        def fetch(url: str, **kwargs):
            counter[0] += 1
            if "ruim" in url:
                raise RuntimeError("timeout")
            body = b"<html><body><p>Maria Silva apresentou proposta valida para a saude estadual.</p></body></html>"
            return body, url, "text/html"

        state, drafts, failures, metrics = batch.run_batch(
            source_payload={"sources": [bad, good]},
            candidates={"123": candidate()},
            existing_drafts=[],
            retries_per_run=1,
            fetcher=fetch,
            workers=2,
        )
        self.assertEqual(1, metrics["collected"])
        self.assertEqual(1, metrics["failed"])
        self.assertEqual(1, len(drafts))
        self.assertEqual(1, len(failures))
        statuses = {v["status"] for v in state["sources"].values()}
        self.assertEqual({"collected", "failed"}, statuses)

    def test_fair_batch_round_robins_candidates(self):
        candidates = {
            "1": {**candidate(), "tse_id": "1", "ballot_name": "A"},
            "2": {**candidate(), "tse_id": "2", "ballot_name": "B"},
            "3": {**candidate(), "tse_id": "3", "ballot_name": "C"},
        }
        rows = []
        for cid in ("1", "2", "3"):
            for index in range(5):
                row = source(f"https://example.org/propostas/{cid}/{index}")
                row["candidate_id"] = cid
                row["candidate_name"] = candidates[cid]["ballot_name"]
                rows.append(row)

        seen = []
        def fetch(url: str, **kwargs):
            seen.append(url)
            cid = url.split("/")[-2]
            body = f"<html><body><p>{candidates[cid]['ballot_name']} apresentou proposta documentada para o estado.</p></body></html>".encode()
            return body, url, "text/html"

        _, _, _, metrics = batch.run_batch(
            source_payload={"sources": rows},
            candidates=candidates,
            existing_drafts=[],
            limit=3,
            per_candidate_limit=2,
            retries_per_run=1,
            fetcher=fetch,
            workers=1,
        )
        self.assertEqual(3, metrics["queued"])
        self.assertEqual(3, metrics["candidates_queued"])
        processed_candidates = {url.split("/")[-2] for url in seen}
        self.assertEqual({"1", "2", "3"}, processed_candidates)

    def test_per_candidate_limit_caps_dominant_candidate(self):
        candidates = {
            "1": {**candidate(), "tse_id": "1", "ballot_name": "A"},
            "2": {**candidate(), "tse_id": "2", "ballot_name": "B"},
        }
        rows = []
        for cid, count in (("1", 8), ("2", 1)):
            for index in range(count):
                row = source(f"https://example.org/propostas/{cid}/{index}")
                row["candidate_id"] = cid
                row["candidate_name"] = candidates[cid]["ballot_name"]
                rows.append(row)

        def fetch(url: str, **kwargs):
            cid = url.split("/")[-2]
            body = f"<html><body><p>{candidates[cid]['ballot_name']} apresentou proposta documentada para o estado.</p></body></html>".encode()
            return body, url, "text/html"

        _, _, _, metrics = batch.run_batch(
            source_payload={"sources": rows},
            candidates=candidates,
            existing_drafts=[],
            per_candidate_limit=2,
            retries_per_run=1,
            fetcher=fetch,
            workers=1,
        )
        self.assertEqual(3, metrics["queued"])

    def test_duplicate_source_rows_are_processed_once(self):
        item = source()
        counter = [0]
        _, drafts, _, metrics = batch.run_batch(
            source_payload={"sources": [item, dict(item)]},
            candidates={"123": candidate()},
            existing_drafts=[],
            fetcher=html_fetch("Maria Silva apresentou uma proposta documentada para o estado.", counter),
            workers=1,
        )
        self.assertEqual(1, metrics["exact_sources"])
        self.assertEqual(1, counter[0])
        self.assertEqual(1, len(drafts))


if __name__ == "__main__":
    unittest.main()
