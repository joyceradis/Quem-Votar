#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync-data.py"
SPEC = importlib.util.spec_from_file_location("sync_data", MODULE_PATH)
sync = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync
assert SPEC.loader is not None
SPEC.loader.exec_module(sync)

class SyncGovernanceTests(unittest.TestCase):
    def test_total_chamber_failure_preserves_previous_verified_links(self) -> None:
        candidates=[{"tse_id":"123","ballot_name":"MARIA SILVA","full_name":"MARIA SILVA","social_name":None,"current_mandate":None,"institutional_history":None}]
        mandate={"institution":"Câmara dos Deputados","type":"federal","chamber_id":99,"status":"Exercício"}
        history={"chamber_id":99,"status":"Exercício"}
        previous_candidate={"tse_id":"123","current_mandate":mandate,"institutional_history":history}
        previous_chamber=[{"chamber_id":99,"status":"Exercício"}]
        def fake_existing(name,default):
            if name=="federal-chamber.json": return previous_chamber
            if name=="candidates-federal.json": return [previous_candidate]
            return default
        with patch.object(sync,"read_existing_json",side_effect=fake_existing), patch.object(sync,"chamber_current_es",side_effect=RuntimeError("timeout")):
            url,exported=sync.enrich_federal(candidates)
        self.assertIn("dadosabertos.camara.leg.br",url)
        self.assertEqual(previous_chamber,exported)
        self.assertEqual(99,candidates[0]["current_mandate"]["chamber_id"])

    def test_total_chamber_failure_without_previous_state_fails_closed(self) -> None:
        candidates=[{"tse_id":"123","ballot_name":"MARIA SILVA","full_name":"MARIA SILVA","social_name":None,"current_mandate":None,"institutional_history":None}]
        with patch.object(sync,"read_existing_json",return_value=[]), patch.object(sync,"chamber_current_es",side_effect=RuntimeError("timeout")):
            with self.assertRaisesRegex(RuntimeError,"sync abortado"):
                sync.enrich_federal(candidates)

    def test_mirror_snapshot_pins_commit_blob_and_bytes(self) -> None:
        filename="deputado-federal.json"
        path=f"{sync.MIRROR_PATH_BASE}/{filename}"
        raw=json.dumps([{"SG_UF":"ES"}]).encode("utf-8")
        commit_sha="a"*40
        blob_sha="b"*40
        def fake_json(url,timeout=20):
            if "/commits?" in url: return [{"sha":commit_sha}]
            if "/contents/" in url: return {"sha":blob_sha}
            raise AssertionError(url)
        with patch.object(sync,"request_json",side_effect=fake_json), patch.object(sync,"request_bytes",return_value=raw) as bytes_mock:
            rows,meta=sync.mirror_snapshot(filename)
        self.assertEqual([{"SG_UF":"ES"}],rows)
        self.assertEqual(commit_sha,meta["commit_sha"])
        self.assertEqual(blob_sha,meta["blob_sha"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),meta["content_sha256"])
        self.assertIn(commit_sha,meta["raw_url"])
        self.assertIn(commit_sha,bytes_mock.call_args.args[0])

    def test_registration_status_sentinel_becomes_explicit_not_available(self) -> None:
        for raw in (None, "", "#NE", "#NULO", "-1", "-3", "NÃO DIVULGÁVEL"):
            self.assertEqual(
                "not_available",
                sync.normalize_registration_status(raw),
                raw,
            )

    def test_registration_status_real_value_is_preserved(self) -> None:
        self.assertEqual(
            "DEFERIDO",
            sync.normalize_registration_status(" DEFERIDO "),
        )


class RunningMateTests(unittest.TestCase):
    """#186 item 4 — vice (Governador) e suplentes (Senador) vivem como campo
    do titular, ligados por NR_CANDIDATO exato. Ambiguidade na fonte nunca
    vira escolha editorial (AGENTS.md §3): estes testes cobrem os três
    desfechos possíveis (linked/ambiguous_source/not_available) sem depender
    da rede, mockando mirror_snapshot como o teste de mirror_snapshot em si
    já cobre a plumbing HTTP separadamente.
    """

    def _mirror(self, rows, repository="herminiotorres/dossie-cidadao"):
        return rows, {"repository": repository, "path": "x", "blob_sha": "b", "html_url": "u"}

    def test_governador_vice_clean_link(self) -> None:
        candidates = {
            "governador": [{"number": "12", "tse_id": "1"}],
            "senador": [],
        }
        vice_row = {
            "SG_UF": "ES",
            "DS_CARGO": "VICE-GOVERNADOR",
            "NR_CANDIDATO": "12",
            "SQ_CANDIDATO": "999",
            "NM_URNA_CANDIDATO": "FULANO VICE",
        }
        with patch.object(sync, "mirror_snapshot", return_value=self._mirror([vice_row])):
            sync.attach_running_mates(candidates)
        running_mate = candidates["governador"][0]["running_mate"]
        self.assertEqual("linked", running_mate["status"])
        self.assertEqual("999", running_mate["tse_id"])
        self.assertEqual("VICE-GOVERNADOR", running_mate["role"])

    def test_senador_suplente_not_available_when_no_ballot_match(self) -> None:
        candidates = {
            "governador": [],
            "senador": [{"number": "77", "tse_id": "2"}],
        }

        def fake_mirror(filename):
            tse_label = "1º SUPLENTE" if filename == "1-suplente.json" else "2º SUPLENTE"
            other_ballot_row = {
                "SG_UF": "ES",
                "DS_CARGO": tse_label,
                "NR_CANDIDATO": "99",
                "SQ_CANDIDATO": "111",
            }
            return self._mirror([other_ballot_row])

        with patch.object(sync, "mirror_snapshot", side_effect=fake_mirror):
            sync.attach_running_mates(candidates)
        substitutes = candidates["senador"][0]["substitutes"]
        self.assertEqual("not_available", substitutes["primeiro_suplente"]["status"])
        self.assertEqual("not_available", substitutes["segundo_suplente"]["status"])

    def test_senador_suplente_ambiguous_source_preserves_both_records(self) -> None:
        # Caso real observado na chapa 156 (ROSE DE FREITAS): dois registros
        # de 1º suplente no mesmo número de urna, ambos "#NE", sem campo que
        # desempate — o pipeline nunca escolhe um, documenta os dois.
        candidates = {
            "governador": [],
            "senador": [{"number": "156", "tse_id": "3"}],
        }
        conflicting_rows = [
            {
                "SG_UF": "ES",
                "DS_CARGO": "1º SUPLENTE",
                "NR_CANDIDATO": "156",
                "SQ_CANDIDATO": "201",
                "DS_SITUACAO_CANDIDATURA": "#NE",
            },
            {
                "SG_UF": "ES",
                "DS_CARGO": "1º SUPLENTE",
                "NR_CANDIDATO": "156",
                "SQ_CANDIDATO": "202",
                "DS_SITUACAO_CANDIDATURA": "#NE",
            },
        ]
        second_suplente_row = {
            "SG_UF": "ES",
            "DS_CARGO": "2º SUPLENTE",
            "NR_CANDIDATO": "156",
            "SQ_CANDIDATO": "203",
        }

        def fake_mirror(filename):
            if filename == "1-suplente.json":
                return self._mirror(conflicting_rows)
            return self._mirror([second_suplente_row])

        with patch.object(sync, "mirror_snapshot", side_effect=fake_mirror):
            sync.attach_running_mates(candidates)
        substitutes = candidates["senador"][0]["substitutes"]
        primeiro = substitutes["primeiro_suplente"]
        self.assertEqual("ambiguous_source", primeiro["status"])
        self.assertEqual(2, len(primeiro["candidates"]))
        self.assertEqual({"201", "202"}, {c["tse_id"] for c in primeiro["candidates"]})
        self.assertEqual("linked", substitutes["segundo_suplente"]["status"])

    def test_running_mate_absent_for_offices_without_roster(self) -> None:
        # federal/estadual não passam por RUNNING_MATE_REGISTRY (chave nem
        # existe no dict), então attach_running_mates não deve tocá-los.
        candidates = {"governador": [], "senador": []}
        mirror_meta = sync.attach_running_mates(candidates)
        self.assertEqual({}, mirror_meta)


if __name__ == '__main__':
    unittest.main()
