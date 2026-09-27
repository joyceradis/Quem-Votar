"""Regressão do guard-rail 'sync nunca escreve em main' (#186/#192).

`audit-site.py` tinha uma checagem ampla demais — nenhuma ocorrência literal
de "git push"/"git commit" era permitida em sync-data.yml — que bloqueou o
job publicar-branch-dados (#192), legítimo por só commitar/empurrar numa
branch de dados efêmera, nunca em main. `check_sync_never_writes_to_main`
substitui a checagem textual por uma verificação do invariante real: o
pipeline pode publicar numa branch nova, mas nunca pode escrever
main/master, com ou sem force, direto ou por refspec/alias.
"""
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit-site.py"
SPEC = importlib.util.spec_from_file_location("audit_site", MODULE_PATH)
audit_site = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(audit_site)

check = audit_site.check_sync_never_writes_to_main


class SyncNeverWritesToMainTests(unittest.TestCase):
    def test_branch_only_flow_passes(self):
        """Fluxo real do #192: cria branch nova, commita e empurra só nela."""
        workflow = """
        git checkout -b "$BRANCH"
        git commit -m "data(sync): snapshot"
        git push -u origin "$BRANCH"
        """
        check(workflow)  # não deve levantar

    def test_no_git_write_at_all_passes(self):
        """Job sem nenhum commit/push (ex.: o job sync original) continua OK."""
        check("actions/upload-artifact@v4\n")

    def test_direct_push_to_main_fails(self):
        workflow = """
        git commit -m "data"
        git push origin main
        """
        with self.assertRaisesRegex(AssertionError, "main"):
            check(workflow)

    def test_direct_push_to_master_alias_fails(self):
        workflow = """
        git commit -m "data"
        git push origin master
        """
        with self.assertRaisesRegex(AssertionError, "master"):
            check(workflow)

    def test_force_push_fails_even_to_a_data_branch(self):
        workflow = """
        git checkout -b "$BRANCH"
        git commit -m "data"
        git push --force -u origin "$BRANCH"
        """
        with self.assertRaisesRegex(AssertionError, "force"):
            check(workflow)

    def test_short_force_flag_fails(self):
        workflow = """
        git checkout -b "$BRANCH"
        git commit -m "data"
        git push -f origin "$BRANCH"
        """
        with self.assertRaisesRegex(AssertionError, "force"):
            check(workflow)

    def test_refspec_alias_to_main_fails(self):
        """git push origin HEAD:main escreve em main por refspec, sem citar
        'origin main' — precisa ser pego do mesmo jeito."""
        workflow = """
        git checkout -b "$BRANCH"
        git commit -m "data"
        git push origin HEAD:main
        """
        with self.assertRaisesRegex(AssertionError, "main"):
            check(workflow)

    def test_full_ref_alias_to_main_fails(self):
        workflow = """
        git checkout -b "$BRANCH"
        git commit -m "data"
        git push origin HEAD:refs/heads/main
        """
        with self.assertRaisesRegex(AssertionError, "main"):
            check(workflow)

    def test_commit_without_new_branch_fails(self):
        """Commitar sem antes criar uma branch nova é indistinguível de
        commitar direto no checkout atual (main, no runner do sync)."""
        workflow = """
        git commit -m "data"
        git push -u origin some-branch
        """
        with self.assertRaisesRegex(AssertionError, "branch nova"):
            check(workflow)

    def test_current_sync_workflow_file_passes(self):
        """O sync-data.yml real do repositório precisa passar por esta
        checagem — é a regressão que efetivamente rodou no #192."""
        real = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "sync-data.yml"
        ).read_text(encoding="utf-8")
        check(real)  # não deve levantar


if __name__ == "__main__":
    unittest.main()
