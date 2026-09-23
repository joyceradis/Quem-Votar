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

    def test_workflow_is_checkout_ui_only_and_persists_artifact_before_gate(self):
        workflow = (ROOT / ".github/workflows/runtime-proof.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("target_ref:", workflow)
        self.assertIn("Execute UI proof matrix", workflow)
        self.assertNotIn("network_policy", workflow)
        self.assertNotIn("target_mode", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertLess(workflow.index("Upload canonical proof artifact"), workflow.index("Enforce binary merge gate"))
        self.assertIn('if merge_gate != "PASS"', workflow)

    def test_ui_harness_preserves_seeded_storage_and_exercises_async_render(self):
        script = (ROOT / "scripts/runtime-proof.cjs").read_text(encoding="utf-8")
        self.assertNotIn("network-summary.json", script)
        self.assertNotIn("google-analytics.com/.*collect", script)
        self.assertNotIn("context.addInitScript(() => localStorage.removeItem", script)
        self.assertIn('localStorage.setItem("qv_compare"', script)
        self.assertIn("waitForComparePeople(page, 2)", script)
        self.assertIn("waitForCompareEmpty(page)", script)
        self.assertIn("delayed-compare-render-waits-for-terminal-state", script)
        self.assertIn("await sleep(700)", script)
        self.assertIn('manifest.merge_gate = manifest.overall === "PASS" ? "PASS" : "FAIL"', script)


if __name__ == "__main__":
    unittest.main()
