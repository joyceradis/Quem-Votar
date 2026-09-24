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

function combineErrors(primary, secondary, message) {
  if (!primary) return secondary;
  return new AggregateError(
    [primary, secondary],
    `${message}: ${errText(primary)} | ${errText(secondary)}`
  );
}

function record(suite, name, status, details = {}) {
  suite.scenarios.push({ name, status, ...details });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function trackPendingTask(pending, task) {
  const tracked = Promise.resolve(task);
  pending.add(tracked);
  tracked.then(
    () => pending.delete(tracked),
    () => pending.delete(tracked)
  );
  tracked.catch(() => {});
  return tracked;
}

async function drainPendingTasks(pending, timeoutMs = 2500) {
  const tasks = [...pending];
  if (!tasks.length) return;

  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error("teardown:PENDING_ROUTE_TIMEOUT")), timeoutMs);
  });

  let settled;
  try {
    settled = await Promise.race([Promise.allSettled(tasks), timeout]);
  } finally {
    clearTimeout(timer);
  }

  const rejected = settled.filter(item => item.status === "rejected");
  if (rejected.length) {
    throw new AggregateError(
      rejected.map(item => item.reason),
      "teardown:PENDING_ROUTE_REJECTED"
    );
  }
}

async function withDelayedCandidateRoutes(page, delayMs, fn) {
  const pattern = /data\/generated\/candidates-(federal|estadual)\.json/;
  const pending = new Set();
  const handler = route => trackPendingTask(pending, (async () => {
    await sleep(delayMs);
    await route.fallback();
  })());

  await page.route(pattern, handler);

  let result;
  let primaryError = null;
  try {
    result = await fn();
  } catch (error) {
    primaryError = error;
  } finally {
    const errors = [];
    if (primaryError) errors.push(primaryError);

    try {
      await page.unroute(pattern, handler);
    } catch (error) {
      errors.push(error);
    }

    try {
      await drainPendingTasks(pending);
    } catch (error) {
      errors.push(error);
    }

    if (errors.length === 1) throw errors[0];
    if (errors.length > 1) {
      throw new AggregateError(errors, "compare:DELAYED_ROUTE_CLEANUP");
    }
  }

  return result;
}

async function screenshot(page, filename) {
  const destination = path.join(SCREENSHOTS, filename);
  await page.screenshot({ path: destination, fullPage: false });
  return path.relative(OUT, destination);
}

async function waitForViewportIntersection(page, selector, label, timeoutMs = 2000) {
  try {
    await page.waitForFunction(
      targetSelector => {
        const node = document.querySelector(targetSelector);
        if (!node) return false;
        const rect = node.getBoundingClientRect();
        return rect.bottom > 0 && rect.top < window.innerHeight;
      },
      selector,
      { timeout: timeoutMs }
    );
  } catch (error) {
    throw new Error(label + ": " + errText(error));
  }
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

function sanitizedLocation(location = {}) {
  if (!location.url) return null;
  try {
    const url = new URL(location.url);
    return `${url.protocol}//${url.host}${url.pathname}`;
  } catch {
    return "unparseable-location";
  }
}

function installRuntimeErrorProbe(page, errors) {
  page.on("pageerror", error => {
    errors.material.push({ type: "pageerror", text: errText(error) });
  });
  page.on("console", message => {
    if (message.type() !== "error") return;
    const location = message.location();
    const text = message.text();
    let external = false;
    try {
      external = Boolean(location.url) && !isLoopbackHost(new URL(location.url).hostname);
    } catch {}
    const detail = { type: "console", text, location: sanitizedLocation(location) };
    if (external && text.startsWith("Failed to load resource:")) {
      errors.expected_firewall.push(detail);
      return;
    }
    errors.material.push(detail);
  });
}

async function exerciseLifecycleAndClose(page, events) {
  assert.ok(page, "teardown:PAGE_NOT_CREATED");
  assert.ok(!page.isClosed(), "teardown:PAGE_ALREADY_CLOSED");
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

async function loadProfileFixtures(page) {
  await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
  return page.evaluate(async () => {
    const load = async path => {
      const response = await fetch(path + "?runtime-proof=1", { cache: "no-store" });
      if (!response.ok) throw new Error(`fixture load failed: ${path} (${response.status})`);
      return response.json();
    };
    const [federal, estadual] = await Promise.all([
      load("data/generated/candidates-federal.json"),
      load("data/generated/candidates-estadual.json")
    ]);
    const all = [
      ...federal.map(candidate => ({ ...candidate, kind: "federal" })),
      ...estadual.map(candidate => ({ ...candidate, kind: "estadual" }))
    ];
    const occupationOnly = all.find(candidate =>
      candidate.occupation &&
      !candidate.current_mandate &&
      !(candidate.institutional_evidence || []).length
    );
    const currentMandate = all.find(candidate => candidate.current_mandate && candidate.occupation);
    if (!occupationOnly) throw new Error("fixture:OCCUPATION_WITHOUT_CURRENT_MANDATE_NOT_FOUND");
    if (!currentMandate) throw new Error("fixture:CURRENT_MANDATE_NOT_FOUND");
    const pick = candidate => ({
      id: String(candidate.tse_id),
      kind: candidate.kind,
      occupation: candidate.occupation,
      expectedActivity: candidate.current_mandate
        ? candidate.kind === "federal" ? "Deputado federal em exercício" : "Mandato atual confirmado"
        : null
    });
    return { occupationOnly: pick(occupationOnly), currentMandate: pick(currentMandate) };
  });
}

async function openProfile(page, fixture) {
  await page.goto(
    BASE + "candidato.html?id=" + encodeURIComponent(fixture.id) + "&cargo=" + fixture.kind,
    { waitUntil: "domcontentloaded" }
  );
  await page.waitForFunction(() => {
    const mount = document.querySelector("#profileMount");
    return mount && !mount.classList.contains("loading") && Boolean(mount.querySelector("#profileCompare"));
  });
}

async function tabTo(page, selector, limit = 30) {
  for (let index = 0; index < limit; index += 1) {
    await page.keyboard.press("Tab");
    if (await page.evaluate(value => document.activeElement?.matches(value), selector)) return;
  }
  assert.fail(`a11y:TAB_TARGET_NOT_REACHED ${selector}`);
}

async function runScenario(browser, suite, name, fn, contextOptions = { viewport: { width: 1366, height: 900 } }) {
  let context;
  let page;
  let error = null;
  const lifecycle = [];
  const runtimeErrors = { material: [], expected_firewall: [] };

  try {
    context = await browser.newContext({ ...contextOptions, serviceWorkers: "block" });
    await installLocalOnlyFirewall(context);
    page = await context.newPage();
    await installLifecycleProbe(page, lifecycle);
    installRuntimeErrorProbe(page, runtimeErrors);
    await fn({ context, page });
    await page.waitForTimeout(25);
  } catch (caught) {
    error = caught;
  } finally {
    try {
      await exerciseLifecycleAndClose(page, lifecycle);
    } catch (teardownError) {
      error = combineErrors(error, teardownError, "scenario:PAGE_TEARDOWN_FAILED");
    }

    if (context) {
      try {
        await context.close();
      } catch (contextError) {
        error = combineErrors(error, contextError, "scenario:CONTEXT_TEARDOWN_FAILED");
      }
    }
  }

  if (runtimeErrors.material.length) {
    error = combineErrors(
      error,
      new Error("runtime:MATERIAL_JAVASCRIPT_ERROR"),
      "scenario:FUNCTIONAL_OR_TEARDOWN_AND_RUNTIME_ERRORS"
    );
  }

  if (error) {
    record(suite, name, "FAIL", {
      error: errText(error),
      lifecycle: [...new Set(lifecycle)],
      runtime_errors: runtimeErrors
    });
  } else {
    record(suite, name, "PASS", {
      lifecycle: [...new Set(lifecycle)],
      runtime_errors: runtimeErrors
    });
  }
}

async function runHarnessInvariantChecks() {
  const suite = { status: "BLOCKED", scenarios: [] };
  manifest.suites.harness_invariants = suite;

  try {
    await assert.rejects(
      () => exerciseLifecycleAndClose({ isClosed: () => true }, []),
      /teardown:PAGE_ALREADY_CLOSED/
    );
    record(suite, "teardown-rejects-preclosed-page", "PASS");
  } catch (error) {
    record(suite, "teardown-rejects-preclosed-page", "FAIL", { error: errText(error) });
  }

  try {
    const pending = new Set();
    let completed = false;
    trackPendingTask(pending, new Promise(resolve => {
      setTimeout(() => {
        completed = true;
        resolve();
      }, 30);
    }));
    await drainPendingTasks(pending, 500);
    assert.equal(completed, true, "teardown:PENDING_ROUTE_NOT_DRAINED");
    assert.equal(pending.size, 0, "teardown:PENDING_ROUTE_SET_NOT_EMPTY");
    record(suite, "pending-route-drain-waits", "PASS");
  } catch (error) {
    record(suite, "pending-route-drain-waits", "FAIL", { error: errText(error) });
  }

  try {
    const pending = new Set();
    trackPendingTask(pending, new Promise((_, reject) => {
      setTimeout(() => reject(new Error("synthetic-route-failure")), 10);
    }));
    await assert.rejects(
      () => drainPendingTasks(pending, 500),
      /teardown:PENDING_ROUTE_REJECTED/
    );
    record(suite, "pending-route-rejection-propagates", "PASS");
  } catch (error) {
    record(suite, "pending-route-rejection-propagates", "FAIL", { error: errText(error) });
  }

  suite.status = worst(suite.scenarios.map(item => item.status));
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
    await Promise.all([
      page.waitForURL(/\/comparar\.html\?ids=/),
      page.locator("#openCompare").click()
    ]);
    await waitForComparePeople(page, 2);
    assert.equal(await page.locator(".compare-person").count(), 2);
    assert.equal(new URL(await page.url()).searchParams.get("ids"), ids.slice(0, 2).join(","));
    const renderedIds = await page.locator(".compare-person a").evaluateAll(nodes =>
      nodes.map(node => new URL(node.href).searchParams.get("id"))
    );
    assert.deepEqual(renderedIds, ids.slice(0, 2));
  });

  await runScenario(browser, suite, "profile-three-questions-anchors-keyboard", async ({ page }) => {
    const { occupationOnly } = await loadProfileFixtures(page);
    await openProfile(page, occupationOnly);

    const sections = await page.locator("#faz-hoje, #vai-fazer, #impacto").evaluateAll(nodes =>
      nodes.map(node => ({ id: node.id, title: node.querySelector("h2")?.textContent?.trim() }))
    );
    assert.deepEqual(sections, [
      { id: "faz-hoje", title: "O que essa pessoa faz hoje?" },
      { id: "vai-fazer", title: "O que ela diz que vai fazer?" },
      { id: "impacto", title: "Onde isso pode mexer na vida real?" }
    ]);

    await page.locator("body").click({ position: { x: 1, y: 1 } });
    await tabTo(page, "#profileCompare");
    await page.keyboard.press("Enter");
    assert.equal(await page.locator("#profileCompare").getAttribute("aria-pressed"), "true");
    await tabTo(page, "#profileShare");
    await tabTo(page, '.profile-jump a[href="#faz-hoje"]');
    assert.equal(await page.evaluate(() => document.activeElement?.matches('.profile-jump a[href="#faz-hoje"]')), true);
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => location.hash === "#faz-hoje");

    const anchors = ["faz-hoje", "vai-fazer", "impacto", "historico", "dados-eleitorais", "fontes"];
    for (const id of anchors) {
      const link = page.locator(`.profile-jump a[href="#${id}"]`);
      assert.equal(await link.count(), 1, `profile:ANCHOR_LINK_${id}`);
      assert.equal(await page.locator(`#${id}`).count(), 1, `profile:ANCHOR_TARGET_${id}`);
      await link.click();
      await page.waitForFunction(hash => location.hash === hash, `#${id}`);
      await waitForViewportIntersection(page, `#${id}`, `profile:ANCHOR_NOT_VISIBLE_${id}`);
    }
    suite.profile_desktop_screenshot = await screenshot(page, "profile-desktop-1366x900.png");
  });

  await runScenario(browser, suite, "profile-occupation-is-not-current-activity", async ({ page }) => {
    const { occupationOnly } = await loadProfileFixtures(page);
    await openProfile(page, occupationOnly);
    const electoral = page.locator("#dados-eleitorais");
    assert.match(await electoral.innerText(), /Ocupação declarada/i);
    assert.ok((await electoral.innerText()).includes(occupationOnly.occupation));
    assert.ok(!(await page.locator("#faz-hoje").innerText()).includes(occupationOnly.occupation));
  });

  await runScenario(browser, suite, "profile-current-mandate-is-current-activity", async ({ page }) => {
    const { currentMandate } = await loadProfileFixtures(page);
    await openProfile(page, currentMandate);
    const current = await page.locator("#faz-hoje").innerText();
    assert.ok(current.includes(currentMandate.expectedActivity));
    assert.ok(!current.includes(currentMandate.occupation));
  });

  await runScenario(browser, suite, "profile-web-share", async ({ context, page }) => {
    await context.addInitScript(() => {
      globalThis.__qvShareCalls = [];
      Object.defineProperty(navigator, "share", {
        configurable: true,
        value: async payload => { globalThis.__qvShareCalls.push(payload); }
      });
    });
    const ids = await loadCandidateIds(page);
    await openProfile(page, { id: ids[0], kind: "federal" });
    await page.locator("#profileShare").focus();
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => globalThis.__qvShareCalls?.length === 1);
    const calls = await page.evaluate(() => globalThis.__qvShareCalls);
    assert.equal(calls.length, 1);
    assert.equal(typeof calls[0].title, "string");
    assert.equal(typeof calls[0].text, "string");
    const shared = new URL(calls[0].url);
    assert.equal(shared.origin, new URL(BASE).origin);
    assert.equal(shared.pathname, new URL(`social/${encodeURIComponent(ids[0])}/`, BASE).pathname);
  });

  await runScenario(browser, suite, "profile-clipboard-fallback", async ({ context, page }) => {
    await context.addInitScript(() => {
      globalThis.__qvClipboardWrites = [];
      Object.defineProperty(navigator, "share", { configurable: true, value: undefined });
      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: { writeText: async value => { globalThis.__qvClipboardWrites.push(value); } }
      });
    });
    const ids = await loadCandidateIds(page);
    await openProfile(page, { id: ids[0], kind: "federal" });
    await page.locator("#profileShare").focus();
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => globalThis.__qvClipboardWrites?.length === 1);
    const writes = await page.evaluate(() => globalThis.__qvClipboardWrites);
    assert.deepEqual(writes, [new URL(`social/${encodeURIComponent(ids[0])}/`, BASE).toString()]);
    assert.equal(await page.locator("#profileShare").innerText(), "Link copiado");
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

    await withDelayedCandidateRoutes(page, 700, async () => {
      const started = Date.now();
      await page.goto(BASE + "comparar.html?ids=" + encodeURIComponent(ids[0] + "," + ids[2]), { waitUntil: "domcontentloaded" });
      await waitForComparePeople(page, 2);
      assert.ok(Date.now() - started >= 500, "compare:ASYNC_WAIT_NOT_EXERCISED");
    });
  });

  await runScenario(browser, suite, "delayed-route-preserves-local-firewall", async ({ page }) => {
    await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });

    await withDelayedCandidateRoutes(page, 25, async () => {
      const failedRequest = page.waitForEvent("requestfailed", request =>
        request.url().startsWith("https://example.invalid/data/generated/candidates-federal.json")
      );
      const outcome = await page.evaluate(async () => {
        try {
          await fetch("https://example.invalid/data/generated/candidates-federal.json");
          return "resolved";
        } catch {
          return "rejected";
        }
      });
      assert.equal(outcome, "rejected", "scope:EXTERNAL_DELAYED_ROUTE_NOT_BLOCKED");
      const request = await failedRequest;
      assert.match(request.url(), /^https:\/\/example\.invalid\//);
    });
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

  await runScenario(
    browser,
    suite,
    "profile-mobile-390x844",
    async ({ page }) => {
      const { occupationOnly } = await loadProfileFixtures(page);
      await openProfile(page, occupationOnly);
      assert.equal(await page.locator("#faz-hoje, #vai-fazer, #impacto").count(), 3, "profile:MOBILE_PRIMARY_SECTIONS");
      assert.equal(await page.locator("#profileCompare").isVisible(), true, "profile:MOBILE_COMPARE_NOT_VISIBLE");
      assert.equal(await page.locator("#profileShare").isVisible(), true, "profile:MOBILE_SHARE_NOT_VISIBLE");
      const impactLink = page.locator('.profile-jump a[href="#impacto"]');
      assert.equal(await impactLink.count(), 1, "profile:MOBILE_IMPACT_LINK_MISSING");
      await impactLink.tap();
      await page.waitForFunction(() => location.hash === "#impacto");
      await waitForViewportIntersection(page, "#impacto", "profile:MOBILE_IMPACT_NOT_VISIBLE");
      const layout = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        delta: document.documentElement.scrollWidth - document.documentElement.clientWidth
      }));
      suite.profile_mobile_layout = layout;
      assert.ok(layout.delta <= 1, "profile:HORIZONTAL_OVERFLOW " + JSON.stringify(layout));
      suite.profile_mobile_screenshot = await screenshot(page, "profile-mobile-390x844.png");
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
    await runHarnessInvariantChecks();
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
