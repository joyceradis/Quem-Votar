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
        self.assertIn("python3 -m http.server 8000 --bind 127.0.0.1", workflow)
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
        self.assertIn("teardown:PAGE_ALREADY_CLOSED", script)
        self.assertIn("await context.close()", script)
        self.assertIn("await page.unroute(pattern, handler)", script)
        self.assertIn("await drainPendingTasks(pending)", script)
        self.assertIn("await route.fallback()", script)

    def test_material_runtime_errors_are_checked_after_teardown_before_pass(self):
        script = (ROOT / "scripts/runtime-proof.cjs").read_text(encoding="utf-8")
        scenario = script[script.index("async function runScenario"):script.index("async function runHarnessInvariantChecks")]
        context_closed = scenario.index("await context.close()")
        final_runtime_check = scenario.index("if (runtimeErrors.material.length)")
        status_decision = scenario.index("if (error)", final_runtime_check)
        self.assertLess(context_closed, final_runtime_check)
        self.assertLess(final_runtime_check, status_decision)
        self.assertIn("error = combineErrors(", scenario[final_runtime_check:status_decision])
        self.assertNotIn("runtimeErrors.material, []", scenario)
        self.assertIn("`${message}: ${errText(primary)} | ${errText(secondary)}`", script)

    def test_ui_scenarios_are_independent_and_merge_gate_is_fail_closed(self):
        script = (ROOT / "scripts/runtime-proof.cjs").read_text(encoding="utf-8")
        self.assertIn("keyboard-one-selection-focus", script)
        self.assertIn("two-selection-opens", script)
        self.assertIn('page.locator("#openCompare").click()', script)
        self.assertIn("three-selection-limit", script)
        self.assertIn("empty-ids-does-not-reuse-storage", script)
        self.assertIn("delayed-compare-render-waits-for-terminal-state", script)
        self.assertIn("delayed-route-preserves-local-firewall", script)
        self.assertIn("teardown-rejects-preclosed-page", script)
        self.assertIn("pending-route-drain-waits", script)
        self.assertIn("pending-route-rejection-propagates", script)
        self.assertIn("cross-tab-storage-sync", script)
        self.assertIn("mobile-390x844", script)
        self.assertIn("profile-three-questions-anchors-keyboard", script)
        self.assertIn("profile-occupation-is-self-declared-fact-without-mandate", script)
        self.assertIn("profile-current-mandate-is-current-activity", script)
        self.assertIn("profile-generic-occupation-is-not-shown-as-today-fact", script)
        self.assertIn("profile-web-share", script)
        self.assertIn("profile-clipboard-fallback", script)
        self.assertIn("profile-mobile-390x844", script)
        self.assertIn('page.on("pageerror"', script)
        self.assertIn('page.on("console"', script)
        self.assertIn('context.addInitScript', script)
        self.assertIn("withDelayedCandidateRoutes(page, 700", script)
        self.assertIn('manifest.merge_gate = manifest.overall === "PASS" ? "PASS" : "FAIL"', script)

    def test_profile_anchor_waits_for_natural_visibility_without_forcing_scroll(self):
        script = (ROOT / "scripts/runtime-proof.cjs").read_text(encoding="utf-8")
        self.assertIn("async function waitForViewportIntersection", script)
        self.assertIn("page.waitForFunction(", script)
        self.assertIn('throw new Error(label + ": " + errText(error))', script)

        profile = script[
            script.index('"profile-three-questions-anchors-keyboard"'):
            script.index('"profile-occupation-is-self-declared-fact-without-mandate"')
        ]
        self.assertIn("waitForViewportIntersection(page", profile)
        self.assertIn("profile:ANCHOR_NOT_VISIBLE_", profile)
        self.assertNotIn("scrollIntoView", profile)

        mobile_start = script.index('"profile-mobile-390x844"')
        mobile = script[mobile_start:script.index("suite.status = worst", mobile_start)]
        self.assertIn('waitForViewportIntersection(page, "#impacto", "profile:MOBILE_IMPACT_NOT_VISIBLE")', mobile)
        self.assertIn("profile:MOBILE_COMPARE_NOT_VISIBLE", mobile)
        self.assertIn("profile:MOBILE_SHARE_NOT_VISIBLE", mobile)
        self.assertNotIn("scrollIntoView", mobile)

    def test_occupation_is_shown_in_today_as_self_declared_fact_without_mandate(self):
        # Ocupação sem mandato em exercício aparece em #faz-hoje como fato
        # autodeclarado e fonteado (nunca como atuação institucional
        # verificada) em vez de "sem dados", e continua também aparecendo em
        # Dados eleitorais — as duas seções não são mutuamente exclusivas.
        script = (ROOT / "scripts/runtime-proof.cjs").read_text(encoding="utf-8")
        scenario = script[
            script.index('"profile-occupation-is-self-declared-fact-without-mandate"'):
            script.index('"profile-current-mandate-is-current-activity"')
        ]
        self.assertIn("/Ocupação declarada/i", scenario)
        self.assertIn('page.locator("#faz-hoje")', scenario)
        self.assertIn("occupationOnly.occupation", scenario)
        self.assertIn("Autodeclarado no registro de candidatura ao TSE", scenario)
        self.assertIn("Sem atuação pública atual confirmada nesta base", scenario)

    def test_generic_occupation_falls_back_to_empty_state_but_stays_in_electoral_data(self):
        # "Outros" (código TSE 956) não descreve nada: precisa continuar em
        # Dados eleitorais sem filtro (comportamento congelado e pré-existente),
        # mas não pode ser exibida em #faz-hoje como se fosse um fato utilizável —
        # o vazio honesto é a resposta certa, não "sem dados" nem "Outros".
        script = (ROOT / "scripts/runtime-proof.cjs").read_text(encoding="utf-8")
        scenario = script[
            script.index('"profile-generic-occupation-is-not-shown-as-today-fact"'):
            script.index('"profile-web-share"')
        ]
        self.assertIn("/Ocupação declarada/i", scenario)
        self.assertIn("genericOccupationOnly.occupation", scenario)
        self.assertIn("profile:GENERIC_OCCUPATION_MISSING_FROM_ELECTORAL_DATA", scenario)
        self.assertIn("profile:GENERIC_OCCUPATION_SHOWN_AS_TODAY_FACT", scenario)
        self.assertIn("Sem atuação pública atual confirmada nesta base", scenario)
        self.assertIn('!todayText.includes(genericOccupationOnly.occupation)', scenario)

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
