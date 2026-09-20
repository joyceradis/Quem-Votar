#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "discover_evidence_sources.py"
SPEC = importlib.util.spec_from_file_location("discover_evidence_sources", MODULE)
discovery = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(discovery)


class DiscoveryTests(unittest.TestCase):
    def candidate(self):
        return {
            "tse_id": "123",
            "ballot_name": "MARIA SILVA",
            "full_name": "MARIA DA SILVA",
            "social_name": None,
            "office": "DEPUTADO FEDERAL",
            "party": "ABC",
            "current_mandate": None,
        }

    def test_ambiguous_handle_is_not_guessed(self):
        self.assertEqual(("", ""), discovery.normalize_declared_value("@maria"))

    def test_explicit_platform_handle_is_normalized(self):
        url, basis = discovery.normalize_declared_value("INSTAGRAM: @maria.silva")
        self.assertEqual("https://www.instagram.com/maria.silva", url)
        self.assertEqual("explicit_instagram_handle", basis)

    def test_tracking_parameters_are_removed(self):
        url = discovery.canonicalize_url(
            "HTTPS://Example.org/propostas/saude/?utm_source=x&b=2&a=1#top"
        )
        self.assertEqual("https://example.org/propostas/saude?a=1&b=2", url)

    def test_generic_landing_is_not_exact_content(self):
        self.assertFalse(discovery.looks_like_exact_content("https://example.org/propostas"))
        self.assertTrue(discovery.looks_like_exact_content("https://example.org/propostas/saude"))
        self.assertTrue(discovery.looks_like_exact_content("https://example.org/plano-de-governo.pdf"))

    def test_site_discovery_only_emits_same_host_specific_links(self):
        candidate = self.candidate()
        candidates = {"123": candidate}
        seed = {
            "candidate_id": "123",
            "candidate_name": "MARIA SILVA",
            "seed_url": "https://example.org/",
            "discovery_status": "seed",
        }
        html = b"""
        <html><body>
          <a href="/propostas">Propostas</a>
          <a href="/propostas/saude">Saude</a>
          <a href="https://other.test/propostas/educacao">Outro</a>
          <a href="/contato">Contato</a>
        </body></html>
        """
        with patch.object(
            discovery.collector,
            "fetch_bytes",
            return_value=(html, "https://example.org/", "text/html; charset=utf-8"),
        ):
            exact, rejected = discovery.discover_site(seed, candidates, 20)
        self.assertFalse(rejected)
        self.assertEqual(1, len(exact))
        self.assertEqual("https://example.org/propostas/saude", exact[0]["source_url"])
        self.assertEqual("exact_content", exact[0]["discovery_status"])

    def test_chamber_discovery_uses_candidate_chamber_id(self):
        candidate = self.candidate()
        candidate["current_mandate"] = {
            "chamber_id": 999,
            "profile_url": "https://www.camara.leg.br/deputados/999",
        }
        candidates = {"123": candidate}

        def fake_json(url):
            self.assertIn("idDeputadoAutor=999", url)
            return {
                "dados": [
                    {
                        "id": 456,
                        "siglaTipo": "PL",
                        "numero": 10,
                        "ano": 2026,
                        "ementa": "Dispõe sobre tema de teste.",
                        "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/456",
                    }
                ]
            }

        sources, rejected = discovery.discover_chamber(candidates, fetch_json=fake_json)
        self.assertFalse(rejected)
        self.assertEqual(1, len(sources))
        self.assertEqual("institutional", sources[0]["source_kind"])
        self.assertIn("idProposicao=456", sources[0]["source_url"])

    def test_dedupe_keeps_seed_and_exact_as_distinct_states(self):
        rows = [
            {"candidate_id": "123", "discovery_status": "seed", "seed_url": "https://x.test/p?a=1&utm_source=x"},
            {"candidate_id": "123", "discovery_status": "seed", "seed_url": "https://x.test/p?a=1"},
            {"candidate_id": "123", "discovery_status": "exact_content", "source_url": "https://x.test/p?a=1"},
        ]
        result = discovery.dedupe_sources(rows)
        self.assertEqual(2, len(result))


if __name__ == "__main__":
    unittest.main()
