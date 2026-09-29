#!/usr/bin/env python3
"""Normalização de redes sociais e histórico eleitoral no sync (#186).

Com o CDN do TSE alcançável, o sync passou a consumir os CSVs oficiais em vez do
espelho de contingência. Dois efeitos só apareceram com o dado real:

- a fonte oficial traz contatos diretos e convites de grupo como "rede social"
  (78 links de grupo de WhatsApp numa única candidatura), com telefone embutido
  em alguns — dado que AGENTS.md §5 proíbe publicar;
- o CSV de histórico traz o município em NM_UE, e o registro perdia o "onde".
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync-data.py"
SPEC = importlib.util.spec_from_file_location("sync_data_social_history", MODULE_PATH)
sync = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync
assert SPEC.loader is not None
SPEC.loader.exec_module(sync)


class SocialLinkPrivacyTests(unittest.TestCase):
    def test_group_invites_and_direct_chat_links_are_not_published(self):
        links = [
            "https://chat.whatsapp.com/F6W8p8YBogr2yeH7zvV2vq",
            "https://wa.me/5527999990000",
            "https://wa.me/qr/UCLEN5ROU62FJ1",
            "https://api.whatsapp.com/send?phone=5527999990000&text=oi",
            "https://web.whatsapp.com/send?phone=5527999990000",
            "https://whatsapp.com/send?phone=5527999990000",
            "https://example.com/contato?Phone=5527999990000",
        ]
        self.assertEqual([], sync._normalize_social_links(links))

    def test_public_profiles_and_channels_are_kept(self):
        links = [
            "https://www.instagram.com/perfil/",
            "https://facebook.com/pagina",
            "https://x.com/perfil",
            "https://www.youtube.com/@canal",
            "https://whatsapp.com/channel/0029Vb8QQsvKQuJDxKMxEM2m",
            "https://whatsapp.com/CHANNEL/0029VBB2KE130LKY5XQXHK42",
            "https://t.me/usuario",
            "https://candidato.com.br",
        ]
        self.assertEqual(len(links), len(sync._normalize_social_links(links)))

    def test_telegram_invites_are_dropped_and_public_channels_kept(self):
        self.assertEqual(
            ["https://t.me/canalpublico"],
            sync._normalize_social_links(
                [
                    "https://t.me/+AbCdEfGhIjK",
                    "https://t.me/joinchat/AbCdEfGhIjK",
                    "https://t.me/canalpublico",
                ]
            ),
        )

    def test_dozens_of_group_invites_do_not_crowd_out_public_profiles(self):
        invites = [f"https://chat.whatsapp.com/Grupo{index:03d}" for index in range(78)]
        public = ["https://www.instagram.com/casagrande/", "https://x.com/casagrande"]
        self.assertEqual(public, sync._normalize_social_links(invites + public))

    def test_existing_normalization_and_deduplication_are_unchanged(self):
        self.assertEqual(
            ["https://example.com/PERFIL"],
            sync._normalize_social_links(["HTTPS://EXAMPLE.COM/PERFIL", "https://example.com/perfil"]),
        )


class HistoryLocationTests(unittest.TestCase):
    def test_title_place_uses_usual_spelling(self):
        self.assertEqual("Espírito Santo", sync._title_place("ESPÍRITO SANTO"))
        self.assertEqual("Colatina", sync._title_place("COLATINA"))
        self.assertEqual("Cachoeiro de Itapemirim", sync._title_place("CACHOEIRO DE ITAPEMIRIM"))
        self.assertEqual("São José do Calçado", sync._title_place("SÃO JOSÉ DO CALÇADO"))
        self.assertEqual("De Lourdes", sync._title_place("DE LOURDES"))  # 1ª palavra sempre maiúscula
        self.assertIsNone(sync._title_place("#NE"))
        self.assertIsNone(sync._title_place("#NULO"))
        self.assertIsNone(sync._title_place(""))
        self.assertIsNone(sync._title_place(None))

    def test_history_records_carry_the_place_from_nm_ue(self):
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
        history = [
            {
                "SQ_CANDIDATO_ATUAL": "80000000001",
                "ANO_ELEICAO": "2016",
                "DS_CARGO": "Prefeito",
                "SG_PARTIDO": "PMDB",
                "SG_UF": "ES",
                "NM_UE": "COLATINA",
                "DS_SIT_TOT_TURNO": "Eleito",
            },
            {
                "SQ_CANDIDATO_ATUAL": "80000000001",
                "ANO_ELEICAO": "2014",
                "DS_CARGO": "Deputado Estadual",
                "SG_PARTIDO": "PMDB",
                "SG_UF": "ES",
                "NM_UE": "ESPÍRITO SANTO",
                "DS_SIT_TOT_TURNO": "Suplente",
            },
            {
                "SQ_CANDIDATO_ATUAL": "80000000001",
                "ANO_ELEICAO": "2012",
                "DS_CARGO": "Vereador",
                "SG_PARTIDO": "PMDB",
                "SG_UF": "ES",
                "NM_UE": "#NE",  # sentinela: sem lugar, não inventa um
                "DS_SIT_TOT_TURNO": "Não eleito",
            },
            {
                "SQ_CANDIDATO_ATUAL": "80000000001",
                "ANO_ELEICAO": "2026",
                "DS_CARGO": "Senador",
                "SG_PARTIDO": "PSD",
                "SG_UF": "ES",
                "NM_UE": "ESPÍRITO SANTO",
                "DS_SIT_TOT_TURNO": "#NULO",
            },
        ]
        social = [
            {"SQ_CANDIDATO": "80000000001", "DS_URL": "https://chat.whatsapp.com/Grupo001"},
            {"SQ_CANDIDATO": "80000000001", "DS_URL": "https://www.instagram.com/ana/"},
        ]
        datasets = {
            sync.TSE_COMPLEMENT_ZIP: [{"SQ_CANDIDATO": "80000000001", "DS_SITUACAO_JULGAMENTO": "DEFERIDO"}],
            sync.TSE_ASSETS_ZIP: [
                {
                    "SQ_CANDIDATO": "80000000001",
                    "NR_ORDEM_BEM_CANDIDATO": "1",
                    "DS_TIPO_BEM_CANDIDATO": "Casa",
                    "DS_BEM_CANDIDATO": "IMÓVEL",
                    "VR_BEM_CANDIDATO": "100000,50",
                }
            ],
            sync.TSE_SOCIAL_ZIP: social,
            sync.TSE_HISTORY_ZIP: history,
        }

        def fake_archive(url, preferred_suffix=None, timeout=90):
            return datasets[url], {
                "institution": "TSE",
                "url": url,
                "archive_member": preferred_suffix or "historico.csv",
                "sha256": "a" * 64,
                "generated_at": "29/09/2026 12:00:00",
                "row_count": len(datasets[url]),
                "status": "fresh",
            }

        with patch.object(sync, "read_tse_archive", side_effect=fake_archive), patch.object(
            sync, "_previous_candidate_map", return_value={}
        ), patch.object(sync, "_load_enrichment_bootstrap", return_value=({}, None)):
            sync.enrich_tse_open_data([candidates])

        records = {item["year"]: item for item in candidates[0]["previous_elections"]}
        self.assertEqual({2016, 2014, 2012}, set(records))  # 2026 nunca entra
        self.assertEqual("Colatina", records[2016]["location"])
        self.assertEqual("Espírito Santo", records[2014]["location"])
        self.assertNotIn("location", records[2012])
        # o convite de grupo saiu; o perfil público ficou
        self.assertEqual(["https://www.instagram.com/ana/"], candidates[0]["social_links"])

    def test_same_year_office_in_two_places_is_not_collapsed(self):
        # Chave de deduplicação inclui o lugar: dois registros que só diferem no
        # município não podem virar um.
        candidates = [{
            "tse_id": "80000000002",
            "ballot_name": "BIA",
            "full_name": "BIA TESTE",
            "social_name": None,
            "registration_status": None,
            "assets": {},
            "social_links": [],
            "previous_elections": [],
            "tse_additional": {},
        }]
        base = {
            "SQ_CANDIDATO_ATUAL": "80000000002",
            "ANO_ELEICAO": "2020",
            "DS_CARGO": "Vereador",
            "SG_PARTIDO": "ABC",
            "SG_UF": "ES",
            "DS_SIT_TOT_TURNO": "Não eleito",
        }
        datasets = {
            sync.TSE_COMPLEMENT_ZIP: [{"SQ_CANDIDATO": "80000000002", "DS_SITUACAO_JULGAMENTO": "DEFERIDO"}],
            sync.TSE_ASSETS_ZIP: [{"SQ_CANDIDATO": "80000000002", "VR_BEM_CANDIDATO": "1,00"}],
            sync.TSE_SOCIAL_ZIP: [{"SQ_CANDIDATO": "80000000002", "DS_URL": "https://x.com/bia"}],
            sync.TSE_HISTORY_ZIP: [
                {**base, "NM_UE": "SERRA"},
                {**base, "NM_UE": "VILA VELHA"},
                {**base, "NM_UE": "SERRA"},  # duplicata exata: essa sim colapsa
            ],
        }

        def fake_archive(url, preferred_suffix=None, timeout=90):
            return datasets[url], {
                "institution": "TSE",
                "url": url,
                "archive_member": preferred_suffix or "historico.csv",
                "sha256": "b" * 64,
                "generated_at": "29/09/2026 12:00:00",
                "row_count": len(datasets[url]),
                "status": "fresh",
            }

        with patch.object(sync, "read_tse_archive", side_effect=fake_archive), patch.object(
            sync, "_previous_candidate_map", return_value={}
        ), patch.object(sync, "_load_enrichment_bootstrap", return_value=({}, None)):
            sync.enrich_tse_open_data([candidates])

        places = sorted(item["location"] for item in candidates[0]["previous_elections"])
        self.assertEqual(["Serra", "Vila Velha"], places)


if __name__ == "__main__":
    unittest.main()
