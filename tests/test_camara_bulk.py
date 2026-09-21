#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_curation_batch as batching
import build_exception_queue as exceptions
import camara_bulk
import coletor_evidencias as collector


def candidate(cid: str = "123", chamber_id: str = "999") -> dict:
    return {
        "tse_id": cid,
        "ballot_name": f"CANDIDATO {cid}",
        "full_name": f"CANDIDATO {cid}",
        "office": "DEPUTADO FEDERAL",
        "party": "TESTE",
        "current_mandate": {
            "chamber_id": chamber_id,
            "profile_url": f"https://www.camara.leg.br/deputados/{chamber_id}",
        },
    }


def bulk_meta(dataset: str, year: int = 2026) -> dict:
    return {
        "dataset": dataset,
        "year": year,
        "url": (
            f"https://dadosabertos.camara.leg.br/arquivos/{dataset}/csv/"
            f"{dataset}-{year}.csv"
        ),
        "final_url": (
            f"https://dadosabertos.camara.leg.br/arquivos/{dataset}/csv/"
            f"{dataset}-{year}.csv"
        ),
        "fetched_at": "2026-09-21T20:00:00+00:00",
        "sha256": (dataset.encode("utf-8").hex() + "0" * 64)[:64],
        "bytes": 100,
        "etag": "",
        "last_modified": "",
        "cache_hit": False,
    }


class CamaraBulkTests(unittest.TestCase):
    def test_bulk_join_preserves_official_type_themes_and_authorship_scope(self):
        candidates = {"123": candidate()}
        author_links = camara_bulk.collect_author_links(
            [
                camara_bulk.normalized_row(
                    {
                        "idProposicao": "10",
                        "uriAutor": "https://dadosabertos.camara.leg.br/api/v2/deputados/999",
                        "nomeAutor": "Candidato Teste",
                        "tipoAutor": "Deputado",
                    }
                )
            ],
            candidates=candidates,
        )
        propositions = camara_bulk.collect_propositions(
            [
                camara_bulk.normalized_row(
                    {
                        "id": "10",
                        "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/10",
                        "siglaTipo": "PL",
                        "numero": "42",
                        "ano": "2026",
                        "ementa": "Dispõe sobre matéria pública para teste.",
                        "dataApresentacao": "2026-08-01T12:00:00",
                    }
                )
            ],
            {"10"},
        )
        themes = camara_bulk.collect_themes(
            [
                camara_bulk.normalized_row(
                    {"idProposicao": "10", "codTema": "40", "tema": "Saúde"}
                ),
                camara_bulk.normalized_row(
                    {"idProposicao": "10", "codTema": "62", "tema": "Educação"}
                ),
            ],
            {"10"},
        )

        sources = camara_bulk.build_sources(
            candidates=candidates,
            year=2026,
            author_links=author_links,
            propositions=propositions,
            themes=themes,
            file_provenance=[
                bulk_meta("proposicoesAutores"),
                bulk_meta("proposicoes"),
                bulk_meta("proposicoesTemas"),
            ],
        )
        self.assertEqual(1, len(sources))
        row = sources[0]
        self.assertEqual("official_author_bulk", row["attribution_trust"])
        self.assertEqual(
            "bulk_proposicoesAutores_join",
            row["source_origin"]["discovery_method"],
        )
        self.assertEqual(
            "listed_author_signatory",
            row["source_origin"]["authorship_scope"],
        )
        self.assertEqual("PL", row["institutional_snapshot"]["siglaTipo"])
        self.assertEqual(
            [{"codTema": "40", "tema": "Saúde", "relevancia": ""},
             {"codTema": "62", "tema": "Educação", "relevancia": ""}],
            row["institutional_snapshot"]["official_themes"],
        )
        self.assertNotIn("topic_id", row)
        self.assertNotIn("review_status", row)

    def test_multiple_target_deputies_create_distinct_candidate_sources(self):
        candidates = {
            "123": candidate("123", "999"),
            "456": candidate("456", "888"),
        }
        author_links = camara_bulk.collect_author_links(
            [
                camara_bulk.normalized_row(
                    {
                        "idProposicao": "10",
                        "uriAutor": "https://dadosabertos.camara.leg.br/api/v2/deputados/999",
                    }
                ),
                camara_bulk.normalized_row(
                    {
                        "idProposicao": "10",
                        "uriAutor": "https://dadosabertos.camara.leg.br/api/v2/deputados/888",
                    }
                ),
            ],
            candidates=candidates,
        )
        propositions = {
            "10": {
                "id": "10",
                "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/10",
                "siglaTipo": "REQ",
                "codTipo": "",
                "numero": "1",
                "ano": "2026",
                "ementa": "Requer audiência pública para teste.",
                "dataApresentacao": "2026-08-01",
                "urlInteiroTeor": "",
                "keywords": "",
            }
        }
        sources = camara_bulk.build_sources(
            candidates=candidates,
            year=2026,
            author_links=author_links,
            propositions=propositions,
            themes={},
            file_provenance=[
                bulk_meta("proposicoesAutores"),
                bulk_meta("proposicoes"),
                bulk_meta("proposicoesTemas"),
            ],
        )
        self.assertEqual({"123", "456"}, {x["candidate_id"] for x in sources})
        self.assertEqual(2, len(sources))

    def test_missing_proposition_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "proposições autorais sem registro"):
            camara_bulk.build_sources(
                candidates={"123": candidate()},
                year=2026,
                author_links={
                    "999999": {
                        "123": {
                            "chamber_id": "999",
                            "author_name": "",
                            "author_uri": "",
                            "author_type": "",
                            "author_order": "",
                            "proponente": "",
                        }
                    }
                },
                propositions={},
                themes={},
                file_provenance=[
                    bulk_meta("proposicoesAutores"),
                    bulk_meta("proposicoes"),
                    bulk_meta("proposicoesTemas"),
                ],
            )

    def test_bulk_snapshot_materializes_without_html_fetch(self):
        source = camara_bulk.build_sources(
            candidates={"123": candidate()},
            year=2026,
            author_links={
                "10": {
                    "123": {
                        "chamber_id": "999",
                        "author_name": "Candidato Teste",
                        "author_uri": "https://dadosabertos.camara.leg.br/api/v2/deputados/999",
                        "author_type": "Deputado",
                        "author_order": "",
                        "proponente": "",
                    }
                }
            },
            propositions={
                "10": {
                    "id": "10",
                    "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/10",
                    "siglaTipo": "PL",
                    "codTipo": "",
                    "numero": "42",
                    "ano": "2026",
                    "ementa": "Dispõe sobre matéria pública para teste.",
                    "dataApresentacao": "2026-08-01",
                    "urlInteiroTeor": "",
                    "keywords": "",
                }
            },
            themes={
                "10": [{"codTema": "40", "tema": "Saúde", "relevancia": ""}]
            },
            file_provenance=[
                bulk_meta("proposicoesAutores"),
                bulk_meta("proposicoes"),
                bulk_meta("proposicoesTemas"),
            ],
        )[0]

        calls = []

        def forbidden_fetch(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("bulk snapshot must not refetch HTML")

        draft = collector.collect_source(
            source,
            candidates={"123": candidate()},
            fetcher=forbidden_fetch,
        )
        self.assertEqual([], calls)
        self.assertEqual("bulk_csv", draft["document_type"])
        self.assertEqual("official_author_bulk", draft["attribution_trust"])
        self.assertEqual("PL", draft["official_document_type"])
        self.assertEqual(
            [{"codTema": "40", "tema": "Saúde", "relevancia": ""}],
            draft["official_themes"],
        )

    def test_curation_batch_enriches_old_draft_from_latest_bulk_source(self):
        source = camara_bulk.build_sources(
            candidates={"123": candidate()},
            year=2026,
            author_links={
                "10": {
                    "123": {
                        "chamber_id": "999",
                        "author_name": "Candidato Teste",
                        "author_uri": "https://dadosabertos.camara.leg.br/api/v2/deputados/999",
                        "author_type": "Deputado",
                        "author_order": "",
                        "proponente": "",
                    }
                }
            },
            propositions={
                "10": {
                    "id": "10",
                    "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/10",
                    "siglaTipo": "PL",
                    "codTipo": "",
                    "numero": "42",
                    "ano": "2026",
                    "ementa": "Dispõe sobre matéria pública para teste.",
                    "dataApresentacao": "2026-08-01",
                    "urlInteiroTeor": "",
                    "keywords": "",
                }
            },
            themes={
                "10": [{"codTema": "40", "tema": "Saúde", "relevancia": ""}]
            },
            file_provenance=[
                bulk_meta("proposicoesAutores"),
                bulk_meta("proposicoes"),
                bulk_meta("proposicoesTemas"),
            ],
        )[0]

        old_draft = {
            "draft_id": "old-api-draft",
            "candidate_id": "123",
            "candidate_name": "CANDIDATO 123",
            "office": "DEPUTADO FEDERAL",
            "party": "TESTE",
            "source_kind": "institutional",
            "source_url": source["source_url"],
            "source_title": source["source_title"],
            "source_publisher": "Câmara dos Deputados",
            "published_at": "2026-08-01",
            "captured_at": "2026-09-20T00:00:00+00:00",
            "raw_excerpt": source["source_title"],
            "review_status": "pending",
            "source_origin": {
                "institution": "Câmara dos Deputados",
                "discovery_method": "api_idDeputadoAutor",
                "chamber_id": "999",
                "proposition_id": "10",
            },
            "attribution_trust": "official_author_api",
            "attribution_basis_hint": "old API binding",
        }

        batch, metrics = batching.build_batch(
            drafts_payload={"drafts": [old_draft]},
            canonical_payload={"entries": []},
            decisions_payload={"decisions": {}},
            sources_payload={"sources": [source]},
            limit=10,
            per_candidate_limit=10,
        )
        self.assertEqual(1, metrics["selected"])
        item = batch["items"][0]
        self.assertEqual("PL", item["official_document_type"])
        self.assertEqual("camara_bulk_daily", item["discovery_transport"])
        self.assertEqual(
            [{"codTema": "40", "tema": "Saúde", "relevancia": ""}],
            item["official_themes"],
        )
        self.assertEqual("institutional_trusted", item["lane"])
        self.assertEqual(0, item["document_priority"])
        self.assertFalse(batch["policy"]["autoapproval"])

    def test_nonprimary_official_type_is_retained_not_auto_rejected(self):
        row = {
            "draft_id": "emc-draft",
            "candidate_id": "123",
            "candidate_name": "CANDIDATO 123",
            "source_kind": "institutional",
            "source_url": (
                "https://www.camara.leg.br/proposicoesWeb/"
                "fichadetramitacao?idProposicao=20"
            ),
            "source_title": "EMC 1/2026 — Emenda de comissão para teste.",
            "source_publisher": "Câmara dos Deputados",
            "published_at": "2026-08-01",
            "review_status": "pending",
            "source_origin": {
                "institution": "Câmara dos Deputados",
                "discovery_method": "bulk_proposicoesAutores_join",
                "chamber_id": "999",
                "proposition_id": "20",
            },
            "attribution_trust": "official_author_bulk",
            "official_document_type": "EMC",
        }
        batch, metrics = batching.build_batch(
            drafts_payload={"drafts": [row]},
            canonical_payload={"entries": []},
            decisions_payload={"decisions": {}},
            sources_payload=None,
            limit=10,
            per_candidate_limit=10,
        )
        self.assertEqual(1, metrics["selected"])
        self.assertEqual(1, batch["items"][0]["document_priority"])
        self.assertEqual("EMC", batch["items"][0]["official_document_type"])

    def test_bulk_attribution_does_not_generate_ambiguous_human_exception(self):
        draft = {
            "draft_id": "bulk",
            "candidate_id": "123",
            "candidate_name": "CANDIDATO 123",
            "source_kind": "institutional",
            "source_url": (
                "https://www.camara.leg.br/proposicoesWeb/"
                "fichadetramitacao?idProposicao=10"
            ),
            "source_publisher": "Câmara dos Deputados",
            "review_status": "pending",
            "candidate_mentioned": False,
            "attribution_trust": "official_author_bulk",
            "source_origin": {
                "institution": "Câmara dos Deputados",
                "discovery_method": "bulk_proposicoesAutores_join",
                "chamber_id": "999",
                "proposition_id": "10",
            },
        }
        queue = exceptions.build_queue(
            candidates={"123": candidate()},
            discovery_payload={"rejections": []},
            processing_payload={"failures": []},
            drafts_payload={"drafts": [draft]},
        )
        human_reasons = {
            item["reason"]
            for item in queue["exceptions"]
            if item.get("queue_class") == "human_review"
        }
        self.assertNotIn("ambiguous_attribution", human_reasons)


if __name__ == "__main__":
    unittest.main()
