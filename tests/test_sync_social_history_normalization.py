#!/usr/bin/env python3
"""Normalização de redes sociais e histórico eleitoral no sync (#186).

Com o CDN do TSE alcançável, o sync passou a consumir os CSVs oficiais em vez do
espelho de contingência. Dois efeitos só apareceram com o dado real:

- a fonte oficial traz contatos diretos e convites de grupo como "rede social"
  (78 links de grupo de WhatsApp numa única candidatura), com telefone embutido
  em alguns — dado que AGENTS.md §5 proíbe publicar;
- o CSV de histórico traz o município em NM_UE, e o registro perdia o "onde";
- a descrição de bem é texto livre e traz CPF de terceiros e número de conta
  bancária (AGENTS.md §5);
- candidatura em dois turnos vira duas linhas no CSV e contava a mesma disputa
  duas vezes no histórico.
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


class AssetDescriptionPrivacyTests(unittest.TestCase):
    def test_cpf_is_omitted_wherever_it_appears(self):
        cases = {
            "APARTAMENTO ADQUIRIDO JUNTAMENTE COM ANA TESTE, CPF NO 123.456.789-09 PELO VALOR DE R$ 270.000,00":
                "APARTAMENTO ADQUIRIDO JUNTAMENTE COM ANA TESTE, CPF NO [omitido] PELO VALOR DE R$ 270.000,00",
            "TERRENO FRAÇÃO - ADQUIRIDO DE CPF 123.456.789-09 E OUTROS EM 01/01/2020":
                "TERRENO FRAÇÃO - ADQUIRIDO DE CPF [omitido] E OUTROS EM 01/01/2020",
            "IMÓVEL, CPF Nº 12345678909": "IMÓVEL, CPF Nº [omitido]",
            "cpf: 12345678909 (vendedor)": "cpf: [omitido] (vendedor)",
        }
        for raw, expected in cases.items():
            self.assertEqual(expected, sync._scrub_asset_description(raw), raw)

    def test_bank_account_number_is_omitted_but_bank_and_agency_stay(self):
        self.assertEqual(
            "BANCO: 104 AGÊNCIA: 1234 CONTA: [omitida]",
            sync._scrub_asset_description("BANCO: 104 AGÊNCIA: 1234 CONTA: 12345-6"),
        )
        self.assertEqual(
            "AG: 1234 CC: [omitida]. POUPANÇA INTEGRADA, SALDO EM 09/26.",
            sync._scrub_asset_description("AG: 1234 CC: 12345678-9. POUPANÇA INTEGRADA, SALDO EM 09/26."),
        )

    def test_descriptions_without_identifiers_are_untouched(self):
        for text in (
            "CLÍNICA VETERINÁRIA EM GUARAPARI",
            "AG: 1234 CC: CEF. SALDO EM 09/26.",  # conta sem número: nada a ocultar
            "Saldo depositado em conta corrente na Caixa Econômica Federal (Agência 1234) em 01/01/2026.",
            "17% DE PARTICIPAÇÃO NA EMPRESA X LTDA, CNPJ N. 12.345.678/0001-90",  # CNPJ é público
            "VEÍCULO AUTOMOTOR TERRESTRE: TOYOTA CAMRY, ANO 2020",
            "",
            None,
        ):
            self.assertEqual(text, sync._scrub_asset_description(text), text)

    def test_scrub_runs_over_live_and_restored_assets(self):
        def candidate(cid):
            return {
                "tse_id": cid,
                "ballot_name": "X",
                "full_name": "X TESTE",
                "social_name": None,
                "registration_status": None,
                "assets": {},
                "social_links": [],
                "previous_elections": [],
                "tse_additional": {},
            }

        # Ao vivo: o CSV oficial traz CPF e conta na descrição.
        live = [candidate("80000000010")]
        datasets = {
            sync.TSE_COMPLEMENT_ZIP: [{"SQ_CANDIDATO": "80000000010", "DS_SITUACAO_JULGAMENTO": "DEFERIDO"}],
            sync.TSE_ASSETS_ZIP: [
                {
                    "SQ_CANDIDATO": "80000000010",
                    "NR_ORDEM_BEM_CANDIDATO": "1",
                    "DS_TIPO_BEM_CANDIDATO": "Apartamento",
                    "DS_BEM_CANDIDATO": "ADQUIRIDO COM ANA, CPF NO 123.456.789-09",
                    "VR_BEM_CANDIDATO": "270000,00",
                },
                {
                    "SQ_CANDIDATO": "80000000010",
                    "NR_ORDEM_BEM_CANDIDATO": "2",
                    "DS_TIPO_BEM_CANDIDATO": "Poupança",
                    "DS_BEM_CANDIDATO": "BANCO: 104 AGÊNCIA: 1234 CONTA: 12345-6",
                    "VR_BEM_CANDIDATO": "1000,00",
                },
            ],
            sync.TSE_SOCIAL_ZIP: [{"SQ_CANDIDATO": "80000000010", "DS_URL": "https://x.com/x"}],
            sync.TSE_HISTORY_ZIP: [
                {"SQ_CANDIDATO_ATUAL": "80000000010", "ANO_ELEICAO": "2022", "DS_CARGO": "Vereador", "SG_UF": "ES"}
            ],
        }

        def fake_archive(url, preferred_suffix=None, timeout=90):
            return datasets[url], {
                "institution": "TSE",
                "url": url,
                "archive_member": preferred_suffix or "historico.csv",
                "sha256": "c" * 64,
                "generated_at": "29/09/2026 12:00:00",
                "row_count": len(datasets[url]),
                "status": "fresh",
            }

        with patch.object(sync, "read_tse_archive", side_effect=fake_archive), patch.object(
            sync, "_previous_candidate_map", return_value={}
        ), patch.object(sync, "_load_enrichment_bootstrap", return_value=({}, None)):
            sync.enrich_tse_open_data([live])

        items = live[0]["assets"]["items"]
        self.assertEqual("ADQUIRIDO COM ANA, CPF NO [omitido]", items[0]["description"])
        self.assertEqual("BANCO: 104 AGÊNCIA: 1234 CONTA: [omitida]", items[1]["description"])
        # tipo e valor não mudam; o total declarado continua somando os dois bens
        self.assertEqual("Apartamento", items[0]["type"])
        self.assertEqual(270000.0, items[0]["value_brl"])
        self.assertEqual(271000.0, live[0]["assets"]["total_declared_brl"])

        # Sem fonte ao vivo: o valor restaurado do estado anterior também passa pelo scrub.
        restored = [candidate("80000000011")]
        previous = {
            "80000000011": {
                "tse_id": "80000000011",
                "assets": {
                    "total_declared_brl": 5.0,
                    "count": 1,
                    "items": [{"order": 1, "type": "Terreno", "description": "COMPRADO DE CPF 123.456.789-09", "value_brl": 5.0}],
                    "source": {"institution": "TSE"},
                },
                "social_links": [],
                "previous_elections": [],
            }
        }
        with patch.object(sync, "read_tse_archive", side_effect=RuntimeError("HTTP 403")), patch.object(
            sync, "_previous_candidate_map", return_value=previous
        ), patch.object(sync, "_load_enrichment_bootstrap", return_value=({}, None)), patch.object(
            sync, "read_existing_json", return_value={"normalizer_version": "4.0.0"}
        ):
            sync.enrich_tse_open_data([restored])
        self.assertEqual(
            "COMPRADO DE CPF [omitido]", restored[0]["assets"]["items"][0]["description"]
        )


class ElectionRoundsTests(unittest.TestCase):
    def _history(self, rows):
        candidates = [{
            "tse_id": "80000000020",
            "ballot_name": "CAROL",
            "full_name": "CAROL TESTE",
            "social_name": None,
            "registration_status": None,
            "assets": {},
            "social_links": [],
            "previous_elections": [],
            "tse_additional": {},
        }]
        base = {"SQ_CANDIDATO_ATUAL": "80000000020", "SG_UF": "ES"}
        datasets = {
            sync.TSE_COMPLEMENT_ZIP: [{"SQ_CANDIDATO": "80000000020", "DS_SITUACAO_JULGAMENTO": "DEFERIDO"}],
            sync.TSE_ASSETS_ZIP: [{"SQ_CANDIDATO": "80000000020", "VR_BEM_CANDIDATO": "1,00"}],
            sync.TSE_SOCIAL_ZIP: [{"SQ_CANDIDATO": "80000000020", "DS_URL": "https://x.com/carol"}],
            sync.TSE_HISTORY_ZIP: [{**base, **row} for row in rows],
        }

        def fake_archive(url, preferred_suffix=None, timeout=90):
            return datasets[url], {
                "institution": "TSE",
                "url": url,
                "archive_member": preferred_suffix or "historico.csv",
                "sha256": "d" * 64,
                "generated_at": "29/09/2026 12:00:00",
                "row_count": len(datasets[url]),
                "status": "fresh",
            }

        with patch.object(sync, "read_tse_archive", side_effect=fake_archive), patch.object(
            sync, "_previous_candidate_map", return_value={}
        ), patch.object(sync, "_load_enrichment_bootstrap", return_value=({}, None)):
            sync.enrich_tse_open_data([candidates])
        return candidates[0]["previous_elections"]

    def test_two_round_candidacy_is_one_record_with_the_final_result(self):
        records = self._history([
            # 2022, Vice-governador: 1º turno "2º turno", 2º turno "Eleito"
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "DS_CARGO": "Vice-governador", "SG_PARTIDO": "PSDB", "NM_UE": "ESPÍRITO SANTO", "DS_SIT_TOT_TURNO": "2º turno"},
            {"ANO_ELEICAO": "2022", "NR_TURNO": "2", "DS_CARGO": "Vice-governador", "SG_PARTIDO": "PSDB", "NM_UE": "ESPÍRITO SANTO", "DS_SIT_TOT_TURNO": "Eleito"},
            # 2018: um turno só
            {"ANO_ELEICAO": "2018", "NR_TURNO": "1", "DS_CARGO": "Senador", "SG_PARTIDO": "PSDB", "NM_UE": "ESPÍRITO SANTO", "DS_SIT_TOT_TURNO": "Não eleito"},
        ])
        self.assertEqual([(2022, "Eleito"), (2018, "Não eleito")], [(r["year"], r["result"]) for r in records])
        self.assertTrue(all("_turn" not in r for r in records))  # detalhe interno não vaza

    def test_order_of_rows_does_not_decide_which_round_wins(self):
        rows = [
            {"ANO_ELEICAO": "2020", "NR_TURNO": "2", "DS_CARGO": "Prefeito", "SG_PARTIDO": "PT", "NM_UE": "VITÓRIA", "DS_SIT_TOT_TURNO": "Não eleito"},
            {"ANO_ELEICAO": "2020", "NR_TURNO": "1", "DS_CARGO": "Prefeito", "SG_PARTIDO": "PT", "NM_UE": "VITÓRIA", "DS_SIT_TOT_TURNO": "2º turno"},
        ]
        for ordered in (rows, list(reversed(rows))):
            records = self._history(ordered)
            self.assertEqual([("Prefeito", "Não eleito")], [(r["office"], r["result"]) for r in records])

    def test_without_turn_number_the_intermediate_result_still_loses(self):
        records = self._history([
            {"ANO_ELEICAO": "2016", "DS_CARGO": "Prefeito", "SG_PARTIDO": "SD", "NM_UE": "VITÓRIA", "DS_SIT_TOT_TURNO": "2º turno"},
            {"ANO_ELEICAO": "2016", "DS_CARGO": "Prefeito", "SG_PARTIDO": "SD", "NM_UE": "VITÓRIA", "DS_SIT_TOT_TURNO": "Não eleito"},
        ])
        self.assertEqual(["Não eleito"], [r["result"] for r in records])

    def test_same_turn_prefers_the_row_that_has_an_outcome(self):
        # Caso real (deputado estadual 2014): duas linhas, uma "Suplente" e outra sem resultado.
        row = {"ANO_ELEICAO": "2014", "NR_TURNO": "1", "DS_CARGO": "Deputado Estadual", "SG_PARTIDO": "PRB", "NM_UE": "ESPÍRITO SANTO"}
        for ordered in (
            [{**row, "DS_SIT_TOT_TURNO": "Suplente"}, {**row, "DS_SIT_TOT_TURNO": "#NULO"}],
            [{**row, "DS_SIT_TOT_TURNO": "#NULO"}, {**row, "DS_SIT_TOT_TURNO": "Suplente"}],
        ):
            records = self._history(ordered)
            self.assertEqual(["Suplente"], [r.get("result") for r in records])

    def test_runoff_without_final_row_is_kept_as_the_source_says(self):
        records = self._history([
            {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "DS_CARGO": "Governador", "SG_PARTIDO": "PL", "NM_UE": "ESPÍRITO SANTO", "DS_SIT_TOT_TURNO": "2º turno"},
        ])
        self.assertEqual(["2º turno"], [r["result"] for r in records])

    def test_different_office_or_party_in_the_same_year_stay_separate(self):
        records = self._history([
            {"ANO_ELEICAO": "2018", "NR_TURNO": "1", "DS_CARGO": "Senador", "SG_PARTIDO": "PSDB", "NM_UE": "ESPÍRITO SANTO", "DS_SIT_TOT_TURNO": "Não eleito"},
            {"ANO_ELEICAO": "2018", "NR_TURNO": "1", "DS_CARGO": "Deputado Federal", "SG_PARTIDO": "PSDB", "NM_UE": "ESPÍRITO SANTO", "DS_SIT_TOT_TURNO": "Suplente"},
        ])
        self.assertEqual(2, len(records))


if __name__ == "__main__":
    unittest.main()
