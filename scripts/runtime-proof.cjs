const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

function isLoopbackHost(hostname) {
  return hostname === "127.0.0.1" || hostname === "localhost" || hostname === "::1";
}

function normalizeLocalBase(raw) {
  const url = new URL(raw);
  assert.equal(url.protocol, "http:", "scope:BASE_MUST_BE_HTTP");
  assert.ok(isLoopbackHost(url.hostname), "scope:BASE_MUST_BE_LOOPBACK");
  if (!url.pathname.endsWith("/")) url.pathname += "/";
  return url.toString();
}

const BASE = normalizeLocalBase(process.env.QV_BASE_URL || "http://127.0.0.1:8000/");
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

async function installLocalOnlyFirewall(context) {
  await context.route("**/*", async route => {
    const raw = route.request().url();
    if (raw.startsWith("data:") || raw.startsWith("blob:") || raw.startsWith("about:")) {
      await route.continue();
      return;
    }

    let url;
    try {
      url = new URL(raw);
    } catch {
      await route.abort("blockedbyclient");
      return;
    }

    if (url.protocol === "http:" && isLoopbackHost(url.hostname)) {
      await route.continue();
      return;
    }

    await route.abort("blockedbyclient");
  });
}

async function installLifecycleProbe(page, events) {
  await page.exposeFunction("__qvLifecycleEvent", eventName => {
    events.push(String(eventName));
  });
  await page.addInitScript(() => {
    window.addEventListener("pagehide", () => {
      void window.__qvLifecycleEvent("pagehide");
    });
    window.addEventListener("unload", () => {
      void window.__qvLifecycleEvent("unload");
    });
  });
}

async function exerciseLifecycleAndClose(page, events) {
  if (!page || page.isClosed()) return;
  events.length = 0;
  await page.goto("about:blank", { waitUntil: "load" });
  await page.waitForTimeout(25);
  assert.ok(events.includes("pagehide"), "teardown:PAGEHIDE_NOT_OBSERVED");
  await page.close();
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

async function loadCandidateIds(page) {
  await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
  await page.waitForSelector("button[data-compare-id]");
  const buttons = page.locator("button[data-compare-id]");
  assert.ok(await buttons.count() >= 4, "ui:INSUFFICIENT_COMPARE_BUTTONS");
  return buttons.evaluateAll(nodes => nodes.slice(0, 4).map(node => node.dataset.compareId));
}

async function runScenario(browser, suite, name, fn, contextOptions = { viewport: { width: 1366, height: 900 } }) {
  let context;
  let page;
  let error = null;
  const lifecycle = [];

  try {
    context = await browser.newContext({ ...contextOptions, serviceWorkers: "block" });
    await installLocalOnlyFirewall(context);
    page = await context.newPage();
    await installLifecycleProbe(page, lifecycle);
    await fn({ context, page });
  } catch (caught) {
    error = caught;
  } finally {
    try {
      await exerciseLifecycleAndClose(page, lifecycle);
    } catch (teardownError) {
      error = error
        ? new Error(errText(error) + " | " + errText(teardownError))
        : teardownError;
    }

    if (context) {
      try {
        await context.close();
      } catch (contextError) {
        error = error
          ? new Error(errText(error) + " | " + errText(contextError))
          : contextError;
      }
    }
  }

  if (error) {
    record(suite, name, "FAIL", { error: errText(error), lifecycle: [...new Set(lifecycle)] });
  } else {
    record(suite, name, "PASS", { lifecycle: [...new Set(lifecycle)] });
  }
}

async function runUi(browser) {
  const suite = { status: "BLOCKED", scenarios: [] };
  manifest.suites.ui = suite;

  await runScenario(browser, suite, "keyboard-one-selection-focus", async ({ page }) => {
    const ids = await loadCandidateIds(page);
    const first = page.locator('[data-compare-id="' + ids[0] + '"]');
    await first.focus();
    await page.keyboard.press("Shift+Tab");
    assert.notEqual(await page.evaluate(() => document.activeElement && document.activeElement.dataset && document.activeElement.dataset.compareId), ids[0]);
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.dataset && document.activeElement.dataset.compareId), ids[0]);
    await page.keyboard.press("Space");
    assert.equal(await first.getAttribute("aria-pressed"), "true");
    assert.match(await page.locator("#compareCount").innerText(), /Escolha mais 1/);
    assert.equal(await page.locator("#openCompare").getAttribute("aria-disabled"), "true");
    assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.dataset && document.activeElement.dataset.compareId), ids[0]);
    suite.desktop_screenshot = await screenshot(page, "desktop-1366x900.png");
  });

  await runScenario(browser, suite, "two-selection-opens", async ({ page }) => {
    const ids = await loadCandidateIds(page);
    await page.locator('[data-compare-id="' + ids[0] + '"]').click();
    await page.locator('[data-compare-id="' + ids[1] + '"]').focus();
    await page.keyboard.press("Enter");
    assert.equal(await page.locator("#openCompare").getAttribute("aria-disabled"), "false");
  });

  await runScenario(browser, suite, "three-selection-limit", async ({ page }) => {
    const ids = await loadCandidateIds(page);
    await page.locator('[data-compare-id="' + ids[0] + '"]').click();
    await page.locator('[data-compare-id="' + ids[1] + '"]').click();
    await page.locator('[data-compare-id="' + ids[2] + '"]').click();
    assert.match(await page.locator("#compareCount").innerText(), /Limite de 3/);
    assert.equal(await page.locator('[data-compare-id="' + ids[3] + '"]').isDisabled(), true);
  });

  await runScenario(browser, suite, "removal-preserves-node-focus", async ({ page }) => {
    const ids = await loadCandidateIds(page);
    await page.locator('[data-compare-id="' + ids[0] + '"]').click();
    await page.locator('[data-compare-id="' + ids[1] + '"]').click();
    await page.locator('[data-compare-id="' + ids[2] + '"]').click();
    const button = page.locator('[data-compare-id="' + ids[1] + '"]');
    await button.focus();
    await page.keyboard.press("Enter");
    assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.dataset && document.activeElement.dataset.compareId), ids[1]);
    assert.equal(await page.locator('[data-compare-id="' + ids[3] + '"]').isDisabled(), false);
  });

  await runScenario(browser, suite, "canonical-invalid-duplicate-url", async ({ page }) => {
    const ids = await loadCandidateIds(page);
    await page.goto(BASE + "comparar.html?ids=" + encodeURIComponent(ids[0] + "," + ids[0] + ",invalid," + ids[2]), { waitUntil: "domcontentloaded" });
    await waitForComparePeople(page, 2);
    assert.equal(await page.locator(".compare-person").count(), 2);
    assert.equal(new URL(await page.url()).searchParams.get("ids"), ids[0] + "," + ids[2]);
    assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("qv_compare") || "[]")), [ids[0], ids[2]]);
  });

  await runScenario(browser, suite, "empty-ids-does-not-reuse-storage", async ({ page }) => {
    const ids = await loadCandidateIds(page);
    await page.evaluate(values => localStorage.setItem("qv_compare", JSON.stringify(values)), [ids[0], ids[2]]);
    await page.goto(BASE + "comparar.html?ids=", { waitUntil: "domcontentloaded" });
    await waitForCompareEmpty(page);
    assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("qv_compare") || "[]")), []);
    assert.match(await page.locator("#compareMount").innerText(), /Ninguém selecionado/);
  });

  await runScenario(browser, suite, "delayed-compare-render-waits-for-terminal-state", async ({ page }) => {
    const ids = await loadCandidateIds(page);
    await page.evaluate(values => localStorage.setItem("qv_compare", JSON.stringify(values)), [ids[0], ids[2]]);
    const pattern = /data\/generated\/candidates-(federal|estadual)\.json/;
    const handler = async route => {
      await sleep(700);
      await route.continue();
    };

    await page.route(pattern, handler);
    try {
      const started = Date.now();
      await page.goto(BASE + "comparar.html?ids=" + encodeURIComponent(ids[0] + "," + ids[2]), { waitUntil: "domcontentloaded" });
      await waitForComparePeople(page, 2);
      assert.ok(Date.now() - started >= 500, "compare:ASYNC_WAIT_NOT_EXERCISED");
    } finally {
      await page.unroute(pattern, handler);
    }
  });

  await runScenario(browser, suite, "cross-tab-storage-sync", async ({ context, page }) => {
    const ids = await loadCandidateIds(page);
    const profile = await context.newPage();
    try {
      await profile.goto(BASE + "candidato.html?id=" + encodeURIComponent(ids[0]), { waitUntil: "domcontentloaded" });
      await profile.waitForSelector("#profileCompare");
      await profile.locator("#profileCompare").click();
      await page.bringToFront();
      await page.waitForFunction(id => {
        const node = document.querySelector('[data-compare-id="' + id + '"]');
        return node && node.getAttribute("aria-pressed") === "true";
      }, ids[0]);
      assert.equal(await page.locator('[data-compare-id="' + ids[0] + '"]').innerText(), "Remover");
    } finally {
      await profile.close();
    }
  });

  await runScenario(
    browser,
    suite,
    "mobile-390x844",
    async ({ page }) => {
      await loadCandidateIds(page);
      const inspectLayout = () => page.evaluate(() => {
        const root = document.documentElement;
        const viewportWidth = root.clientWidth;
        const offenders = Array.from(document.querySelectorAll("body *"))
          .map(node => {
            const rect = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return {
              tag: node.tagName.toLowerCase(),
              id: node.id || null,
              class: typeof node.className === "string" ? node.className : null,
              left: Math.round(rect.left * 10) / 10,
              right: Math.round(rect.right * 10) / 10,
              width: Math.round(rect.width * 10) / 10,
              position: style.position,
              transform: style.transform
            };
          })
          .filter(item => item.right > viewportWidth + 1 || item.left < -1)
          .slice(0, 20);
        return {
          clientWidth: viewportWidth,
          scrollWidth: root.scrollWidth,
          delta: root.scrollWidth - viewportWidth,
          offenders
        };
      });
      const beforeSelection = await inspectLayout();
      const first = page.locator("button[data-compare-id]").first();
      await first.scrollIntoViewIfNeeded();
      await first.tap();
      assert.equal(await first.getAttribute("aria-pressed"), "true");
      assert.equal(await page.locator("#compareTray").isVisible(), true);
      const afterSelection = await inspectLayout();
      suite.mobile_layout = { before_selection: beforeSelection, after_selection: afterSelection };
      assert.ok(beforeSelection.delta <= 1, "ui:HORIZONTAL_OVERFLOW_BEFORE_SELECTION " + JSON.stringify(beforeSelection));
      assert.ok(afterSelection.delta <= 1, "ui:HORIZONTAL_OVERFLOW_AFTER_SELECTION " + JSON.stringify(afterSelection));
      suite.mobile_screenshot = await screenshot(page, "mobile-390x844.png");
    },
    { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }
  );

  suite.status = worst(suite.scenarios.map(item => item.status));
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
