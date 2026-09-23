const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const BASE = process.env.QV_BASE_URL || "http://127.0.0.1:8000/";
const OUT = path.resolve(process.env.QV_PROOF_OUT || "runtime-proof-artifact");
const SCREENSHOTS = path.join(OUT, "screenshots");

fs.mkdirSync(SCREENSHOTS, { recursive: true });

const manifest = {
  schema_version: "1.0.0",
  generated_at: new Date().toISOString(),
  run: {
    id: process.env.QV_RUN_ID || null,
    attempt: process.env.QV_RUN_ATTEMPT || null,
    harness_sha: process.env.QV_HARNESS_SHA || null
  },
  target: {
    ref: process.env.QV_TARGET_REF || null,
    sha: process.env.QV_TARGET_SHA || null,
    mode: "checkout",
    base_url: BASE
  },
  requested: {
    suite: "ui"
  },
  overall: "BLOCKED",
  merge_gate: "FAIL",
  suites: {},
  artifacts: []
};

const statusWeight = { PASS: 0, INCONCLUSIVE: 1, BLOCKED: 2, FAIL: 3 };

function worst(statuses) {
  if (!statuses.length) return "BLOCKED";
  return statuses.reduce((a, b) => statusWeight[b] > statusWeight[a] ? b : a, "PASS");
}

function errText(error) {
  return String(error && (error.message || error) || "unknown error");
}

function record(suite, name, status, details = {}) {
  suite.scenarios.push({ name, status, ...details });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function screenshot(page, filename) {
  const destination = path.join(SCREENSHOTS, filename);
  await page.screenshot({ path: destination, fullPage: false });
  return path.relative(OUT, destination);
}

async function waitForComparePeople(page, expected) {
  await page.waitForFunction(count => {
    const mount = document.querySelector("#compareMount");
    if (!mount) return false;
    if ((mount.textContent || "").includes("Não foi possível carregar todas as candidaturas")) return true;
    return mount.querySelectorAll(".compare-person").length === count;
  }, expected);
  const text = await page.locator("#compareMount").innerText();
  assert.ok(!text.includes("Não foi possível carregar todas as candidaturas"), "compare:LOAD_ERROR");
}

async function waitForCompareEmpty(page) {
  await page.waitForFunction(() => {
    const mount = document.querySelector("#compareMount");
    if (!mount) return false;
    if ((mount.textContent || "").includes("Não foi possível carregar todas as candidaturas")) return true;
    return Boolean(mount.querySelector(".compare-empty"));
  });
  const text = await page.locator("#compareMount").innerText();
  assert.ok(!text.includes("Não foi possível carregar todas as candidaturas"), "compare:LOAD_ERROR");
}

async function runUi(browser) {
  const suite = { status: "BLOCKED", scenarios: [] };
  manifest.suites.ui = suite;

  let context;
  try {
    context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    await context.route(/googletagmanager\.com|google-analytics\.com/, route => route.abort());

    const page = await context.newPage();
    await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("button[data-compare-id]");
    await page.evaluate(() => localStorage.removeItem("qv_compare"));
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForSelector("button[data-compare-id]");

    const buttons = page.locator("button[data-compare-id]");
    assert.ok(await buttons.count() >= 4, "ui:INSUFFICIENT_COMPARE_BUTTONS");
    const ids = await buttons.evaluateAll(nodes => nodes.slice(0, 4).map(node => node.dataset.compareId));

    const check = async (name, fn) => {
      try {
        await fn();
        record(suite, name, "PASS");
      } catch (error) {
        record(suite, name, "FAIL", { error: errText(error) });
      }
    };

    await check("keyboard-one-selection-focus", async () => {
      await buttons.nth(0).focus();
      await page.keyboard.press("Shift+Tab");
      assert.notEqual(await page.evaluate(() => document.activeElement?.dataset?.compareId), ids[0]);
      await page.keyboard.press("Tab");
      assert.equal(await page.evaluate(() => document.activeElement?.dataset?.compareId), ids[0]);
      await page.keyboard.press("Space");
      assert.equal(await buttons.nth(0).getAttribute("aria-pressed"), "true");
      assert.match(await page.locator("#compareCount").innerText(), /Escolha mais 1/);
      assert.equal(await page.locator("#openCompare").getAttribute("aria-disabled"), "true");
      assert.equal(await page.evaluate(() => document.activeElement?.dataset?.compareId), ids[0]);
    });

    await check("two-selection-opens", async () => {
      await page.locator(`[data-compare-id="${ids[1]}"]`).focus();
      await page.keyboard.press("Enter");
      assert.equal(await page.locator("#openCompare").getAttribute("aria-disabled"), "false");
    });

    await check("three-selection-limit", async () => {
      await page.locator(`[data-compare-id="${ids[2]}"]`).click();
      assert.match(await page.locator("#compareCount").innerText(), /Limite de 3/);
      assert.equal(await page.locator(`[data-compare-id="${ids[3]}"]`).isDisabled(), true);
    });

    await check("removal-preserves-node-focus", async () => {
      const button = page.locator(`[data-compare-id="${ids[1]}"]`);
      await button.focus();
      await page.keyboard.press("Enter");
      assert.equal(await page.evaluate(() => document.activeElement?.dataset?.compareId), ids[1]);
      assert.equal(await page.locator(`[data-compare-id="${ids[3]}"]`).isDisabled(), false);
    });

    await check("canonical-invalid-duplicate-url", async () => {
      await page.goto(BASE + "comparar.html?ids=" + encodeURIComponent(`${ids[0]},${ids[0]},invalid,${ids[2]}`), { waitUntil: "domcontentloaded" });
      await waitForComparePeople(page, 2);
      assert.equal(await page.locator(".compare-person").count(), 2);
      assert.equal(new URL(await page.url()).searchParams.get("ids"), `${ids[0]},${ids[2]}`);
      assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("qv_compare") || "[]")), [ids[0], ids[2]]);
    });

    await check("empty-ids-does-not-reuse-storage", async () => {
      await page.evaluate(values => localStorage.setItem("qv_compare", JSON.stringify(values)), [ids[0], ids[2]]);
      await page.goto(BASE + "comparar.html?ids=", { waitUntil: "domcontentloaded" });
      await waitForCompareEmpty(page);
      assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("qv_compare") || "[]")), []);
      assert.match(await page.locator("#compareMount").innerText(), /Ninguém selecionado/);
    });

    await check("delayed-compare-render-waits-for-terminal-state", async () => {
      await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
      await page.evaluate(values => localStorage.setItem("qv_compare", JSON.stringify(values)), [ids[0], ids[2]]);
      await page.route(/data\/generated\/candidates-(federal|estadual)\.json/, async route => {
        await sleep(700);
        await route.continue();
      });
      const started = Date.now();
      await page.goto(BASE + "comparar.html?ids=" + encodeURIComponent(`${ids[0]},${ids[2]}`), { waitUntil: "domcontentloaded" });
      await waitForComparePeople(page, 2);
      assert.ok(Date.now() - started >= 500, "compare:ASYNC_WAIT_NOT_EXERCISED");
      await page.unroute(/data\/generated\/candidates-(federal|estadual)\.json/);
    });

    await check("cross-tab-storage-sync", async () => {
      await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
      await page.evaluate(() => localStorage.removeItem("qv_compare"));
      const profile = await context.newPage();
      try {
        await profile.goto(BASE + "candidato.html?id=" + encodeURIComponent(ids[0]), { waitUntil: "domcontentloaded" });
        await profile.waitForSelector("#profileCompare");
        await profile.locator("#profileCompare").click();
        await page.bringToFront();
        await page.waitForFunction(id => document.querySelector(`[data-compare-id="${id}"]`)?.getAttribute("aria-pressed") === "true", ids[0]);
        assert.equal(await page.locator(`[data-compare-id="${ids[0]}"]`).innerText(), "Remover");
      } finally {
        await profile.close();
      }
    });

    try {
      suite.desktop_screenshot = await screenshot(page, "desktop-1366x900.png");
    } catch (error) {
      suite.desktop_screenshot_error = errText(error);
    }

    await context.close();
    context = null;

    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    try {
      await mobile.route(/googletagmanager\.com|google-analytics\.com/, route => route.abort());
      const m = await mobile.newPage();
      try {
        await m.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
        await m.waitForSelector("button[data-compare-id]");
        assert.ok(await m.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth) <= 1);
        const first = m.locator("button[data-compare-id]").first();
        await first.scrollIntoViewIfNeeded();
        await first.tap();
        assert.equal(await first.getAttribute("aria-pressed"), "true");
        assert.equal(await m.locator("#compareTray").isVisible(), true);
        record(suite, "mobile-390x844", "PASS");
      } catch (error) {
        record(suite, "mobile-390x844", "FAIL", { error: errText(error) });
      }

      try {
        suite.mobile_screenshot = await screenshot(m, "mobile-390x844.png");
      } catch (error) {
        suite.mobile_screenshot_error = errText(error);
      }
    } finally {
      await mobile.close();
    }

    suite.status = worst(suite.scenarios.map(item => item.status));
  } catch (error) {
    record(suite, "ui-setup", "BLOCKED", { error: errText(error) });
    suite.status = "BLOCKED";
  } finally {
    if (context) await context.close().catch(() => {});
  }
}

function listFiles(root) {
  const entries = [];
  if (!fs.existsSync(root)) return entries;
  for (const name of fs.readdirSync(root)) {
    const full = path.join(root, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) entries.push(...listFiles(full));
    else entries.push(full);
  }
  return entries;
}

function finalizeArtifacts() {
  manifest.artifacts = listFiles(OUT)
    .filter(file => path.basename(file) !== "proof-manifest.json")
    .map(file => ({
      path: path.relative(OUT, file),
      bytes: fs.statSync(file).size,
      sha256: crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex")
    }))
    .sort((a, b) => a.path.localeCompare(b.path));
}

function writeManifest() {
  manifest.overall = worst(Object.values(manifest.suites).map(suite => suite.status));
  manifest.merge_gate = manifest.overall === "PASS" ? "PASS" : "FAIL";
  finalizeArtifacts();
  fs.writeFileSync(path.join(OUT, "proof-manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
  console.log(JSON.stringify({ overall: manifest.overall, merge_gate: manifest.merge_gate, suites: manifest.suites }, null, 2));
}

(async () => {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    await runUi(browser);
  } catch (error) {
    manifest.suites.harness = {
      status: "BLOCKED",
      scenarios: [{ name: "browser-launch", status: "BLOCKED", error: errText(error) }]
    };
  } finally {
    if (browser) await browser.close().catch(() => {});
    writeManifest();
  }
})();
