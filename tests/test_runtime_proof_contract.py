import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RuntimeProofContractTests(unittest.TestCase):
    def test_manifest_keeps_diagnostic_states_but_merge_gate_is_binary(self):
        schema = json.loads((ROOT / "docs/runtime-proof-manifest.schema.json").read_text(encoding="utf-8"))
        states = {"PASS", "FAIL", "INCONCLUSIVE", "BLOCKED"}
        self.assertEqual(set(schema["properties"]["overall"]["enum"]), states)
        self.assertEqual(set(schema["properties"]["merge_gate"]["enum"]), {"PASS", "FAIL"})
        self.assertEqual(schema["properties"]["target"]["properties"]["mode"]["const"], "checkout")
        self.assertEqual(schema["properties"]["requested"]["properties"]["suite"]["const"], "ui")
        self.assertTrue(schema["$id"].startswith("urn:"))

    def test_workflow_is_checkout_ui_only_and_persists_artifact_before_gate(self):
        workflow = (ROOT / ".github/workflows/runtime-proof.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("target_ref:", workflow)
        self.assertIn("Execute UI proof matrix", workflow)
        self.assertIn("QV_BASE_URL: http://127.0.0.1:8000/", workflow)
        self.assertNotIn("target_mode", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertLess(workflow.index("Upload canonical proof artifact"), workflow.index("Enforce binary merge gate"))
        self.assertIn('if merge_gate != "PASS"', workflow)

    def test_each_scenario_gets_fresh_context_and_observable_teardown(self):
        script = (ROOT / "scripts/runtime-proof.cjs").read_text(encoding="utf-8")
        self.assertIn("async function runScenario", script)
        self.assertIn("browser.newContext", script)
        self.assertIn('serviceWorkers: "block"', script)
        self.assertIn('context.route("**/*"', script)
        self.assertIn('"pagehide"', script)
        self.assertIn('"unload"', script)
        self.assertIn("exerciseLifecycleAndClose(page, lifecycle)", script)
        self.assertIn("await context.close()", script)
        self.assertIn("await page.unroute(pattern, handler)", script)

    def test_ui_scenarios_are_independent_and_merge_gate_is_fail_closed(self):
        script = (ROOT / "scripts/runtime-proof.cjs").read_text(encoding="utf-8")
        self.assertIn("keyboard-one-selection-focus", script)
        self.assertIn("two-selection-opens", script)
        self.assertIn("three-selection-limit", script)
        self.assertIn("empty-ids-does-not-reuse-storage", script)
        self.assertIn("delayed-compare-render-waits-for-terminal-state", script)
        self.assertIn("cross-tab-storage-sync", script)
        self.assertIn("mobile-390x844", script)
        self.assertIn("await sleep(700)", script)
        self.assertIn('manifest.merge_gate = manifest.overall === "PASS" ? "PASS" : "FAIL"', script)

    def test_changed_surface_has_no_remote_runtime_or_environment_lane(self):
        paths = [
            ROOT / ".github/workflows/runtime-proof.yml",
            ROOT / "scripts/runtime-proof.cjs",
            ROOT / "docs/RUNTIME_PROOF.md",
            ROOT / "docs/runtime-proof-manifest.schema.json",
        ]
        text = "\n".join(path.read_text(encoding="utf-8").lower() for path in paths)
        forbidden = [
            "target_" + "mode",
            "served_" + "revision",
            "pro" + "duction",
            "de" + "ploy",
            "google-" + "analytics",
            "google" + "tagmanager",
            "g" + "tag(",
            "ga" + "4",
        ]
        for token in forbidden:
            self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
