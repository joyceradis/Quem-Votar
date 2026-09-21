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


def manifest_record():
    return {
        "curation_order": 1,
        "candidate_id": "123",
        "chamber_id": 999,
        "proposition_id": 456,
        "source_url": (
            "https://www.camara.leg.br/proposicoesWeb/"
            "fichadetramitacao?idProposicao=456"
        ),
    }


class ReacquisitionTests(unittest.TestCase):
    def test_author_matches_by_id_or_uri(self):
        self.assertTrue(
            reacquire.author_matches({"dados": [{"id": 999}]}, 999)
        )
        self.assertTrue(
            reacquire.author_matches(
                {
                    "dados": [
                        {
                            "uri": (
                                "https://dadosabertos.camara.leg.br/"
                                "api/v2/deputados/999"
                            )
                        }
                    ]
                },
                999,
            )
        )
        self.assertIsNone(
            reacquire.author_matches(
                {"dados": [{"id": 111, "uri": "https://x/deputados/111"}]},
                999,
            )
        )

    def test_snapshot_chamber_id_must_match_manifest(self):
        row = manifest_record()
        row["chamber_id"] = 1000
        with self.assertRaisesRegex(RuntimeError, "chamber_id diverge"):
            reacquire.validate_record(
                row,
                candidates={"123": candidate()},
            )

    def test_source_url_must_match_proposition_id(self):
        row = manifest_record()
        row["source_url"] = (
            "https://www.camara.leg.br/proposicoesWeb/"
            "fichadetramitacao?idProposicao=999"
        )
        with self.assertRaisesRegex(RuntimeError, "source_url não corresponde"):
            reacquire.validate_record(
                row,
                candidates={"123": candidate()},
            )

    def test_reacquire_requires_official_author_match(self):
        calls = []

        def fake_json(url):
            calls.append(url)
            if url.endswith("/autores"):
                return {
                    "dados": [
                        {
                            "id": 999,
                            "nome": "Maria Silva",
                            "uri": (
                                "https://dadosabertos.camara.leg.br/"
                                "api/v2/deputados/999"
                            ),
                        }
                    ]
                }
            return {
                "dados": {
                    "id": 456,
                    "siglaTipo": "PL",
                    "numero": 10,
                    "ano": 2026,
                    "ementa": "Dispõe sobre tema de teste.",
                    "dataApresentacao": "2026-01-15T10:00:00",
                }
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
            "api_proposition_author_reacquisition",
            row["source_origin"]["discovery_method"],
        )
        self.assertEqual(456, row["source_origin"]["proposition_id"])
        self.assertEqual(999, row["source_origin"]["chamber_id"])

    def test_wrong_author_is_rejected_not_collected(self):
        def fake_json(url):
            if url.endswith("/autores"):
                return {
                    "dados": [
                        {
                            "id": 111,
                            "nome": "Outra Pessoa",
                            "uri": (
                                "https://dadosabertos.camara.leg.br/"
                                "api/v2/deputados/111"
                            ),
                        }
                    ]
                }
            return {
                "dados": {
                    "id": 456,
                    "siglaTipo": "PL",
                    "numero": 10,
                    "ano": 2026,
                    "ementa": "Teste.",
                }
            }

        sources, rejections, metrics = reacquire.reacquire(
            manifest={"records": [manifest_record()]},
            candidates={"123": candidate()},
            fetch_json=fake_json,
        )
        self.assertFalse(sources["sources"])
        self.assertEqual(1, metrics["rejected"])
        self.assertIn(
            "autoria oficial não contém",
            rejections["rejections"][0]["detail"],
        )


if __name__ == "__main__":
    unittest.main()
