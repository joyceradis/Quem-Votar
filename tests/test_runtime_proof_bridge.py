import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bridge", ROOT / "scripts/runtime-proof-evidence.py")
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


class RuntimeBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.target = self.root / "target"
        self.harness = self.root / "harness"
        for repo in (self.target, self.harness):
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "tracked.txt").write_text("fixture\n")
            BRIDGE.git(repo, "add", ".")
            BRIDGE.git(repo, "-c", "user.name=Test fixture", "-c", "user.email=fixture@example.invalid",
                       "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        self.out = self.root / "artifact"
        self.out.mkdir()
        for name in BRIDGE.REQUIRED_FILES:
            file = self.out / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"test evidence")
        self.env = {
            "QV_HARNESS_REF": BRIDGE.git(self.harness, "rev-parse", "HEAD"),
            "QV_TARGET_REF": BRIDGE.git(self.target, "rev-parse", "HEAD"),
            "QV_WORKFLOW_SHA": "a" * 40,
            "QV_RUN_ID": "123", "QV_RUN_ATTEMPT": "1", "QV_ACTOR": "operator",
            "QV_TRIGGERING_ACTOR": "operator", "QV_REPOSITORY": "fixture/repo",
            "QV_MATRIX_OUTCOME": "success",
        }
        self.manifest = {
            "overall": "PASS", "merge_gate": "PASS",
            "run": {"harness_sha": self.env["QV_HARNESS_REF"], "id": "123", "attempt": "1"},
            "target": {"ref": self.env["QV_TARGET_REF"], "sha": self.env["QV_TARGET_REF"],
                       "mode": "checkout", "base_url": "http://127.0.0.1:8000/"},
            "suites": {name: {"status": "PASS", "scenarios": [
                {"name": scenario, "status": "PASS", "runtime_errors": {"material": []}}
                for scenario in sorted(required)]}
                for name, required in (("ui", BRIDGE.UI_SCENARIOS), ("harness_invariants", BRIDGE.INVARIANTS))},
        }

    def reconcile(self):
        return BRIDGE.reconcile(copy.deepcopy(self.manifest), self.env, self.target, self.harness, self.out)

    def test_complete_evidence_passes_and_records_attempt(self):
        result = self.reconcile()
        self.assertEqual(result["overall"], "PASS")
        self.assertEqual(result["bridge"]["artifact_name"], "runtime-proof-123-1")

    def test_mutable_short_and_injected_refs_are_blocked(self):
        for value in ("main", "a" * 7, "a" * 40 + "\n", "$(touch injected)"):
            with self.subTest(value=value):
                self.env["QV_TARGET_REF"] = value
                self.assertEqual(self.reconcile()["overall"], "BLOCKED")

    def test_full_but_wrong_sha_is_blocked(self):
        self.env["QV_TARGET_REF"] = "b" * 40
        self.assertIn("target:sha_mismatch", self.reconcile()["bridge"]["problems"])

    def test_misattributed_manifest_is_blocked(self):
        for section, key in (("run", "harness_sha"), ("run", "attempt"), ("target", "sha")):
            old = self.manifest[section][key]
            self.manifest[section][key] = "wrong"
            self.assertEqual(self.reconcile()["overall"], "BLOCKED")
            self.manifest[section][key] = old

    def test_tracked_and_untracked_target_mutation_are_blocked(self):
        (self.target / "tracked.txt").write_text("changed")
        self.assertIn("target:dirty_checkout", self.reconcile()["bridge"]["problems"])
        BRIDGE.git(self.target, "checkout", "--", "tracked.txt")
        (self.target / "extra.txt").write_text("extra")
        self.assertIn("target:dirty_checkout", self.reconcile()["bridge"]["problems"])

    def test_harness_tracked_mutation_is_blocked(self):
        (self.harness / "tracked.txt").write_text("changed")
        self.assertIn("harness:dirty_checkout", self.reconcile()["bridge"]["problems"])

    def test_missing_or_duplicate_scenario_cannot_pass(self):
        scenarios = self.manifest["suites"]["ui"]["scenarios"]
        removed = scenarios.pop()
        self.assertEqual(self.reconcile()["overall"], "BLOCKED")
        scenarios.extend([removed, removed])
        self.assertEqual(self.reconcile()["overall"], "BLOCKED")

    def test_missing_screenshot_or_log_blocks_green_matrix(self):
        for name in BRIDGE.REQUIRED_FILES:
            file = self.out / name
            file.unlink()
            self.assertEqual(self.reconcile()["overall"], "BLOCKED")
            file.write_text("restored")

    def test_runtime_error_fails_even_if_scenario_claims_pass(self):
        self.manifest["suites"]["ui"]["scenarios"][0]["runtime_errors"]["material"] = ["TypeError"]
        self.assertEqual(self.reconcile()["overall"], "FAIL")

    def test_functional_failure_is_not_hidden_by_missing_evidence(self):
        self.manifest["suites"]["ui"]["scenarios"][0]["status"] = "FAIL"
        (self.out / "http.log").unlink()
        self.assertEqual(self.reconcile()["overall"], "FAIL")

    def test_skipped_matrix_and_missing_error_capture_block(self):
        self.env["QV_MATRIX_OUTCOME"] = "skipped"
        self.assertEqual(self.reconcile()["overall"], "BLOCKED")
        self.env["QV_MATRIX_OUTCOME"] = "success"
        del self.manifest["suites"]["ui"]["scenarios"][0]["runtime_errors"]
        self.assertEqual(self.reconcile()["overall"], "BLOCKED")

    def test_cli_missing_manifest_writes_blocked_receipt(self):
        result = subprocess.run(["python3", str(ROOT / "scripts/runtime-proof-evidence.py"),
                                 str(self.target), str(self.out)], cwd=self.harness,
                                env={**os.environ, **self.env}, capture_output=True)
        self.assertEqual(result.returncode, 1)
        manifest = json.loads((self.out / "proof-manifest.json").read_text())
        self.assertEqual(manifest["overall"], "BLOCKED")
        self.assertEqual(len(manifest["artifacts"]), len(BRIDGE.REQUIRED_FILES))

    def test_workflow_has_only_manual_trigger_and_no_default_refs(self):
        text = (ROOT / ".github/workflows/runtime-proof.yml").read_text()
        events = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertIn("  workflow_dispatch:", events)
        for forbidden in ("pull_request:", "push:", "schedule:", "issue_comment:", "default:"):
            self.assertNotIn(forbidden, events)
        self.assertIn("cancel-in-progress: false", text)
        self.assertEqual(text.count("persist-credentials: false"), 2)
        self.assertNotIn("contents: write", text)
        self.assertLess(text.index("Reject mutable"), text.index("Checkout harness"))


if __name__ == "__main__":
    unittest.main()
