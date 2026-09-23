const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const BASE = process.env.QV_BASE_URL || "http://127.0.0.1:8000/";
const SUITE = process.env.QV_PROOF_SUITE || "ui";
const NETWORK_POLICY = process.env.QV_NETWORK_POLICY || "privacy-sentinels";
const OUT = path.resolve(process.env.QV_PROOF_OUT || "runtime-proof-artifact");
const TARGET_DIR = path.resolve(process.env.QV_TARGET_DIR || ".");
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
    checkout_sha: process.env.QV_TARGET_SHA || null,
    mode: process.env.QV_TARGET_MODE || "checkout",
    base_url: BASE,
    served_revision: (process.env.QV_TARGET_MODE || "checkout") === "checkout"
      ? (process.env.QV_TARGET_SHA || null)
      : null,
    revision_status: (process.env.QV_TARGET_MODE || "checkout") === "checkout"
      ? "VERIFIED_CHECKOUT"
      : "UNVERIFIED_PRODUCTION"
  },
  requested: {
    suite: SUITE,
    network_policy: NETWORK_POLICY
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
function decoded(value) {
  let out = String(value || "");
  for (let i = 0; i < 3; i += 1) {
    try { out = decodeURIComponent(out.replace(/\+/g, "%20")); } catch { break; }
  }
  return out;
}
function eventName(hit) {
  const url = new URL(hit.url);
  return url.searchParams.get("en") || new URLSearchParams(hit.postData || "").get("en") || "unknown";
}
function payload(hit) {
  return decoded(`${hit.url}\n${hit.postData || ""}`);
}
function payloadKeys(hit) {
  const url = new URL(hit.url);
  const body = new URLSearchParams(hit.postData || "");
  return {
    event: eventName(hit),
    method: hit.method,
    endpoint: `${url.hostname}${url.pathname}`,
    url_param_keys: [...new Set([...url.searchParams.keys()])].sort(),
    body_param_keys: [...new Set([...body.keys()])].sort(),
    payload_sha256: crypto.createHash("sha256").update(`${hit.url}\n${hit.postData || ""}`).digest("hex")
  };
}
function markerHits(scope, markers) {
  const body = scope.map(payload).join("\n").toLocaleLowerCase("pt-BR");
  return markers.filter(Boolean).filter(marker => body.includes(String(marker).toLocaleLowerCase("pt-BR")));
}
function record(suite, name, status, details = {}) {
  suite.scenarios.push({ name, status, ...details });
}
async function screenshot(page, filename) {
  const destination = path.join(SCREENSHOTS, filename);
  await page.screenshot({ path: destination, fullPage: true });
  return path.relative(OUT, destination);
}
async function settle(page) {
  await page.waitForTimeout(2500);
}
async function waitForComparePeople(page, expected) {
  await page.waitForFunction(count => {
    const mount = document.querySelector("#compareMount");
    if (!mount) return false;
    if ((mount.textContent || "").includes("Não foi possível carregar todas as candidaturas")) return true;
    return mount.querySelectorAll(".compare-person").length === count;
  }, expected);
  const failed = await page.locator("#compareMount").innerText();
  assert.ok(!failed.includes("Não foi possível carregar todas as candidaturas"), "compare:LOAD_ERROR");
}
async function waitForCompareEmpty(page) {
  await page.waitForFunction(() => {
    const mount = document.querySelector("#compareMount");
    if (!mount) return false;
    if ((mount.textContent || "").includes("Não foi possível carregar todas as candidaturas")) return true;
    return Boolean(mount.querySelector(".compare-empty"));
  });
  const failed = await page.locator("#compareMount").innerText();
  assert.ok(!failed.includes("Não foi possível carregar todas as candidaturas"), "compare:LOAD_ERROR");
}

async function runUi(browser) {
  const suite = { status: "BLOCKED", scenarios: [] };
  manifest.suites.ui = suite;
  let context;
  try {
    context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    await context.route(/googletagmanager\.com|google-analytics\.com/, route => route.abort());
    await context.addInitScript(() => localStorage.removeItem("qv_compare"));
    const page = await context.newPage();
    await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
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

    await check("cross-tab-storage-sync", async () => {
      await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
      await page.waitForSelector(`[data-compare-id="${ids[0]}"]`);
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
      suite.desktop_screenshot = await screenshot(page, "desktop-final.png");
    } catch (error) {
      suite.desktop_screenshot_error = errText(error);
    }
    await context.close();
    context = null;

    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    try {
      await mobile.route(/googletagmanager\.com|google-analytics\.com/, route => route.abort());
      await mobile.addInitScript(() => localStorage.removeItem("qv_compare"));
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

async function runNetwork(browser) {
  const suite = { status: "BLOCKED", policy: NETWORK_POLICY, scenarios: [] };
  manifest.suites.network = suite;
  const hits = [];
  let context;
  try {
    context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    context.on("request", request => {
      if (/google-analytics\.com\/.*collect/i.test(request.url())) {
        hits.push({ url: request.url(), postData: request.postData(), method: request.method() });
      }
    });
    await context.route(/google-analytics\.com\/.*collect/i, route => route.abort());
    const page = await context.newPage();

    const strict = NETWORK_POLICY === "ga4-privacy-strict";
    const evaluate = (name, scope, markers, extraCheck) => {
      if (!scope.length) {
        record(suite, name, "INCONCLUSIVE", { reason: "NO_COLLECT" });
        return;
      }
      const found = markerHits(scope, markers);
      if (found.length) {
        record(suite, name, "FAIL", { reason: "FORBIDDEN_VALUE", markers: found, events: scope.map(eventName) });
        return;
      }
      if (extraCheck) {
        const violation = extraCheck(scope);
        if (violation) {
          record(suite, name, "FAIL", { reason: violation, events: scope.map(eventName) });
          return;
        }
      }
      if (strict) {
        const events = [...new Set(scope.map(eventName))];
        if (events.some(event => event !== "page_view")) {
          record(suite, name, "FAIL", { reason: "ENHANCED_OR_AUTOMATIC_EVENT", events });
          return;
        }
      }
      record(suite, name, "PASS", { collect: scope.length, events: scope.map(eventName) });
    };

    const scenario = async (name, route, markers, action, extraCheck) => {
      const start = hits.length;
      try {
        await page.goto(BASE + route, { waitUntil: "domcontentloaded" });
        if (action) await action(page);
        await settle(page);
        evaluate(name, hits.slice(start), markers, extraCheck);
      } catch (error) {
        record(suite, name, "BLOCKED", { error: errText(error) });
      }
    };

    const candidateMarkers = ["SENTINEL_ID_91357", "SENTINEL_TEMA_24680", "SENTINEL_HASH_13579"];
    await scenario("candidate-initial", "candidato.html?id=SENTINEL_ID_91357&tema=SENTINEL_TEMA_24680#SENTINEL_HASH_13579", candidateMarkers);

    {
      const start = hits.length;
      try {
        await page.reload({ waitUntil: "domcontentloaded" });
        await settle(page);
        evaluate("candidate-reload", hits.slice(start), candidateMarkers);
      } catch (error) {
        record(suite, "candidate-reload", "BLOCKED", { error: errText(error) });
      }
    }

    await scenario(
      "listing-query",
      "candidatos.html?cargo=federal&q=SENTINEL_Q_86420&partido=SENTINEL_PARTY_97531&tema=SENTINEL_TOPIC_11223",
      ["SENTINEL_Q_86420", "SENTINEL_PARTY_97531", "SENTINEL_TOPIC_11223"]
    );

    await scenario(
      "compare-ids",
      "comparar.html?ids=SENTINEL_A_31415,SENTINEL_B_92653",
      ["SENTINEL_A_31415", "SENTINEL_B_92653"]
    );

    {
      const start = hits.length;
      try {
        await page.goto(BASE + "candidatos.html?cargo=federal&q=SENTINEL_HISTORY_44556", { waitUntil: "domcontentloaded" });
        await settle(page);
        const before = hits.slice(start).filter(hit => eventName(hit) === "page_view").length;
        await page.evaluate(() => history.pushState({}, "", "?cargo=federal&q=SENTINEL_PUSH_77889"));
        await settle(page);
        await page.goBack();
        await settle(page);
        await page.goForward();
        await settle(page);
        evaluate(
          "history",
          hits.slice(start),
          ["SENTINEL_HISTORY_44556", "SENTINEL_PUSH_77889"],
          scope => scope.filter(hit => eventName(hit) === "page_view").length !== before ? "AUTOMATIC_PAGE_VIEW" : null
        );
      } catch (error) {
        record(suite, "history", "BLOCKED", { error: errText(error) });
      }
    }

    {
      const start = hits.length;
      try {
        const federal = JSON.parse(fs.readFileSync(path.join(TARGET_DIR, "data/generated/candidates-federal.json"), "utf8"));
        const candidate = federal[0];
        const candidateId = String(candidate.tse_id);
        const candidateName = String(candidate.ballot_name || candidate.full_name);
        await page.goto(BASE + "candidato.html?id=" + encodeURIComponent(candidateId), { waitUntil: "domcontentloaded" });
        await page.waitForFunction(name => document.title.includes(name), candidateName);
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await settle(page);
        const outbound = page.locator('.source-item a[target="_blank"]').first();
        if (!await outbound.count()) {
          record(suite, "dynamic-auto-events", "INCONCLUSIVE", { reason: "OUTBOUND_LINK_NOT_AVAILABLE" });
        } else {
          const outboundUrl = await outbound.getAttribute("href") || "";
          await context.route(outboundUrl, route => route.abort()).catch(() => {});
          const popup = context.waitForEvent("page", { timeout: 5000 }).catch(() => null);
          await outbound.click();
          const opened = await popup;
          await settle(page);
          if (opened) await opened.close();
          evaluate("dynamic-auto-events", hits.slice(start), [candidateId, candidateName, outboundUrl]);
        }
      } catch (error) {
        record(suite, "dynamic-auto-events", "BLOCKED", { error: errText(error) });
      }
    }

    fs.writeFileSync(path.join(OUT, "network-summary.json"), JSON.stringify({
      semantics: "Sanitized GA4 request metadata. Raw request values are not persisted.",
      requests: hits.map(payloadKeys)
    }, null, 2) + "\n");

    suite.observed_events = [...new Set(hits.map(eventName))].sort();
    suite.collect_requests = hits.length;
    suite.status = worst(suite.scenarios.map(item => item.status));
  } catch (error) {
    record(suite, "network-setup", "BLOCKED", { error: errText(error) });
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
  if (manifest.target.mode === "production" && manifest.target.revision_status !== "VERIFIED_DEPLOYED") {
    manifest.suites.provenance = {
      status: "BLOCKED",
      scenarios: [{
        name: "production-served-revision",
        status: "BLOCKED",
        reason: "SERVED_REVISION_UNVERIFIED"
      }]
    };
  }
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
    if (SUITE === "ui" || SUITE === "all") await runUi(browser);
    if (SUITE === "network" || SUITE === "all") await runNetwork(browser);
    if (!["ui", "network", "all"].includes(SUITE)) {
      manifest.suites.harness = { status: "BLOCKED", scenarios: [{ name: "suite-selection", status: "BLOCKED", error: `Unknown suite: ${SUITE}` }] };
    }
  } catch (error) {
    manifest.suites.harness = { status: "BLOCKED", scenarios: [{ name: "browser-launch", status: "BLOCKED", error: errText(error) }] };
  } finally {
    if (browser) await browser.close().catch(() => {});
    writeManifest();
  }
})();
