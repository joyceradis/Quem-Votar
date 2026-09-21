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


def zip_csv(name: str, body: str) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, body.encode("cp1252"))
    return data.getvalue()


class TseEnrichmentTests(unittest.TestCase):
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
        ):
            sync.enrich_tse_open_data([candidates])

        exported = str(candidates[0]).lower()
        self.assertNotIn("cpf", exported)
        self.assertNotIn("email", exported)
        self.assertNotIn("processo", exported)
        self.assertNotIn("protocolo", exported)


if __name__ == "__main__":
    unittest.main()
