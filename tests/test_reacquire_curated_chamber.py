#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import reacquire_curated_chamber as reacquire


def candidate(cid="123", chamber_id=999):
    return {
        "tse_id": cid,
        "ballot_name": "MARIA SILVA",
        "full_name": "MARIA SILVA",
        "office": "DEPUTADO FEDERAL",
        "party": "ABC",
        "current_mandate": {
            "institution": "Câmara dos Deputados",
            "chamber_id": chamber_id,
            "profile_url": f"https://www.camara.leg.br/deputados/{chamber_id}",
        },
    }


def manifest_record(prop_id=456):
    return {
        "curation_order": 1,
        "candidate_id": "123",
        "chamber_id": 999,
        "proposition_id": prop_id,
        "source_url": (
            "https://www.camara.leg.br/proposicoesWeb/"
            f"fichadetramitacao?idProposicao={prop_id}"
        ),
    }


class ReacquisitionTests(unittest.TestCase):
    def test_snapshot_chamber_id_must_match_manifest(self):
        row = manifest_record()
        row["chamber_id"] = 1000
        with self.assertRaisesRegex(RuntimeError, "chamber_id diverge"):
            reacquire.validate_record(row, candidates={"123": candidate()})

    def test_source_url_must_match_proposition_id(self):
        row = manifest_record()
        row["source_url"] = (
            "https://www.camara.leg.br/proposicoesWeb/"
            "fichadetramitacao?idProposicao=999"
        )
        with self.assertRaisesRegex(RuntimeError, "source_url não corresponde"):
            reacquire.validate_record(row, candidates={"123": candidate()})

    def test_next_link_reads_official_pagination(self):
        payload = {
            "links": [
                {"rel": "self", "href": "https://api.test/page=1"},
                {"rel": "next", "href": "https://api.test/page=2"},
            ]
        }
        self.assertEqual(
            "https://api.test/page=2",
            reacquire.next_link(payload),
        )

    def test_reacquire_paginates_filtered_author_query_until_target(self):
        calls = []

        def fake_json(url):
            calls.append(url)
            if "page=2" in url:
                return {
                    "dados": [
                        {
                            "id": 456,
                            "siglaTipo": "PL",
                            "numero": 10,
                            "ano": 2026,
                            "ementa": "Dispõe sobre tema de teste.",
                            "dataApresentacao": "2026-01-15T10:00:00",
                            "uri": "https://dados.test/proposicoes/456",
                        }
                    ],
                    "links": [],
                }
            self.assertIn("idDeputadoAutor=999", url)
            return {
                "dados": [{"id": 111, "siglaTipo": "PL", "numero": 1, "ano": 2026}],
                "links": [{"rel": "next", "href": "https://api.test/page=2"}],
            }

        sources, rejections, metrics = reacquire.reacquire(
            manifest={"records": [manifest_record()]},
            candidates={"123": candidate()},
            fetch_json=fake_json,
        )
        self.assertFalse(rejections["rejections"])
        self.assertEqual(1, metrics["requested"])
        self.assertEqual(1, metrics["reacquired"])
        self.assertEqual(0, metrics["rejected"])
        self.assertEqual(2, len(calls))

        row = sources["sources"][0]
        self.assertEqual("institutional", row["source_kind"])
        self.assertEqual("exact_content", row["discovery_status"])
        self.assertEqual("official_author_api", row["attribution_trust"])
        self.assertEqual(
            "api_idDeputadoAutor_paginated_reacquisition",
            row["source_origin"]["discovery_method"],
        )
        self.assertEqual(456, row["source_origin"]["proposition_id"])
        self.assertEqual(999, row["source_origin"]["chamber_id"])
        self.assertEqual(2, row["source_origin"]["api_page"])

    def test_missing_target_is_rejected_closed(self):
        def fake_json(url):
            return {
                "dados": [{"id": 111, "siglaTipo": "PL", "numero": 1, "ano": 2026}],
                "links": [],
            }

        sources, rejections, metrics = reacquire.reacquire(
            manifest={"records": [manifest_record()]},
            candidates={"123": candidate()},
            fetch_json=fake_json,
        )
        self.assertFalse(sources["sources"])
        self.assertEqual(1, metrics["rejected"])
        self.assertIn(
            "não localizado",
            rejections["rejections"][0]["detail"],
        )

    def test_max_page_failure_does_not_emit_source(self):
        def fake_json(url):
            return {
                "dados": [{"id": 111}],
                "links": [{"rel": "next", "href": "https://api.test/again"}],
            }

        sources, rejections, metrics = reacquire.reacquire(
            manifest={"records": [manifest_record()]},
            candidates={"123": candidate()},
            fetch_json=fake_json,
            max_pages=1,
        )
        self.assertFalse(sources["sources"])
        self.assertEqual(1, metrics["rejected"])
        self.assertIn("limite de paginação", rejections["rejections"][0]["detail"])


if __name__ == "__main__":
    unittest.main()
