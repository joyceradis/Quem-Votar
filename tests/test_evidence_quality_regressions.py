#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

collector = load("collector_quality", "coletor_evidencias.py")
discovery = load("discovery_quality", "discover_evidence_sources.py")
batch = load("batch_quality", "process_evidence_batch.py")
queue = load("queue_quality", "build_exception_queue.py")


def candidate(cid="123", name="MARIA SILVA"):
    return {
        "tse_id": cid,
        "ballot_name": name,
        "full_name": name,
        "office": "DEPUTADO FEDERAL",
        "party": "ABC",
        "current_mandate": None,
    }


class EvidenceQualityRegressionTests(unittest.TestCase):
    def test_linktree_blog_can_never_be_exact_content(self):
        self.assertFalse(
            discovery.looks_like_exact_content(
                "https://linktr.ee/blog/affiliate-marketing",
                "Everything you need to know about affiliate marketing",
            )
        )

    def test_linktree_uses_external_candidate_destination_not_blog(self):
        candidates = {"123": candidate()}
        seed = {
            "candidate_id": "123",
            "candidate_name": "MARIA SILVA",
            "seed_url": "https://linktr.ee/mariasilva",
            "discovery_status": "seed",
        }
        landing = b"""
        <html><body>
          <a href="https://linktr.ee/blog/affiliate-marketing">Blog Linktree</a>
          <a href="https://candidate.example/propostas/saude">Proposta de saude</a>
        </body></html>
        """

        with patch.object(
            discovery.collector,
            "fetch_bytes",
            return_value=(landing, "https://linktr.ee/mariasilva", "text/html; charset=utf-8"),
        ):
            found, rejected = discovery.discover_site(seed, candidates, 20)

        self.assertFalse(rejected)
        urls = {
            row.get("source_url") or row.get("seed_url")
            for row in found
        }
        self.assertNotIn("https://linktr.ee/blog/affiliate-marketing", urls)
        self.assertIn("https://candidate.example/propostas/saude", urls)
        exact = [x for x in found if x.get("discovery_status") == "exact_content"]
        self.assertEqual(1, len(exact))
        self.assertEqual(
            "link_aggregator_outbound_exact",
            exact[0]["source_origin"]["discovery_method"],
        )

    def test_dummy_text_is_rejected_before_draft(self):
        reason, disposition = collector.detect_content_quality_issue(
            title="14 de maio de 2026 Lorem Ipsum",
            text="Lorem Ipsum - Davi Esmael",
            source_kind="official_candidate",
        )
        self.assertEqual(("dummy_text", "reject"), (reason, disposition))

    def test_foreign_casino_seo_is_quarantined_but_portuguese_policy_text_is_not(self):
        reason, disposition = collector.detect_content_quality_issue(
            title="Meilleur Casino en ligne 2026 - Classement complet",
            text="Casino online bonus slot sites",
            source_kind="official_candidate",
        )
        self.assertEqual(("suspected_spam_content", "quarantine"), (reason, disposition))

        reason2, disposition2 = collector.detect_content_quality_issue(
            title="Projeto regulamenta cassinos no Brasil",
            text="O deputado apresentou projeto de lei sobre regulamentação de cassinos e fiscalização.",
            source_kind="official_candidate",
        )
        self.assertEqual(("", ""), (reason2, disposition2))

    def test_quality_rejection_becomes_permanent_processing_state(self):
        item = {
            "candidate_id": "123",
            "candidate_name": "MARIA SILVA",
            "source_kind": "official_candidate",
            "discovery_status": "exact_content",
            "source_url": "https://candidate.example/noticias/spam",
            "source_title": "Meilleur Casino en ligne 2026",
            "source_publisher": "candidate.example",
        }
        def fetch(url: str, **kwargs):
            body = b"<html><body><p>Casino online bonus slot sites free spins jackpot.</p></body></html>"
            return body, url, "text/html; charset=utf-8"

        state, drafts, failures, metrics = batch.run_batch(
            source_payload={"sources": [item]},
            candidates={"123": candidate()},
            existing_drafts=[],
            retries_per_run=1,
            workers=1,
            fetcher=fetch,
        )
        sid = batch.make_source_id(item)
        self.assertEqual("quarantined", state["sources"][sid]["status"])
        self.assertEqual(1, metrics["quarantined"])
        self.assertEqual(0, metrics["collected"])
        self.assertFalse(drafts)
        self.assertEqual("quarantined", failures[0]["processing_status"])

        _, _, _, second = batch.run_batch(
            source_payload={"sources": [item]},
            candidates={"123": candidate()},
            existing_drafts=[],
            state_payload=state,
            retries_per_run=1,
            workers=1,
            fetcher=fetch,
        )
        self.assertEqual(1, second["skipped_permanent"])
        self.assertEqual(0, second["queued"])

    def test_chamber_id_deputado_autor_sets_trusted_attribution(self):
        cand = candidate()
        cand["current_mandate"] = {
            "chamber_id": 999,
            "profile_url": "https://www.camara.leg.br/deputados/999",
        }
        def fake_json(url):
            return {
                "dados": [{
                    "id": 456,
                    "siglaTipo": "REQ",
                    "numero": 10,
                    "ano": 2026,
                    "ementa": "Requer audiência pública.",
                    "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/456",
                }]
            }
        sources, rejected = discovery.discover_chamber(
            {"123": cand},
            fetch_json=fake_json,
        )
        self.assertFalse(rejected)
        self.assertEqual("official_author_api", sources[0]["attribution_trust"])
        self.assertEqual(
            "api_idDeputadoAutor",
            sources[0]["source_origin"]["discovery_method"],
        )

    def test_trusted_chamber_draft_does_not_create_ambiguous_attribution(self):
        draft = {
            "draft_id": "d1",
            "candidate_id": "123",
            "candidate_name": "MARIA SILVA",
            "source_kind": "institutional",
            "source_url": "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=456",
            "candidate_mentioned": False,
            "published_at": "2026-01-01",
            "attribution_trust": "official_author_api",
            "source_origin": {
                "institution": "Câmara dos Deputados",
                "discovery_method": "api_idDeputadoAutor",
                "chamber_id": 999,
                "proposition_id": 456,
            },
        }
        payload = queue.build_queue(
            candidates={"123": candidate()},
            discovery_payload={"rejections": []},
            processing_payload={"failures": []},
            drafts_payload={"drafts": [draft]},
            observed_at="2026-09-20T15:00:00+00:00",
        )
        self.assertEqual(0, payload["metrics"]["human_review_open"])
        self.assertFalse(payload["exceptions"])

    def test_spam_exception_is_quarantine_not_human_review(self):
        payload = queue.build_queue(
            candidates={"123": candidate()},
            discovery_payload={"rejections": []},
            processing_payload={
                "failures": [{
                    "failure_id": "f1",
                    "candidate_id": "123",
                    "source_url": "https://candidate.example/spam",
                    "stage": "collection",
                    "error": "quality_quarantine:suspected_spam_content",
                    "processing_status": "quarantined",
                }]
            },
            drafts_payload={"drafts": []},
            observed_at="2026-09-20T15:00:00+00:00",
        )
        row = payload["exceptions"][0]
        self.assertEqual("suspected_spam_content", row["reason"])
        self.assertEqual("quarantine", row["disposition"])
        self.assertFalse(row["requires_human"])


if __name__ == "__main__":
    unittest.main()
