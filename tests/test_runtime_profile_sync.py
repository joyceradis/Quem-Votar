"""Behavioral regressions for #136; fake frames, no browser/runtime dispatch."""
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

BOOTSTRAP = r"""
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("scripts/runtime-proof.cjs", "utf8");
function section(start, end) {
  assert.ok(source.includes(start) && source.includes(end));
  return source.slice(source.indexOf(start), source.indexOf(end));
}
const sandbox = {
  assert, location: { hash: "#impacto" }, window: { innerHeight: 844 },
  document: { querySelector: () => null },
  errText: error => String(error.message || error)
};
vm.createContext(sandbox);
vm.runInContext(section("async function waitForViewportIntersection(", "async function installLocalOnlyFirewall("), sandbox);
function framesPage(frames) {
  let polls = 0;
  return {
    get polls() { return polls; },
    async waitForFunction(predicate, id, options) {
      assert.equal(options.timeout, 2000);
      for (const frame of frames) {
        polls++;
        sandbox.location.hash = frame.hash ?? "#impacto";
        sandbox.document.querySelector = target => {
          assert.equal(target, id);
          return frame.rect ? { getBoundingClientRect: () => frame.rect } : null;
        };
        if (predicate(id)) return;
      }
      throw new Error("Timeout 2000ms exceeded");
    }
  };
}
"""

class RuntimeProfileSyncTests(unittest.TestCase):
    def run_js(self, body):
        result = subprocess.run(
            ["node", "-e", BOOTSTRAP + "\n(async () => {\n" + body +
             "\n})().catch(error => { console.error(error); process.exitCode = 1; });"],
            cwd=ROOT, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hash_alone_waits_for_natural_visibility(self):
        self.run_js(r"""
const page = framesPage([
  { rect: { top: 1000, bottom: 1200 } },
  { rect: { top: 900, bottom: 1100 } },
  { rect: { top: 700, bottom: 900 } }
]);
await sandbox.waitForViewportIntersection(page, "#impacto", "profile:ANCHOR_NOT_VISIBLE_impacto");
assert.equal(page.polls, 3);
""")

    def test_missing_target_and_offscreen_rects_do_not_pass(self):
        self.run_js(r"""
const page = framesPage([
  {},
  { rect: { top: -200, bottom: 0 } },
  { rect: { top: 844, bottom: 1000 } }
]);
await assert.rejects(() => sandbox.waitForViewportIntersection(page, "#impacto", "profile:ANCHOR_NOT_VISIBLE_impacto"),
  /profile:ANCHOR_NOT_VISIBLE_impacto: Timeout 2000ms exceeded/);
assert.equal(page.polls, 3);
""")

    def test_visibility_timeout_is_recorded_as_scenario_fail(self):
        self.run_js(r"""
sandbox.installLocalOnlyFirewall = async () => {};
sandbox.installLifecycleProbe = async () => {};
sandbox.installRuntimeErrorProbe = () => {};
sandbox.exerciseLifecycleAndClose = async () => {};
sandbox.combineErrors = (primary, secondary) => primary || secondary;
sandbox.record = (suite, name, status, details) => suite.scenarios.push({ name, status, ...details });
vm.runInContext(section("async function runScenario(", "async function runHarnessInvariantChecks("), sandbox);
const page = framesPage([{ rect: { top: 1000, bottom: 1200 } }]);
let closed = false;
const browser = { newContext: async () => ({
  newPage: async () => page, close: async () => { closed = true; }
}) };
const suite = { scenarios: [] };
await sandbox.runScenario(browser, suite, "anchor-timeout",
  async ({ page }) => sandbox.waitForViewportIntersection(page, "#impacto", "profile:ANCHOR_NOT_VISIBLE_impacto"));
assert.equal(closed, true);
assert.equal(suite.scenarios.length, 1);
assert.equal(suite.scenarios[0].status, "FAIL");
assert.match(suite.scenarios[0].error, /profile:ANCHOR_NOT_VISIBLE_impacto/);
""")

    def test_case_insensitive_label_preserves_occupation_semantics(self):
        self.run_js(r"""
const block = section(
  '  await runScenario(browser, suite, "profile-occupation-is-not-current-activity"',
  '  await runScenario(browser, suite, "profile-current-mandate-is-current-activity"'
);
const start = block.indexOf("async ({ page }) => {") + "async ({ page }) => {".length;
const body = block.slice(start, block.lastIndexOf("});"));
sandbox.loadProfileFixtures = async () => ({ occupationOnly: { occupation: "PROFESSOR" } });
sandbox.openProfile = async () => {};
const scenario = vm.runInContext("(async (page) => {" + body + "})", sandbox);
const page = (electoral, today) => ({
  locator: selector => ({ innerText: async () => {
    assert.ok(["#dados-eleitorais", "#faz-hoje"].includes(selector));
    return selector === "#dados-eleitorais" ? electoral : today;
  } })
});
for (const label of ["Ocupação declarada", "OCUPAÇÃO DECLARADA"]) {
  await scenario(page(label + ": PROFESSOR", "Sem atuação atual confirmada"));
  await assert.rejects(() => scenario(page(label + ": PROFESSOR", "PROFESSOR")));
}
await assert.rejects(() => scenario(page("OCUPAÇÃO DECLARADA: OUTRA", "Sem atuação atual confirmada")));
await assert.rejects(() => scenario(page("PROFESSOR", "Sem atuação atual confirmada")));
""")

    def test_desktop_and_mobile_use_hash_then_observation_only_wait(self):
        self.run_js(r"""
const desktop = section(
  '  await runScenario(browser, suite, "profile-three-questions-anchors-keyboard"',
  '  await runScenario(browser, suite, "profile-occupation-is-not-current-activity"'
);
const mobile = source.slice(source.indexOf('    "profile-mobile-390x844",'));
assert.ok(desktop.includes('await link.click();'));
assert.ok(desktop.includes('await page.waitForFunction(hash => location.hash === hash'));
assert.ok(desktop.indexOf('await page.waitForFunction(hash => location.hash === hash') <
  desktop.indexOf('await waitForViewportIntersection(page'));
assert.ok(mobile.includes('await impactLink.tap();'));
assert.ok(mobile.includes('await page.waitForFunction(() => location.hash === "#impacto")'));
assert.ok(mobile.indexOf('await page.waitForFunction(() => location.hash === "#impacto")') <
  mobile.indexOf('await waitForViewportIntersection(page'));
assert.ok(desktop.includes('await waitForViewportIntersection(page'));
assert.ok(mobile.includes('await waitForViewportIntersection(page'));
const helper = section("async function waitForViewportIntersection(", "async function installLocalOnlyFirewall(");
for (const code of [helper, desktop, mobile]) {
  assert.doesNotMatch(code, /scrollIntoView|scrollTo\s*\(|scrollBy\s*\(|scrollTop\s*=/);
}
for (const message of ["profile:MOBILE_COMPARE_NOT_VISIBLE", "profile:MOBILE_SHARE_NOT_VISIBLE",
                       "profile:HORIZONTAL_OVERFLOW"]) {
  assert.ok(mobile.includes(message));
}
""")

if __name__ == "__main__":
    unittest.main()
