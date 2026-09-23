import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RuntimeProofContractTests(unittest.TestCase):
    def test_manifest_schema_has_four_explicit_states(self):
        schema = json.loads((ROOT / "docs/runtime-proof-manifest.schema.json").read_text(encoding="utf-8"))
        states = {"PASS", "FAIL", "INCONCLUSIVE", "BLOCKED"}
        self.assertEqual(set(schema["properties"]["overall"]["enum"]), states)
        suite_status = schema["properties"]["suites"]["additionalProperties"]["properties"]["status"]["enum"]
        self.assertEqual(set(suite_status), states)

    def test_workflow_is_reusable_and_persists_artifact_before_enforcement(self):
        workflow = (ROOT / ".github/workflows/runtime-proof.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("target_ref:", workflow)
        self.assertIn("- ui", workflow)
        self.assertIn("- network", workflow)
        self.assertIn("- all", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertLess(workflow.index("Upload canonical proof artifact"), workflow.index("Enforce manifest outcome"))

    def test_harness_has_no_issue_specific_head_sha_and_never_maps_no_collect_to_pass(self):
        script = (ROOT / "scripts/runtime-proof.cjs").read_text(encoding="utf-8")
        self.assertNotIn("e0c0bcc61d21e5967add04254582cac59561933d", script)
        self.assertNotIn("753c754c4f150070c4dfeb36dc99fccf828f51e3", script)
        self.assertIn('reason: "NO_COLLECT"', script)
        self.assertIn('"INCONCLUSIVE"', script)
        self.assertIn("network-summary.json", script)
        self.assertIn("payload_sha256", script)
        self.assertIn("Raw request values are not persisted.", script)


if __name__ == "__main__":
    unittest.main()
