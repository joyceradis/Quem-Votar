#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_curation_batch as batching
import coletor_evidencias as collector
import discover_evidence_sources as discovery
import process_evidence_batch as processor


def candidate(cid: str = "123") -> dict:
    return {
        "tse_id": cid,
        "ballot_name": f"CANDIDATO {cid}",
        "full_name": f"CANDIDATO {cid}",
        "office": "DEPUTADO FEDERAL",
        "party": "TESTE",
    }


def chamber_source(cid: str = "123", prop_id: int = 456) -> dict:
    title = f"PL 10/2026 — Ementa institucional da proposição {prop_id} para teste."
    return {
        "candidate_id": cid,
        "candidate_name": f"CANDIDATO {cid}",
        "source_kind": "institutional",
        "discovery_status": "exact_content",
        "seed_url": "https://www.camara.leg.br/deputados/999",
        "source_url": (
            "https://www.camara.leg.br/proposicoesWeb/"
            f"fichadetramitacao?idProposicao={prop_id}"
        ),
        "source_title": title,
        "source_publisher": "Câmara dos Deputados",
        "published_at": "2026-01-10",
        "attribution_trust": "official_author_api",
        "attribution_basis_hint": (
            f"Câmara dos Deputados API: idDeputadoAutor=999; idProposicao={prop_id}."
        ),
        "source_origin": {
            "institution": "Câmara dos Deputados",
            "discovery_method": "api_idDeputadoAutor",
            "chamber_id": 999,
            "proposition_id": prop_id,
            "api_url": "https://dadosabertos.camara.leg.br/api/v2/proposicoes?idDeputadoAutor=999",
        },
        "institutional_snapshot": {
            "transport": "camara_dados_abertos",
            "query": "idDeputadoAutor",
            "candidate_id": cid,
            "chamber_id": 999,
            "proposition_id": prop_id,
            "api_url": "https://dadosabertos.camara.leg.br/api/v2/proposicoes?idDeputadoAutor=999",
            "api_item_uri": f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{prop_id}",
            "siglaTipo": "PL",
            "numero": "10",
            "ano": 2026,
            "ementa": f"Ementa institucional da proposição {prop_id} para teste.",
            "dataApresentacao": "2026-01-10",
            "title": title,
        },
    }


class WartimeThroughputTests(unittest.TestCase):
    def test_listing_routes_are_not_exact_content(self):
        self.assertFalse(
            discovery.looks_like_exact_content(
                "https://exemplo.org/categoria/noticias/",
                "Notícias",
            )
        )
        self.assertFalse(
            discovery.looks_like_exact_content(
                "https://exemplo.org/tipo/artigos/",
                "Artigos",
            )
        )
        self.assertTrue(
            discovery.looks_like_exact_content(
                "https://exemplo.org/artigos/projeto-cria-rota-turistica/",
                "Projeto cria rota turística",
            )
        )

    def test_trusted_chamber_snapshot_does_not_refetch_html(self):
        source = chamber_source()
        calls = []

        def forbidden_fetch(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("HTML fetch must not happen")

        draft = collector.collect_source(
            source,
            candidates={"123": candidate()},
            fetcher=forbidden_fetch,
        )
        self.assertEqual([], calls)
        self.assertEqual("api_json", draft["document_type"])
        self.assertEqual("official_author_api", draft["attribution_trust"])
        self.assertIn("Ementa institucional", draft["raw_excerpt"])
        self.assertEqual("Câmara dos Deputados", draft["source_publisher"])

    def test_exhausted_429_recovers_through_snapshot_transport_upgrade(self):
        source = chamber_source()
        sid = processor.make_source_id(source)
        state = {
            "version": "1.0.0",
            "sources": {
                sid: {
                    "source_id": sid,
                    "candidate_id": "123",
                    "source_url": source["source_url"],
                    "attempts": 3,
                    "status": "failed",
                    "last_error": f"HTTP 429 ao coletar {source['source_url']}",
                }
            },
        }

        result_state, drafts, failures, metrics = processor.run_batch(
            source_payload={"sources": [source]},
            candidates={"123": candidate()},
            existing_drafts=[],
            state_payload=state,
            max_attempts=3,
            retries_per_run=2,
            workers=1,
            limit=10,
            per_candidate_limit=10,
            fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("snapshot path should not call fetcher")
            ),
        )
        self.assertEqual(1, metrics["collected"])
        self.assertEqual(0, metrics["skipped_exhausted"])
        self.assertFalse(failures)
        self.assertEqual(1, len(drafts))
        self.assertEqual("collected", result_state["sources"][sid]["status"])

    def test_curation_delta_excludes_decided_canonical_and_listing(self):
        trusted = collector.collect_source(
            chamber_source("1", 101),
            candidates={"1": candidate("1")},
            fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("no fetch")
            ),
        )
        decided = dict(trusted, draft_id="decided", candidate_id="2", candidate_name="C2")
        canonical = dict(trusted, draft_id="canonical", candidate_id="3", candidate_name="C3")
        canonical["source_url"] = (
            "https://www.camara.leg.br/proposicoesWeb/"
            "fichadetramitacao?idProposicao=303"
        )
        shared_other_candidate = dict(
            canonical,
            draft_id="shared-other-candidate",
            candidate_id="5",
            candidate_name="C5",
        )
        listing = {
            "draft_id": "listing",
            "candidate_id": "4",
            "candidate_name": "C4",
            "source_kind": "official_candidate",
            "source_url": "https://exemplo.org/categoria/noticias/",
            "source_title": "Notícias",
            "source_publisher": "exemplo.org",
            "review_status": "pending",
        }

        payload, metrics = batching.build_batch(
            drafts_payload={"drafts": [trusted, decided, canonical, shared_other_candidate, listing]},
            canonical_payload={"entries": [{"candidate_id": canonical["candidate_id"], "source_url": canonical["source_url"]}]},
            decisions_payload={"decisions": {"QUARENTENA": ["decided"]}},
            limit=100,
            per_candidate_limit=12,
        )
        self.assertEqual(2, payload["metrics"]["selected"])
        selected_ids = {row["draft_id"] for row in payload["items"]}
        self.assertEqual({trusted["draft_id"], "shared-other-candidate"}, selected_ids)
        self.assertTrue(all(row["lane"] == "institutional_trusted" for row in payload["items"]))
        self.assertEqual(1, metrics["skipped_decided"])
        self.assertEqual(1, metrics["skipped_canonical"])
        self.assertEqual(1, metrics["skipped_listing"])
        self.assertEqual(1, metrics["canonical_urls"])
        self.assertEqual(1, metrics["canonical_candidate_urls"])
        self.assertFalse(payload["policy"]["autoapproval"])

    def test_curation_prefers_recent_dated_item_within_same_priority(self):
        older = collector.collect_source(
            chamber_source("1", 201),
            candidates={"1": candidate("1")},
            fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("no fetch")
            ),
        )
        newer = collector.collect_source(
            chamber_source("1", 202),
            candidates={"1": candidate("1")},
            fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("no fetch")
            ),
        )
        undated = collector.collect_source(
            chamber_source("1", 203),
            candidates={"1": candidate("1")},
            fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("no fetch")
            ),
        )

        older["published_at"] = "2023-02-01"
        newer["published_at"] = "2026-07-01"
        undated["published_at"] = ""

        payload, metrics = batching.build_batch(
            drafts_payload={"drafts": [older, undated, newer]},
            canonical_payload={"entries": []},
            decisions_payload={"decisions": {}},
            limit=1,
            per_candidate_limit=1,
        )

        self.assertEqual(1, metrics["selected"])
        self.assertEqual(newer["draft_id"], payload["items"][0]["draft_id"])
        self.assertEqual("2026-07-01", payload["items"][0]["published_at"])
        self.assertEqual("institutional_trusted", payload["items"][0]["lane"])
        self.assertEqual(0, payload["items"][0]["document_priority"])
        self.assertFalse(payload["policy"]["autoapproval"])

    def test_decision_ledger_has_exactly_154_unique_ids(self):
        payload = json.loads(
            (ROOT / "data/staging/wartime-curation-decisions.json").read_text(
                encoding="utf-8"
            )
        )
        ids = [
            did
            for values in payload["decisions"].values()
            for did in values
        ]
        self.assertEqual(154, len(ids))
        self.assertEqual(154, len(set(ids)))


if __name__ == "__main__":
    unittest.main()
