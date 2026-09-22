#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_curation_batch as batching
import build_exception_queue as exceptions
import camara_bulk
import coletor_evidencias as collector
import discover_evidence_sources as discovery


class FakeResponse:
    def __init__(self, body: bytes, url: str):
        self._body = body
        self._offset = 0
        self._url = url
        self.headers = {
            "Content-Length": str(len(body)),
            "Content-Type": "text/csv",
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def geturl(self):
        return self._url

    def read(self, size: int = -1):
        if self._offset >= len(self._body):
            return b""
        if size < 0:
            size = len(self._body) - self._offset
        chunk = self._body[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk


class SequencedOpener:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def open(self, request, timeout):
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


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
    def test_download_retries_transient_errors_but_not_permanent_http_errors(self):
        url = camara_bulk.bulk_url("proposicoesAutores", 2026)
        transient = urllib.error.HTTPError(url, 503, "busy", {}, None)
        permanent = urllib.error.HTTPError(url, 404, "missing", {}, None)

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            transient_opener = SequencedOpener(
                [transient, FakeResponse(b"idProposicao\n10\n", url)]
            )
            with (
                patch.object(
                    camara_bulk.urllib.request,
                    "build_opener",
                    return_value=transient_opener,
                ),
                patch.object(camara_bulk.collector, "validate_public_https_url"),
                patch("time.sleep"),
            ):
                _, meta = camara_bulk.download_bulk_csv(
                    "proposicoesAutores",
                    2026,
                    cache_dir=cache_dir,
                    retries=3,
                    timeout=20,
                )

            self.assertEqual(2, transient_opener.calls)
            self.assertEqual(2, meta["download_attempts"])

        with tempfile.TemporaryDirectory() as tmp:
            permanent_opener = SequencedOpener([permanent])
            with (
                patch.object(
                    camara_bulk.urllib.request,
                    "build_opener",
                    return_value=permanent_opener,
                ),
                patch.object(camara_bulk.collector, "validate_public_https_url"),
                patch("time.sleep"),
            ):
                with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
                    camara_bulk.download_bulk_csv(
                        "proposicoesAutores",
                        2026,
                        cache_dir=Path(tmp),
                        retries=3,
                        timeout=20,
                    )

            self.assertEqual(1, permanent_opener.calls)

    def test_fetch_bytes_retries_transient_errors_but_not_permanent_errors(self):
        url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
        transient_errors = (
            TimeoutError("timed out"),
            urllib.error.URLError(ConnectionRefusedError("connection refused")),
            urllib.error.HTTPError(url, 429, "too many requests", {}, None),
            urllib.error.HTTPError(url, 503, "unavailable", {}, None),
            urllib.error.HTTPError(url, 599, "network timeout", {}, None),
        )

        for transient in transient_errors:
            with self.subTest(transient=repr(transient)):
                opener = SequencedOpener(
                    [transient, FakeResponse(b'{"dados": []}', url)]
                )
                with (
                    patch.object(
                        collector.urllib.request,
                        "build_opener",
                        return_value=opener,
                    ),
                    patch.object(collector, "validate_public_https_url"),
                    patch.object(collector.time, "sleep") as sleep,
                ):
                    body, final_url, content_type = collector.fetch_bytes(
                        url,
                        retries=3,
                    )

                self.assertEqual(b'{"dados": []}', body)
                self.assertEqual(url, final_url)
                self.assertEqual("text/csv", content_type)
                self.assertEqual(2, opener.calls)
                sleep.assert_called_once_with(1)

        for code in (404, 408):
            with self.subTest(permanent_http=code):
                permanent_http = urllib.error.HTTPError(
                    url, code, "permanent client error", {}, None
                )
                permanent_opener = SequencedOpener([permanent_http])
                with (
                    patch.object(
                        collector.urllib.request,
                        "build_opener",
                        return_value=permanent_opener,
                    ),
                    patch.object(collector, "validate_public_https_url"),
                    patch.object(collector.time, "sleep") as permanent_sleep,
                ):
                    with self.assertRaisesRegex(RuntimeError, f"HTTP {code}"):
                        collector.fetch_bytes(url, retries=3)

                self.assertEqual(1, permanent_opener.calls)
                permanent_sleep.assert_not_called()

        oversized_opener = SequencedOpener([FakeResponse(b"too large", url)])
        with (
            patch.object(
                collector.urllib.request,
                "build_opener",
                return_value=oversized_opener,
            ),
            patch.object(collector, "validate_public_https_url"),
            patch.object(collector.time, "sleep") as local_error_sleep,
        ):
            with self.assertRaisesRegex(RuntimeError, "resposta excede limite"):
                collector.fetch_bytes(url, max_bytes=1, retries=3)

        self.assertEqual(1, oversized_opener.calls)
        local_error_sleep.assert_not_called()

    def test_fetch_bytes_stops_after_retry_limit(self):
        url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
        opener = SequencedOpener(
            [
                TimeoutError("attempt 1"),
                TimeoutError("attempt 2"),
                TimeoutError("attempt 3"),
            ]
        )

        with (
            patch.object(
                collector.urllib.request,
                "build_opener",
                return_value=opener,
            ),
            patch.object(collector, "validate_public_https_url"),
            patch.object(collector.time, "sleep") as sleep,
        ):
            with self.assertRaisesRegex(RuntimeError, "timeout"):
                collector.fetch_bytes(url, retries=3)

        self.assertEqual(3, opener.calls)
        self.assertEqual([((1,), {}), ((2,), {})], sleep.call_args_list)

    def test_bulk_isolates_dataset_failure_and_processes_newest_year_first(self):
        calls = []

        def fake_download(dataset, year, *, cache_dir, **kwargs):
            calls.append((dataset, year))
            if dataset == "proposicoesTemas" and year == 2025:
                raise RuntimeError("proposicoesTemas-2025: timeout")

            path = cache_dir / f"{dataset}-{year}.csv"
            proposition_id = str(year)
            if dataset == "proposicoesAutores":
                content = (
                    "idProposicao,uriAutor\n"
                    f"{proposition_id},https://dadosabertos.camara.leg.br/api/v2/deputados/999\n"
                )
            elif dataset == "proposicoes":
                content = (
                    "id,uri,siglaTipo,numero,ano,ementa,dataApresentacao\n"
                    f"{proposition_id},https://dadosabertos.camara.leg.br/api/v2/proposicoes/{proposition_id},"
                    f"PL,1,{year},Teste do ano {year},{year}-01-01\n"
                )
            else:
                content = f"idProposicao,codTema,tema\n{proposition_id},40,Saúde\n"
            path.write_text(content, encoding="utf-8")
            return path, bulk_meta(dataset, year)

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(camara_bulk, "download_bulk_csv", side_effect=fake_download):
                sources, report = camara_bulk.discover_chamber_bulk(
                    {"123": candidate()},
                    cache_dir=Path(tmp),
                    years=(2023, 2024, 2025, 2026),
                )

        self.assertEqual(
            [
                ("proposicoesAutores", 2026),
                ("proposicoes", 2026),
                ("proposicoesTemas", 2026),
                ("proposicoesAutores", 2025),
                ("proposicoes", 2025),
                ("proposicoesTemas", 2025),
                ("proposicoesAutores", 2024),
                ("proposicoes", 2024),
                ("proposicoesTemas", 2024),
                ("proposicoesAutores", 2023),
                ("proposicoes", 2023),
                ("proposicoesTemas", 2023),
            ],
            calls,
        )
        self.assertEqual([2026, 2025, 2024, 2023], report["years"])
        self.assertEqual([2025], report["failed_years"])
        self.assertEqual(
            {"2026", "2024", "2023"},
            {row["institutional_snapshot"]["ano"] for row in sources},
        )
        failed = next(row for row in report["year_reports"] if row["year"] == 2025)
        self.assertEqual("failed", failed["status"])
        failed_dataset = next(
            row for row in failed["datasets"] if row["dataset"] == "proposicoesTemas"
        )
        self.assertEqual("failed", failed_dataset["status"])

    def test_discover_chamber_paginates_every_page_for_exact_year(self):
        candidates = {"123": candidate()}
        requested = []

        def fake_json(url):
            requested.append(url)
            if "pagina=2" in url:
                return {
                    "dados": [{"id": 11, "siglaTipo": "PL", "numero": 2, "ano": 2026}],
                    "links": [],
                }
            return {
                "dados": [{"id": 10, "siglaTipo": "PL", "numero": 1, "ano": 2026}],
                "links": [{"rel": "next", "href": "https://dadosabertos.camara.leg.br/api/v2/proposicoes?pagina=2"}],
            }

        sources, rejected = discovery.discover_chamber(
            candidates,
            fetch_json=fake_json,
            exact_years=(2026,),
        )

        first_query = urllib.parse.parse_qs(urllib.parse.urlsplit(requested[0]).query)
        self.assertEqual(["2026"], first_query["ano"])
        self.assertEqual(2, len(requested))
        self.assertEqual({"10", "11"}, {
            str(row["source_origin"]["proposition_id"]) for row in sources
        })
        self.assertEqual([], rejected)

    def test_discover_chamber_paginates_every_page_without_exact_years(self):
        candidates = {"123": candidate()}
        requested = []

        def fake_json(url):
            requested.append(url)
            if "pagina=2" in url:
                return {
                    "dados": [
                        {"id": 11, "siglaTipo": "PL", "numero": 2, "ano": 2025},
                        {"id": 12, "siglaTipo": "PL", "numero": 3, "ano": 2022},
                    ],
                    "links": [],
                }
            return {
                "dados": [
                    {"id": 10, "siglaTipo": "PL", "numero": 1, "ano": 2026}
                ],
                "links": [
                    {
                        "rel": "next",
                        "href": (
                            "https://dadosabertos.camara.leg.br/api/v2/"
                            "proposicoes?pagina=2"
                        ),
                    }
                ],
            }

        sources, rejected = discovery.discover_chamber(
            candidates,
            fetch_json=fake_json,
            min_year=2023,
        )

        first_query = urllib.parse.parse_qs(urllib.parse.urlsplit(requested[0]).query)
        self.assertNotIn("ano", first_query)
        self.assertEqual(2, len(requested))
        self.assertEqual(
            {"10", "11"},
            {str(row["source_origin"]["proposition_id"]) for row in sources},
        )
        self.assertEqual([], rejected)

    def test_discover_chamber_discards_candidate_year_when_page_two_fails(self):
        candidates = {"123": candidate()}

        def fake_json(url):
            if "pagina=2" in url:
                raise TimeoutError("page two timed out")
            return {
                "dados": [{"id": 10, "siglaTipo": "PL", "numero": 1, "ano": 2026}],
                "links": [{"rel": "next", "href": "https://dadosabertos.camara.leg.br/api/v2/proposicoes?pagina=2"}],
            }

        sources, rejected = discovery.discover_chamber(
            candidates,
            fetch_json=fake_json,
            exact_years=(2026,),
        )

        self.assertEqual([], sources)
        self.assertEqual(1, len(rejected))
        self.assertEqual("chamber_discovery_failed", rejected[0]["reason"])
        self.assertIn("year=2026", rejected[0]["detail"])

    def test_discover_chamber_discards_candidate_year_on_cross_year_record(self):
        candidates = {"123": candidate()}

        sources, rejected = discovery.discover_chamber(
            candidates,
            fetch_json=lambda url: {
                "dados": [{"id": 10, "siglaTipo": "PL", "numero": 1, "ano": 2025}],
                "links": [],
            },
            exact_years=(2026,),
        )

        self.assertEqual([], sources)
        self.assertEqual(1, len(rejected))
        self.assertIn("expected year 2026", rejected[0]["detail"])

    def test_run_discovery_calls_api_only_for_failed_bulk_year(self):
        candidates = {"123": candidate()}
        bulk_source = {
            "candidate_id": "123",
            "candidate_name": "CANDIDATO 123",
            "source_kind": "institutional",
            "discovery_status": "exact_content",
            "source_url": "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2026",
        }
        api_source = {
            **bulk_source,
            "source_url": "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2025",
        }
        fallback_calls = []

        def fake_bulk(*args, **kwargs):
            return [bulk_source], {
                "mode": "camara_bulk_daily",
                "failed_years": [2025],
                "year_reports": [],
                "source_records": 1,
            }

        def fake_api(api_candidates, *, exact_years):
            fallback_calls.append(tuple(exact_years))
            return [api_source], []

        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(discovery, "declared_seed_sources", return_value=([], [], {})),
                patch.object(discovery.camara_bulk, "discover_chamber_bulk", side_effect=fake_bulk),
                patch.object(discovery, "discover_chamber", side_effect=fake_api),
            ):
                payload, _, metrics = discovery.run_discovery(
                    candidates=candidates,
                    existing_sources=[],
                    discover_sites=False,
                    chamber_bulk_cache_dir=Path(tmp),
                    chamber_bulk_years=(2023, 2024, 2025, 2026),
                )

        self.assertEqual([(2025,)], fallback_calls)
        self.assertEqual(2, len(payload["sources"]))
        provenance = payload["discovery_run"]["chamber_provenance"]
        self.assertEqual([2025], provenance["api_fallback_years"])
        self.assertEqual("camara_bulk_partial_api_fallback", provenance["mode"])
        self.assertEqual("camara_bulk_partial_api_fallback", metrics["chamber_transport_mode"])

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
