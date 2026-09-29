"""Guard de privacidade do audit-site.py (#186): nenhum CPF nem número de conta
bancária pode chegar ao snapshot publicado. Complementa a normalização do sync
(#221): o sync oculta; o audit reprova se algum escapar."""
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit-site.py"
SPEC = importlib.util.spec_from_file_location("audit_site_privacy", MODULE_PATH)
audit_site = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(audit_site)


def row(tse_id, description):
    return {"tse_id": tse_id, "assets": {"items": [{"description": description}]}}


class PrivacyLeakTests(unittest.TestCase):
    def test_cpf_and_account_number_are_flagged(self):
        rows = [
            row("1", "IMÓVEL, CPF NO 123.456.789-09"),
            row("2", "BANCO: 104 AGÊNCIA: 1234 CONTA: 12345-6"),
            row("3", "AG: 1234 CC: 12345678-9. POUPANÇA"),
            row("4", "Saldo em c/c: 1234567-8"),
        ]
        self.assertEqual(["1", "2", "3", "4"], audit_site.privacy_leaks(rows))

    def test_clean_rows_pass(self):
        rows = [
            row("1", "IMÓVEL, CPF NO [omitido]"),
            row("2", "BANCO: 104 AGÊNCIA: 1234 CONTA: [omitida]"),
            row("3", "AG: 1234 CC: CEF. SALDO EM 09/26."),
            row("4", "QUOTAS DA EMPRESA X, CNPJ N. 12.345.678/0001-90"),
            row("5", "Saldo depositado em conta corrente na Caixa (Agência 1234)"),
        ]
        self.assertEqual([], audit_site.privacy_leaks(rows))

    def test_committed_snapshot_has_no_leak(self):
        import json

        base = Path(__file__).resolve().parents[1] / "data" / "generated"
        rows = []
        for kind in ("federal", "estadual", "governador", "senador"):
            path = base / f"candidates-{kind}.json"
            if path.exists():
                rows.extend(json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual([], audit_site.privacy_leaks(rows))


if __name__ == "__main__":
    unittest.main()
