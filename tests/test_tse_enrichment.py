#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync-data.py"
SPEC = importlib.util.spec_from_file_location("sync_data_issue86", MODULE_PATH)
sync = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync
assert SPEC.loader is not None
SPEC.loader.exec_module(sync)

BOOTSTRAP_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "bootstrap-tse-enrichment.py"
)
BOOTSTRAP_SPEC = importlib.util.spec_from_file_location(
    "bootstrap_tse_enrichment_issue86",
    BOOTSTRAP_MODULE_PATH,
)
bootstrap = importlib.util.module_from_spec(BOOTSTRAP_SPEC)
sys.modules[BOOTSTRAP_SPEC.name] = bootstrap
assert BOOTSTRAP_SPEC.loader is not None
BOOTSTRAP_SPEC.loader.exec_module(bootstrap)


def zip_csv(name: str, body: str) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, body.encode("cp1252"))
    return data.getvalue()


class TseEnrichmentTests(unittest.TestCase):
    def test_bootstrap_social_links_normalize_query_and_deduplicate_real_case(self):
        html = """
        <h2 id="canais">Canais</h2>
        <ul class="canais">
          <li><a href="https://instagram.com/cezar.lazaroo?IGSH=MTDJEDJHODN0CMP6YG==">Instagram 1</a></li>
          <li><a href="https://instagram.com/cezar.lazaroo?igsh=mtdjedjhodn0cmp6yg==">Instagram 2</a></li>
        </ul>
        <h2 id="historico">Histórico</h2>
        """
        self.assertEqual(
            ["https://instagram.com/cezar.lazaroo?igsh=MTDJEDJHODN0CMP6YG=="],
            bootstrap.extract_social_links(html),
        )

    def test_bootstrap_history_exposes_uf_from_official_divulga_url(self):
        html = """
        <h2 id="historico">Histórico</h2>
        <table>
          <caption>Candidaturas anteriores desta pessoa</caption>
          <tbody>
            <tr>
              <td>2020</td>
              <td>Vereador</td>
              <td>REPUBLICANOS</td>
              <td>Pancas</td>
              <td>96</td>
              <td>—</td>
              <td>Suplente</td>
              <td><a href="https://divulgacandcontas.tse.jus.br/divulga/#/candidato/SUDESTE/ES/2030402020/80001208438/2020/56790">TSE</a></td>
            </tr>
          </tbody>
        </table>
        """
        records = bootstrap.extract_history(html)
        self.assertEqual(1, len(records))
        self.assertEqual("Pancas", records[0]["location"])
        self.assertEqual("ES", records[0]["uf"])

    def test_reads_es_partition_and_provenance(self):
        raw = zip_csv(
            "bem_candidato_2026_ES.csv",
            "DT_GERACAO;HH_GERACAO;SQ_CANDIDATO;VR_BEM_CANDIDATO\n"
            "21/09/2026;12:00:00;80000000001;10,50\n",
        )
        with patch.object(sync, "request_bytes", return_value=raw):
            rows, meta = sync.read_tse_archive(
                sync.TSE_ASSETS_ZIP,
                "bem_candidato_2026_ES.csv",
            )
        self.assertEqual("80000000001", rows[0]["SQ_CANDIDATO"])
        self.assertEqual("21/09/2026 12:00:00", meta["generated_at"])
        self.assertEqual("fresh", meta["status"])
        self.assertEqual(64, len(meta["sha256"]))

    def test_enrichment_joins_only_by_sq_candidato(self):
        candidates = [{
            "tse_id": "80000000001",
            "ballot_name": "ANA",
            "full_name": "ANA TESTE",
            "social_name": None,
            "registration_status": None,
            "assets": {},
            "social_links": [],
            "previous_elections": [],
            "tse_additional": {},
        }]
        complement = [{
            "SQ_CANDIDATO": "80000000001",
            "DS_SITUACAO_JULGAMENTO": "DEFERIDO",
            "DT_ACEITE_CANDIDATURA": "2026-08-01 10:00:00",
            "ST_DECLARAR_BENS": "S",
        }]
        assets = [{
            "SQ_CANDIDATO": "80000000001",
            "NR_ORDEM_BEM_CANDIDATO": "1",
            "DS_TIPO_BEM_CANDIDATO": "Casa",
            "DS_BEM_CANDIDATO": "IMÓVEL",
            "VR_BEM_CANDIDATO": "100000,50",
            "DT_ULT_ATUAL_BEM_CANDIDATO": "20/09/2026",
        }]
        social = [
            {"SQ_CANDIDATO": "80000000001", "DS_URL": "HTTPS://EXAMPLE.COM/PERFIL"},
            {"SQ_CANDIDATO": "999", "DS_URL": "https://example.com/outro"},
        ]
        history = [
            {
                "SQ_CANDIDATO_ATUAL": "80000000001",
                "ANO_ELEICAO": "2022",
                "DS_CARGO": "DEPUTADO FEDERAL",
                "SG_PARTIDO": "ABC",
                "SG_UF": "ES",
                "DS_SIT_TOT_TURNO": "NÃO ELEITO",
            },
            {
                "SQ_CANDIDATO_ATUAL": "80000000001",
                "ANO_ELEICAO": "2026",
                "DS_CARGO": "DEPUTADO FEDERAL",
                "SG_PARTIDO": "XYZ",
                "SG_UF": "ES",
                "DS_SIT_TOT_TURNO": "#NULO",
            },
        ]
        datasets = {
            sync.TSE_COMPLEMENT_ZIP: complement,
            sync.TSE_ASSETS_ZIP: assets,
            sync.TSE_SOCIAL_ZIP: social,
            sync.TSE_HISTORY_ZIP: history,
        }

        def fake_archive(url, preferred_suffix=None, timeout=90):
            return datasets[url], {
                "institution": "TSE",
                "url": url,
                "archive_member": preferred_suffix or "historico.csv",
                "sha256": "a" * 64,
                "generated_at": "21/09/2026 12:00:00",
                "row_count": len(datasets[url]),
                "status": "fresh",
            }

        with patch.object(sync, "read_tse_archive", side_effect=fake_archive), patch.object(
            sync, "_previous_candidate_map", return_value={}
        ), patch.object(
            sync, "_load_enrichment_bootstrap", return_value=({}, None)
        ):
            meta, counts = sync.enrich_tse_open_data([candidates])

        candidate = candidates[0]
        self.assertEqual("DEFERIDO", candidate["registration_status"])
        self.assertEqual(100000.50, candidate["assets"]["total_declared_brl"])
        self.assertEqual(1, candidate["assets"]["count"])
        self.assertEqual(["https://example.com/PERFIL"], candidate["social_links"])
        self.assertEqual(1, len(candidate["previous_elections"]))
        self.assertEqual(2022, candidate["previous_elections"][0]["year"])
        self.assertEqual("SQ_CANDIDATO_ATUAL", meta["candidate_history"]["join_field"])
        self.assertEqual(1, counts["asset_records"])
        self.assertEqual(1, counts["social_links"])
        self.assertEqual(1, counts["previous_election_records"])

    def test_personal_identifiers_are_not_exported_by_complement(self):
        candidates = [{
            "tse_id": "80000000001",
            "registration_status": None,
            "assets": {},
            "social_links": [],
            "previous_elections": [],
            "tse_additional": {},
        }]
        complement = [{
            "SQ_CANDIDATO": "80000000001",
            "DS_SITUACAO_JULGAMENTO": "DEFERIDO",
            "NR_PROCESSO": "SECRET",
            "NR_PROTOCOLO_CANDIDATURA": "SECRET",
            "NR_CPF_CANDIDATO": "00000000000",
            "DS_EMAIL": "private@example.com",
            "ST_DECLARAR_BENS": "N",
        }]
        datasets = {
            sync.TSE_COMPLEMENT_ZIP: complement,
            sync.TSE_ASSETS_ZIP: [{"SQ_CANDIDATO": "80000000001", "NR_ORDEM_BEM_CANDIDATO": "1", "VR_BEM_CANDIDATO": "1,00"}],
            sync.TSE_SOCIAL_ZIP: [{"SQ_CANDIDATO": "80000000001", "DS_URL": "https://example.com"}],
            sync.TSE_HISTORY_ZIP: [{"SQ_CANDIDATO_ATUAL": "80000000001", "ANO_ELEICAO": "2022", "DS_CARGO": "VEREADOR"}],
        }
        def fake_archive(url, preferred_suffix=None, timeout=90):
            return datasets[url], {"institution": "TSE", "url": url, "status": "fresh", "sha256": "b"*64, "row_count": len(datasets[url])}
        with patch.object(sync, "read_tse_archive", side_effect=fake_archive), patch.object(
            sync, "_previous_candidate_map", return_value={}
        ), patch.object(
            sync, "_load_enrichment_bootstrap", return_value=({}, None)
        ):
            sync.enrich_tse_open_data([candidates])

        exported = str(candidates[0]).lower()
        self.assertNotIn("cpf", exported)
        self.assertNotIn("email", exported)
        self.assertNotIn("processo", exported)
        self.assertNotIn("protocolo", exported)


def _entry(cid: str, sha: str = "a", sync: str = "16/09/2026 às 16:35", **extra) -> dict:
    return {
        "candidate_id": cid,
        "transport_url": f"https://meuvoto.org.br/candidato/{cid}.html",
        "transport_sha256": sha * 64,
        "source_sync_at": sync,
        "official_candidate_url": f"https://divulgacandcontas.tse.jus.br/divulga/#/candidato/SUDESTE/ES/1/{cid}/2026/ES",
        "assets": {"total_declared_brl": None, "count": 0, "items": []},
        "social_links": [],
        "previous_elections": [],
        **extra,
    }


def _page(cid: str, sections=("patrimonio", "canais", "historico"), identification: str = "") -> bytes:
    body = "".join(f'<h2 id="{sid}">x</h2><p>sem registros</p>' for sid in sections)
    return (
        f'<html><body data-salvar="{cid}" data-quando="16/09/2026 às 16:35">{identification}{body}'
        f'<a href="https://divulgacandcontas.tse.jus.br/divulga/#/candidato/SUDESTE/ES/1/{cid}/2026/ES">tse</a>'
        "</body></html>"
    ).encode("utf-8")


def _declared_previous(count: int) -> str:
    """Trecho da identificação como o MeuVoto o publica (visto no run 36618481606)."""
    note = "primeira disputa mapeada" if count == 0 else f"desde 2004"
    return (
        f'<dl><div>\n<dt>Eleições anteriores</dt>\n<dd>{count}</dd>\n'
        f'<dd class="perfil-exato">{note}</dd>\n</div></dl>'
    )


class _FakeResponse:
    def __init__(self, raw: bytes):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.raw


class BootstrapMajoritarianCoverageTests(unittest.TestCase):
    def test_universe_covers_the_four_offices(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, name in enumerate(bootstrap.OFFICE_SNAPSHOT_FILES):
                (root / name).write_text(json.dumps([{"tse_id": 100 + index}]), encoding="utf-8")
            with patch.object(bootstrap, "GENERATED", root):
                self.assertEqual(["100", "101", "102", "103"], bootstrap.current_candidate_ids())

    def test_missing_office_snapshot_fails_closed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp, patch.object(bootstrap, "GENERATED", Path(tmp)):
            with self.assertRaises(FileNotFoundError):
                bootstrap.current_candidate_ids()

    def test_merge_keeps_existing_entries_and_recomputes_aggregate(self):
        old_a, old_b = _entry("1", "a"), _entry("3", "b")
        existing = {
            "version": "1.0.0",
            "captured_at": "2026-09-21T22:42:54+00:00",
            "source": {"observed_source_sync_at": ["16/09/2026 às 16:35"], "candidate_count": 2},
            "entries": [old_a, old_b],
        }
        new = _entry("2", "c", sync="28/09/2026 às 10:00", captured_at="2026-09-29T20:00:00+00:00")
        merged = bootstrap.merge_payload(existing, [new])

        self.assertEqual(["1", "2", "3"], [e["candidate_id"] for e in merged["entries"]])
        self.assertIs(merged["entries"][0], old_a)  # entradas existentes passam intactas
        self.assertIs(merged["entries"][2], old_b)
        self.assertEqual(3, merged["source"]["candidate_count"])
        self.assertEqual(bootstrap.aggregate_sha256(merged["entries"]), merged["source"]["aggregate_sha256"])
        self.assertEqual(
            ["16/09/2026 às 16:35", "28/09/2026 às 10:00"],
            merged["source"]["observed_source_sync_at"],
        )
        # captura nova não rejuvenesce a antiga
        self.assertEqual("2026-09-21T22:42:54+00:00", merged["captured_at"])

    def test_merge_never_overwrites_an_existing_entry(self):
        existing = {"source": {}, "entries": [_entry("1")]}
        with self.assertRaisesRegex(RuntimeError, "não sobrescreve"):
            bootstrap.merge_payload(existing, [_entry("1", "z")])

    def test_committed_bootstrap_is_stable_and_reproducible(self):
        import json

        path = Path(__file__).resolve().parents[1] / "data" / "reference" / "tse-enrichment-bootstrap.json"
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        self.assertEqual(raw, bootstrap.dump_payload(payload))  # merge não reformata o que já existe
        self.assertEqual(payload["source"]["aggregate_sha256"], bootstrap.aggregate_sha256(payload["entries"]))
        self.assertEqual(payload["source"]["candidate_count"], len(payload["entries"]))

    def test_unexpected_page_structure_is_not_recorded_as_zero(self):
        raw = _page("55", sections=("patrimonio",))  # sem canais/historico
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=_FakeResponse(raw)), patch.object(
            bootstrap.time, "sleep"
        ):
            with self.assertRaisesRegex(RuntimeError, "estrutura inesperada"):
                bootstrap.fetch_candidate("55", require_sections=True)

    def test_page_with_sections_and_no_records_is_a_legitimate_empty(self):
        raw = _page("56")
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=_FakeResponse(raw)):
            entry = bootstrap.fetch_candidate("56", require_sections=True, captured_at="2026-09-29T20:00:00+00:00")
        self.assertEqual(0, entry["assets"]["count"])
        self.assertEqual([], entry["social_links"])
        self.assertEqual("2026-09-29T20:00:00+00:00", entry["captured_at"])

    def test_first_time_candidate_without_history_section_is_a_declared_empty(self):
        # 4 dos 16 majoritários (run 36618481606): sem seção "historico", e a
        # própria página declara "Eleições anteriores: 0 — primeira disputa mapeada".
        raw = _page("58", sections=("patrimonio", "canais"), identification=_declared_previous(0))
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=_FakeResponse(raw)):
            entry = bootstrap.fetch_candidate("58", require_sections=True)
        self.assertEqual([], entry["previous_elections"])
        self.assertEqual(0, entry["assets"]["count"])

    def test_missing_history_section_with_declared_previous_elections_is_rejected(self):
        raw = _page("59", sections=("patrimonio", "canais"), identification=_declared_previous(3))
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=_FakeResponse(raw)), patch.object(
            bootstrap.time, "sleep"
        ):
            with self.assertRaisesRegex(RuntimeError, "estrutura inesperada"):
                bootstrap.fetch_candidate("59", require_sections=True)

    def test_missing_history_section_without_declaration_is_rejected(self):
        raw = _page("60", sections=("patrimonio", "canais"))
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=_FakeResponse(raw)), patch.object(
            bootstrap.time, "sleep"
        ):
            with self.assertRaisesRegex(RuntimeError, "estrutura inesperada"):
                bootstrap.fetch_candidate("60", require_sections=True)

    def test_declared_zero_does_not_excuse_other_missing_sections(self):
        for sections in (("canais",), ("patrimonio",), ()):
            raw = _page("61", sections=sections, identification=_declared_previous(0))
            with patch.object(bootstrap.urllib.request, "urlopen", return_value=_FakeResponse(raw)), patch.object(
                bootstrap.time, "sleep"
            ):
                with self.assertRaisesRegex(RuntimeError, "estrutura inesperada"):
                    bootstrap.fetch_candidate("61", require_sections=True)

    def test_declared_previous_elections_parses_only_the_explicit_count(self):
        self.assertEqual(0, bootstrap.declared_previous_elections(_declared_previous(0)))
        self.assertEqual(8, bootstrap.declared_previous_elections(_declared_previous(8)))
        self.assertIsNone(bootstrap.declared_previous_elections("<p>Eleições anteriores</p>"))
        self.assertIsNone(bootstrap.declared_previous_elections("<dt>Eleições anteriores</dt><dd>—</dd>"))

    def test_page_for_another_candidate_is_rejected(self):
        raw = _page("999")
        with patch.object(bootstrap.urllib.request, "urlopen", return_value=_FakeResponse(raw)), patch.object(
            bootstrap.time, "sleep"
        ):
            with self.assertRaisesRegex(RuntimeError, "SQ_CANDIDATO esperado"):
                bootstrap.fetch_candidate("57", require_sections=True)

    def test_merge_missing_reports_failures_and_writes_only_successes(self):
        import json
        import tempfile
        from contextlib import redirect_stdout

        existing = {
            "version": "1.0.0",
            "captured_at": "2026-09-21T22:42:54+00:00",
            "source": {"observed_source_sync_at": [], "candidate_count": 1, "aggregate_sha256": "x"},
            "entries": [_entry("1")],
        }

        def fake_fetch(cid, **kwargs):
            if cid == "3":
                raise RuntimeError("3: HTTPError: HTTP Error 404: Not Found")
            return _entry(cid, "d", captured_at=kwargs.get("captured_at"))

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bootstrap.json"
            out.write_text(bootstrap.dump_payload(existing), encoding="utf-8")
            with patch.object(bootstrap, "OUT", out), patch.object(
                bootstrap, "current_candidate_ids", return_value=["1", "2", "3"]
            ), patch.object(bootstrap, "fetch_candidate", side_effect=fake_fetch):
                with redirect_stdout(io.StringIO()) as buffer:
                    code = bootstrap.run_merge_missing(strict=False)
                self.assertEqual(0, code)
                written = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual(["1", "2"], [e["candidate_id"] for e in written["entries"]])
                summary = json.loads(buffer.getvalue())
                self.assertEqual(["2"], summary["fetched"])
                self.assertEqual("3", summary["failed"][0]["candidate_id"])
                self.assertIn("404", summary["failed"][0]["error"])

                # --strict: mesma coleta, mas a falha derruba o job
                out.write_text(bootstrap.dump_payload(existing), encoding="utf-8")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(1, bootstrap.run_merge_missing(strict=True))

    def test_merge_missing_with_nothing_to_do_does_not_touch_the_file(self):
        import tempfile
        from contextlib import redirect_stdout

        existing = {"source": {"candidate_count": 1}, "entries": [_entry("1")]}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bootstrap.json"
            out.write_text(bootstrap.dump_payload(existing), encoding="utf-8")
            before = out.read_bytes()
            with patch.object(bootstrap, "OUT", out), patch.object(
                bootstrap, "current_candidate_ids", return_value=["1"]
            ):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(0, bootstrap.run_merge_missing(strict=True))
            self.assertEqual(before, out.read_bytes())

    def test_merge_missing_rejects_ids_outside_the_current_universe(self):
        import tempfile
        from contextlib import redirect_stdout

        existing = {"source": {"candidate_count": 2}, "entries": [_entry("1"), _entry("9")]}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bootstrap.json"
            out.write_text(bootstrap.dump_payload(existing), encoding="utf-8")
            with patch.object(bootstrap, "OUT", out), patch.object(
                bootstrap, "current_candidate_ids", return_value=["1", "2"]
            ):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "fora do universo"):
                        bootstrap.run_merge_missing(strict=False)


if __name__ == "__main__":
    unittest.main()
