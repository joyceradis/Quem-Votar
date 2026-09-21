#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/staging/wartime-curation-154-summary.json"
DRY_RUN = ROOT / "data/staging/wartime-curation-154-dry-run.json"
CANONICAL = ROOT / "data/reference/topic-evidence.json"
TOPICS = ROOT / "data/reference/policy-topics.json"
FEDERAL = ROOT / "data/generated/candidates-federal.json"
META = ROOT / "data/generated/meta.json"

REMOVED_URL = (
    "https://www.camara.leg.br/proposicoesWeb/"
    "fichadetramitacao?idProposicao=2605709"
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class WartimeCurationReconciliationTests(unittest.TestCase):
    def test_manifest_counts_and_freeze_boundary(self):
        m = load(MANIFEST)
        self.assertEqual(
            {
                "approved": 26,
                "rejected": 62,
                "quarantined": 66,
                "approved_v5_5_eligible": 22,
                "approved_held_by_taxonomy": 4,
            },
            m["counts"],
        )
        self.assertEqual(26, len(m["approved"]))
        self.assertEqual(154, m["source"]["rows"])
        self.assertEqual(
            "f7ab2370c58aeaa49990a181dd013ca15f712120adb0d165bace9f8124ce5c50",
            m["source"]["sha256"],
        )

        topic_ids = {x["id"] for x in load(TOPICS)["topics"]}
        eligible = [
            x for x in m["approved"]
            if x["promotion_v5_5"] == "ELEGÍVEL_V5_5"
        ]
        held = [
            x for x in m["approved"]
            if x["promotion_v5_5"] == "RETIDO_TAXONOMIA_V5_5"
        ]
        self.assertEqual(22, len(eligible))
        self.assertEqual(4, len(held))
        self.assertTrue(all(x["topic_id"] in topic_ids for x in eligible))
        self.assertTrue(all(x["topic_id"] not in topic_ids for x in held))

    def test_dry_run_and_canonical_reconciliation(self):
        m = load(MANIFEST)
        dry = load(DRY_RUN)["result"]
        canonical = load(CANONICAL)
        canonical_urls = {x["source_url"] for x in canonical["entries"]}

        self.assertEqual(22, len(canonical["entries"]))
        self.assertEqual(22, dry["canonical_after"])
        self.assertEqual(0, dry["new_canonical_additions"])
        self.assertEqual(1, dry["canonical_removals"])
        self.assertFalse(dry["autoapproval"])
        self.assertFalse(dry["schema_changed"])
        self.assertFalse(dry["taxonomy_changed"])
        self.assertNotIn(REMOVED_URL, canonical_urls)

        eligible = [
            x for x in m["approved"]
            if x["promotion_v5_5"] == "ELEGÍVEL_V5_5"
        ]
        held = [
            x for x in m["approved"]
            if x["promotion_v5_5"] == "RETIDO_TAXONOMIA_V5_5"
        ]
        self.assertTrue(all(x["source_url"] in canonical_urls for x in eligible))
        self.assertTrue(all(x["source_url"] not in canonical_urls for x in held))

    def test_generated_snapshot_matches_canonical_count(self):
        canonical = load(CANONICAL)["entries"]
        federal = load(FEDERAL)
        embedded = [
            evidence
            for candidate in federal
            for evidence in (candidate.get("topic_evidence") or [])
        ]
        self.assertEqual(len(canonical), len(embedded))
        self.assertEqual(22, len(embedded))
        self.assertEqual(22, load(META)["counts"]["topic_evidence"])
        self.assertNotIn(
            REMOVED_URL,
            {x["source_url"] for x in embedded},
        )


if __name__ == "__main__":
    unittest.main()
