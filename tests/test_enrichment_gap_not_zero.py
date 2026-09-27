"""Regressão do finding do Codex no #193 (P1): candidatura nova sem
cobertura de bootstrap não pode virar 'zero declarado'.

Cenário real: `sync-data.py` generalizou o registry para 4 cargos (#187).
Quando as fontes ao vivo do TSE falham (403) e o `previous` (estado anterior
publicado) só cobre o universo antigo (deputados), `_apply_bootstrap_field`
era chamado incondicionalmente sobre TODOS os candidatos só quando
`restored == 0`; como `restored` era truthy (547 > 0) mesmo cobrindo só uma
fração do universo atual (563, com os 16 novos de governador/senador), o
bootstrap nunca rodava para completar a lacuna — os 16 novos ficavam com o
default `count: 0, items: []` do topo da função, indistinguível de um "TSE
confirma zero" verificado.

`_fill_enrichment_field` restaura o que dá e completa com bootstrap só quem
sobrou; `_mark_enrichment_gap` marca explicitamente quem não teve nenhuma
fonte, para nunca ser lido como zero verificado (AGENTS.md §2/§5).
"""
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync-data.py"
SPEC = importlib.util.spec_from_file_location("sync_data", MODULE_PATH)
sync_data = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(sync_data)

fill_field = sync_data._fill_enrichment_field
mark_gap = sync_data._mark_enrichment_gap


def _candidate(tse_id, **defaults):
    base = {"tse_id": tse_id, "assets": {"total_declared_brl": None, "count": 0, "items": [], "source": None}}
    base.update(defaults)
    return base


class EnrichmentGapNotZeroTests(unittest.TestCase):
    def test_reproduces_codex_193_scenario_new_offices_without_any_source(self):
        """137 federal + 410 estadual (simulados como 2 IDs para o teste)
        restauráveis do estado anterior; 16 novos (governador/senador,
        aqui 2 IDs) sem estado anterior nem bootstrap — o bug original os
        publicava com o default zero sem sinalizar nada."""
        deputados = [_candidate("1"), _candidate("2")]
        novos = [_candidate("80001"), _candidate("80002")]
        candidates = deputados + novos

        previous = {
            "1": {"assets": {"total_declared_brl": "1000.00", "count": 1, "items": [{"x": 1}], "source": {}}},
            "2": {"assets": {"total_declared_brl": None, "count": 0, "items": [], "source": {}}},
        }
        bootstrap = {}  # não cobre os cargos novos, como no #193

        covered = fill_field(candidates, previous, bootstrap, "assets", previous_enrichment_valid=True)
        gaps = mark_gap(candidates, covered, "assets")

        self.assertEqual(covered, {"1", "2"})
        self.assertEqual(set(gaps), {"80001", "80002"})

        by_id = {c["tse_id"]: c for c in candidates}
        self.assertEqual(by_id["1"]["assets"]["count"], 1, "restaurado do estado anterior")
        self.assertNotIn("enrichment_gaps", by_id["1"], "candidato coberto não deve carregar marca de lacuna")
        self.assertNotIn("enrichment_gaps", by_id["2"])

        for cid in ("80001", "80002"):
            self.assertEqual(
                by_id[cid]["assets"]["count"], 0,
                "sem fonte nenhuma, o valor no campo continua o default — não inventamos outro formato",
            )
            self.assertIn(
                "assets", by_id[cid]["enrichment_gaps"],
                "mas precisa estar marcado como não coberto, nunca como zero verificado silencioso",
            )

    def test_bootstrap_fills_exactly_the_gap_previous_left(self):
        """Quando o bootstrap cobre quem o estado anterior não cobriu, a
        lacuna fecha e ninguém fica marcado."""
        candidates = [_candidate("1"), _candidate("2")]
        previous = {"1": {"assets": {"count": 1, "items": [{"x": 1}], "total_declared_brl": "10.00", "source": {}}}}
        bootstrap = {"2": {"assets": {"count": 3, "items": [{}, {}, {}], "total_declared_brl": "5.00", "source": {}}}}

        covered = fill_field(candidates, previous, bootstrap, "assets", previous_enrichment_valid=True)
        gaps = mark_gap(candidates, covered, "assets")

        self.assertEqual(covered, {"1", "2"})
        self.assertEqual(gaps, [])
        by_id = {c["tse_id"]: c for c in candidates}
        self.assertEqual(by_id["1"]["assets"]["count"], 1)
        self.assertEqual(by_id["2"]["assets"]["count"], 3, "bootstrap completou quem faltava")

    def test_bootstrap_never_overwrites_a_candidate_already_restored(self):
        """Um bootstrap mais velho não pode pisar em cima de um estado
        anterior mais recente para quem já foi restaurado."""
        candidates = [_candidate("1")]
        previous = {"1": {"assets": {"count": 5, "items": [{}] * 5, "total_declared_brl": "999.00", "source": {}}}}
        bootstrap = {"1": {"assets": {"count": 1, "items": [{}], "total_declared_brl": "1.00", "source": {}}}}

        covered = fill_field(candidates, previous, bootstrap, "assets", previous_enrichment_valid=True)

        self.assertEqual(covered, {"1"})
        self.assertEqual(candidates[0]["assets"]["count"], 5, "restore vence bootstrap para quem já está coberto")

    def test_no_source_at_all_marks_every_candidate(self):
        candidates = [_candidate("1"), _candidate("2")]
        covered = fill_field(candidates, {}, {}, "assets", previous_enrichment_valid=False)
        gaps = mark_gap(candidates, covered, "assets")
        self.assertEqual(covered, set())
        self.assertEqual(set(gaps), {"1", "2"})


if __name__ == "__main__":
    unittest.main()
