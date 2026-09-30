#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import prepare_chamber_recovery as recovery
import process_evidence_batch as batch


def chamber_source(proposition_id: int) -> dict:
    return {
        "candidate_id": "80002541009",
        "source_kind": "institutional",
        "discovery_status": "exact_content",
        "attribution_trust": "official_author_bulk",
        "source_url": (
            "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao"
            f"?idProposicao={proposition_id}"
        ),
        "source_origin": {
            "institution": "Câmara dos Deputados",
            "chamber_id": "220528",
            "proposition_id": str(proposition_id),
            "author_name": "Dr. Victor Linhalis",
            "authorship_scope": "listed_author_signatory",
        },
        "institutional_snapshot": {
            "candidate_id": "80002541009",
            "chamber_id": "220528",
            "proposition_id": str(proposition_id),
            "siglaTipo": "EMR",
            "urlInteiroTeor": (
                "https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra"
                f"?codteor={proposition_id + 1000}"
            ),
        },
    }


def failed_state(item: dict) -> dict:
    return {
        "source_id": batch.make_source_id(item),
        "candidate_id": item["candidate_id"],
        "source_url": item["source_url"],
        "status": "failed",
        "attempts": 3,
        "reprocess_count": 0,
        "last_error": recovery.EXPECTED_ERROR,
    }


class ChamberRecoveryPreparationTests(unittest.TestCase):
    def test_parse_source_ids_rejects_duplicates_and_unbounded_input(self):
        with self.assertRaises(ValueError):
            recovery.parse_source_ids("0123456789abcdefabcd,0123456789abcdefabcd")
        with self.assertRaises(ValueError):
            recovery.parse_source_ids("0123456789abcdefabcd,")
        with self.assertRaises(ValueError):
            recovery.parse_source_ids(",".join(
                f"{number:020x}" for number in range(recovery.MAX_RECOVERY_SOURCES + 1)
            ))

    def test_only_selected_verified_exhausted_sources_are_reintroduced(self):
        selected = [chamber_source(2494683), chamber_source(2494684)]
        unrelated = chamber_source(2494685)
        state = {
            batch.make_source_id(item): failed_state(item)
            for item in selected + [unrelated]
        }
        source_ids = [batch.make_source_id(item) for item in selected]

        payload = recovery.build_recovery_payload(
            sources=selected + [unrelated],
            states=state,
            source_ids=source_ids,
        )

        self.assertEqual(selected, payload)
        self.assertEqual(3, len(state))

    def test_recovery_rejects_sources_that_have_already_migrated(self):
        item = chamber_source(2494683)
        source_id = batch.make_source_id(item)
        state = failed_state(item)
        state["reprocess_count"] = 1

        with self.assertRaisesRegex(ValueError, "não está elegível"):
            recovery.build_recovery_payload(
                sources=[item],
                states={source_id: state},
                source_ids=[source_id],
            )

    def test_recovery_rejects_non_official_document_links(self):
        item = chamber_source(2494683)
        item["institutional_snapshot"]["urlInteiroTeor"] = (
            "https://evil.example/proposicoesWeb/prop_mostrarintegra?codteor=1"
        )
        source_id = batch.make_source_id(item)

        with self.assertRaisesRegex(ValueError, "Proveniência incompatível"):
            recovery.build_recovery_payload(
                sources=[item],
                states={source_id: failed_state(item)},
                source_ids=[source_id],
            )

    def test_restores_only_selected_sources_from_verified_failed_baseline(self):
        target = chamber_source(2494683)
        target_id = batch.make_source_id(target)
        unrelated_id = "unrelated-source-id"
        unrelated = {"status": "failed", "attempts": 3, "last_error": "unrelated"}
        current = {
            target_id: {
                **failed_state(target),
                "status": "collected",
                "attempts": 103,
                "reprocess_count": 100,
                "last_error": "",
                "chamber_section_recovery_v1": True,
            },
            unrelated_id: dict(unrelated),
        }
        baseline = {
            target_id: failed_state(target),
            unrelated_id: {"status": "failed", "attempts": 9},
        }

        restored, previous = recovery.restore_selected_baseline_states(
            current_states=current,
            baseline_states=baseline,
            source_ids=[target_id],
        )

        self.assertEqual(failed_state(target), restored[target_id])
        self.assertEqual(unrelated, restored[unrelated_id])
        self.assertEqual(100, previous[target_id]["reprocess_count"])

    def test_refuses_to_restore_unrelated_current_states(self):
        target = chamber_source(2494683)
        target_id = batch.make_source_id(target)
        current = {
            target_id: {
                **failed_state(target),
                "status": "quarantined",
            },
        }
        baseline = {target_id: failed_state(target)}

        with self.assertRaisesRegex(ValueError, "não pode ser restaurado"):
            recovery.restore_selected_baseline_states(
                current_states=current,
                baseline_states=baseline,
                source_ids=[target_id],
            )


if __name__ == "__main__":
    unittest.main()
