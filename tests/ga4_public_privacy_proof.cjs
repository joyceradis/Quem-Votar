const { chromium } = require("@playwright/test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const BASE = new URL(process.env.QV_BASE_URL || "https://joyceradis.github.io/Quem-Votar/");
const EXPECTED_MAIN_SHA = process.env.QV_EXPECTED_MAIN_SHA || "";
const OUT = process.env.QV_PROOF_OUT || "ga4-public-proof.json";

const results = [];
let candidateFixture = null;

function decodeDeep(value) {
  let out = String(value || "");
  for (let i = 0; i < 4; i += 1) {
    try {
      const next = decodeURIComponent(out.replace(/\+/g, "%20"));
      if (next === out) break;
      out = next;
    } catch {
      break;
    }
  }
  return out;
}

function isCollect(urlString) {
  try {
    const url = new URL(urlString);
    return /(^|\.)google-analytics\.com$/i.test(url.hostname) && /\/collect(?:$|[/?])/i.test(url.pathname);
  } catch {
    return false;
  }
}

function rawPayload(hit) {
  return decodeDeep(hit.url + "\n" + (hit.postData || ""));
}

function paramsFor(hit) {
  const out = new Map();
  const url = new URL(hit.url);
  for (const [key, value] of url.searchParams) out.set(key, decodeDeep(value));
  if (hit.postData) {
    for (const line of String(hit.postData).split(/\r?\n/)) {
      for (const [key, value] of new URLSearchParams(line)) {
        if (!out.has(key)) out.set(key, decodeDeep(value));
      }
    }
  }
  return out;
}

function eventName(hit) {
  return paramsFor(hit).get("en") || "unknown";
}

function safeHitSummary(hit) {
  const p = paramsFor(hit);
  return {
    event: eventName(hit),
    page_location: p.get("dl") || null,
    page_referrer: p.get("dr") || null,
    page_title: p.get("dt") || null,
    link_url: p.get("ep.link_url") || p.get("link_url") || null,
    outbound: p.get("ep.outbound") || p.get("outbound") || null,
    payload_sha256: crypto.createHash("sha256").update(hit.url + "\n" + (hit.postData || "")).digest("hex"),
  };
}

function assertAbsent(hits, markers, label) {
  const all = hits.map(rawPayload).join("\n").toLocaleLowerCase("pt-BR");
  for (const marker of markers.filter(Boolean)) {
    assert.ok(
      !all.includes(String(marker).toLocaleLowerCase("pt-BR")),
      label + ":FORBIDDEN_VALUE:" + marker
    );
  }
}

function assertCanonical(hits, expectedLocation, expectedTitle, label) {
  for (const hit of hits) {
    const p = paramsFor(hit);
    const dl = p.get("dl");
    const dt = p.get("dt");
    if (dl) assert.equal(dl, expectedLocation, label + ":DIRTY_PAGE_LOCATION:" + dl);
    if (dt) assert.equal(dt, expectedTitle, label + ":DIRTY_PAGE_TITLE:" + dt);
    const dr = p.get("dr");
    if (dr) {
      const ref = new URL(dr);
      assert.equal(ref.origin, BASE.origin, label + ":EXTERNAL_REFERRER");
      assert.ok(ref.pathname.startsWith(BASE.pathname), label + ":OUT_OF_SCOPE_REFERRER");
      assert.equal(ref.search, "", label + ":REFERRER_QUERY");
      assert.equal(ref.hash, "", label + ":REFERRER_HASH");
    }
  }
}

async function waitForQuiescence(hits, { minHits = 1, quietMs = 1200, maxMs = 9000 } = {}) {
  const started = Date.now();
  let lastCount = hits.length;
  let stableSince = Date.now();
  while (Date.now() - started < maxMs) {
    await new Promise(resolve => setTimeout(resolve, 150));
    if (hits.length !== lastCount) {
      lastCount = hits.length;
      stableSince = Date.now();
    }
    if (hits.length >= minHits && Date.now() - stableSince >= quietMs) return;
  }
  if (hits.length < minHits) throw new Error("NO_COLLECT_WITHIN_TIMEOUT");
  throw new Error("COLLECT_NOT_QUIESCENT");
}

async function newProbeContext(browser) {
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    serviceWorkers: "block",
  });
  const hits = [];
  await context.route("**/*", async route => {
    const request = route.request();
    if (isCollect(request.url())) {
      hits.push({
        url: request.url(),
        method: request.method(),
        postData: request.postData(),
        resourceType: request.resourceType(),
      });
      await route.abort("blockedbyclient");
      return;
    }
    await route.continue();
  });
  return { context, hits };
}

async function finishContext(context, page, hits) {
  if (page && !page.isClosed()) {
    await page.close({ runBeforeUnload: true }).catch(() => {});
  }
  await new Promise(resolve => setTimeout(resolve, 700));
  await context.close().catch(() => {});
  return hits;
}

async function publicFileParity() {
  const local = fs.readFileSync(path.join(process.cwd(), "telemetry.js"), "utf8");
  const url = new URL("telemetry.js", BASE);
  url.searchParams.set("privacy-proof", Date.now().toString());
  const response = await fetch(url, { headers: { "cache-control": "no-cache" } });
  assert.equal(response.status, 200, "PUBLIC_TELEMETRY_HTTP_" + response.status);
  const served = await response.text();
  assert.equal(
    crypto.createHash("sha256").update(served).digest("hex"),
    crypto.createHash("sha256").update(local).digest("hex"),
    "PUBLIC_TELEMETRY_DOES_NOT_MATCH_CHECKOUT"
  );
  results.push({
    name: "served-telemetry-parity",
    status: "PASS",
    expected_main_sha: EXPECTED_MAIN_SHA,
    sha256: crypto.createHash("sha256").update(served).digest("hex"),
  });
}

async function fetchCandidateFixture() {
  const response = await fetch(new URL("data/generated/candidates-federal.json?privacy-proof=1", BASE));
  assert.equal(response.status, 200, "CANDIDATE_FIXTURE_HTTP_" + response.status);
  const data = await response.json();
  assert.ok(Array.isArray(data) && data.length, "NO_CANDIDATE_FIXTURE");
  const candidate = data[0];
  candidateFixture = {
    id: String(candidate.tse_id),
    name: String(candidate.ballot_name || candidate.full_name),
  };
}

async function trackedScenario(browser, spec) {
  const { context, hits } = await newProbeContext(browser);
  const page = await context.newPage();
  let error = null;
  let note = null;
  try {
    await page.goto(new URL(spec.path, BASE).toString(), { waitUntil: "domcontentloaded", timeout: 30000 });
    if (spec.action) await spec.action(page, hits);
    await waitForQuiescence(hits, { minHits: spec.minHits ?? 1 });
  } catch (caught) {
    error = caught;
  }
  await finishContext(context, page, hits);

  try {
    if (error) throw error;
    assertAbsent(hits, spec.markers || [], spec.name);
    if (spec.expectedLocation) {
      assertCanonical(hits, spec.expectedLocation, spec.expectedTitle, spec.name);
    }
    const pageViews = hits.filter(hit => eventName(hit) === "page_view");
    if (spec.expectOnePageView !== false) {
      assert.equal(pageViews.length, 1, spec.name + ":PAGE_VIEW_COUNT=" + pageViews.length);
    }
    if (spec.extraAssert) await spec.extraAssert(hits);
    results.push({
      name: spec.name,
      status: "PASS",
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
      note,
    });
  } catch (caught) {
    results.push({
      name: spec.name,
      status: "FAIL",
      error: String(caught && (caught.message || caught)),
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
    });
  }
}

async function noTelemetryScenario(browser, spec) {
  const { context, hits } = await newProbeContext(browser);
  const page = await context.newPage();
  let navStatus = null;
  let error = null;
  try {
    const response = await page.goto(new URL(spec.path, BASE).toString(), { waitUntil: "domcontentloaded", timeout: 30000 });
    navStatus = response ? response.status() : null;
    await new Promise(resolve => setTimeout(resolve, 2500));
  } catch (caught) {
    error = caught;
  }
  await finishContext(context, page, hits);
  try {
    if (error) throw error;
    assertAbsent(hits, spec.markers || [], spec.name);
    if (hits.length) {
      assertCanonical(hits, BASE.toString(), "Quem Votar? · Espírito Santo 2026", spec.name);
    }
    results.push({
      name: spec.name,
      status: "PASS",
      navigation_status: navStatus,
      collect_count: hits.length,
      events: hits.map(eventName),
      interpretation: hits.length ? "telemetry-failed-closed-to-root" : "no-ga4-on-route",
      hits: hits.map(safeHitSummary),
    });
  } catch (caught) {
    results.push({
      name: spec.name,
      status: "FAIL",
      error: String(caught && (caught.message || caught)),
      navigation_status: navStatus,
      collect_count: hits.length,
      hits: hits.map(safeHitSummary),
    });
  }
}

async function historyScenario(browser) {
  const name = "history-back-forward";
  const markers = ["QVPRIVACY_HISTORY_44556", "QVPRIVACY_PUSH_77889"];
  const { context, hits } = await newProbeContext(browser);
  const page = await context.newPage();
  let error = null;
  try {
    await page.goto(
      new URL("candidatos.html?cargo=federal&q=" + markers[0], BASE).toString(),
      { waitUntil: "domcontentloaded", timeout: 30000 }
    );
    await waitForQuiescence(hits);
    const before = hits.filter(hit => eventName(hit) === "page_view").length;
    await page.evaluate(marker => history.pushState({}, "", "?cargo=federal&q=" + marker), markers[1]);
    await new Promise(resolve => setTimeout(resolve, 1200));
    await page.goBack({ waitUntil: "domcontentloaded" }).catch(() => {});
    await new Promise(resolve => setTimeout(resolve, 1200));
    await page.goForward({ waitUntil: "domcontentloaded" }).catch(() => {});
    await new Promise(resolve => setTimeout(resolve, 1500));
    const after = hits.filter(hit => eventName(hit) === "page_view").length;
    assert.equal(after, before, name + ":AUTOMATIC_HISTORY_PAGE_VIEW");
  } catch (caught) {
    error = caught;
  }
  await finishContext(context, page, hits);

  try {
    if (error) throw error;
    assertAbsent(hits, markers, name);
    assertCanonical(
      hits,
      new URL("candidatos.html", BASE).toString(),
      "Candidaturas · Quem Votar?",
      name
    );
    results.push({
      name,
      status: "PASS",
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
    });
  } catch (caught) {
    results.push({
      name,
      status: "FAIL",
      error: String(caught && (caught.message || caught)),
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
    });
  }
}

async function reloadScenario(browser) {
  const name = "candidate-reload";
  const markers = ["QVPRIVACY_RELOAD_ID_91357", "QVPRIVACY_RELOAD_HASH_13579"];
  const { context, hits } = await newProbeContext(browser);
  const page = await context.newPage();
  let error = null;
  try {
    const url = new URL("candidato.html?id=" + markers[0] + "#" + markers[1], BASE).toString();
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await waitForQuiescence(hits);
    const before = hits.length;
    await page.reload({ waitUntil: "domcontentloaded", timeout: 30000 });
    await waitForQuiescence(hits, { minHits: before + 1 });
    const reloadHits = hits.slice(before);
    assertAbsent(reloadHits, markers, name);
    assertCanonical(
      reloadHits,
      new URL("candidato.html", BASE).toString(),
      "Entenda esta candidatura · Quem Votar?",
      name
    );
    assert.equal(
      reloadHits.filter(hit => eventName(hit) === "page_view").length,
      1,
      name + ":PAGE_VIEW_COUNT"
    );
  } catch (caught) {
    error = caught;
  }
  await finishContext(context, page, hits);

  if (error) {
    results.push({
      name,
      status: "FAIL",
      error: String(error && (error.message || error)),
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
    });
  } else {
    results.push({
      name,
      status: "PASS",
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
    });
  }
}

async function dynamicCandidateScenario(browser) {
  const name = "dynamic-title-scroll-actual-outbound";
  const { context, hits } = await newProbeContext(browser);
  const page = await context.newPage();
  let outboundUrl = "";
  let error = null;
  try {
    await page.goto(
      new URL("candidato.html?id=" + encodeURIComponent(candidateFixture.id) + "&cargo=federal", BASE).toString(),
      { waitUntil: "domcontentloaded", timeout: 30000 }
    );
    await page.waitForFunction(
      expected => document.title.includes(expected),
      candidateFixture.name,
      { timeout: 10000 }
    );
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await new Promise(resolve => setTimeout(resolve, 1800));

    const outbound = page.locator('#fontes a[href^="http"], .source-item a[href^="http"]').first();
    if (await outbound.count()) {
      outboundUrl = await outbound.getAttribute("href") || "";
      await outbound.evaluate(el => el.addEventListener("click", event => event.preventDefault(), { once: true }));
      await outbound.click();
    }
    await waitForQuiescence(hits);
  } catch (caught) {
    error = caught;
  }
  await finishContext(context, page, hits);

  try {
    if (error) throw error;
    assertAbsent(hits, [candidateFixture.id, candidateFixture.name], name);
    assertCanonical(
      hits,
      new URL("candidato.html", BASE).toString(),
      "Entenda esta candidatura · Quem Votar?",
      name
    );

    const clickHits = hits.filter(hit => eventName(hit) === "click");
    if (outboundUrl && clickHits.length) {
      const rawClicks = clickHits.map(rawPayload).join("\n");
      if (rawClicks.includes(outboundUrl)) {
        throw new Error(name + ":ACTUAL_OUTBOUND_URL_TRANSMITTED");
      }
    }

    results.push({
      name,
      status: "PASS",
      candidate_identity_absent: true,
      outbound_link_present: Boolean(outboundUrl),
      outbound_click_events: clickHits.length,
      outbound_url_sha256: outboundUrl ? crypto.createHash("sha256").update(outboundUrl).digest("hex") : null,
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
    });
  } catch (caught) {
    results.push({
      name,
      status: "FAIL",
      error: String(caught && (caught.message || caught)),
      outbound_link_present: Boolean(outboundUrl),
      outbound_url_sha256: outboundUrl ? crypto.createHash("sha256").update(outboundUrl).digest("hex") : null,
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
    });
  }
}

async function syntheticOutboundScenario(browser) {
  const name = "enhanced-measurement-outbound-sentinel";
  const markerPath = "QVPRIVACY_OUTBOUND_PATH_55123";
  const markerQuery = "QVPRIVACY_OUTBOUND_QUERY_88421";
  const { context, hits } = await newProbeContext(browser);
  const page = await context.newPage();
  let error = null;
  try {
    await page.goto(new URL("sobre.html", BASE).toString(), { waitUntil: "domcontentloaded", timeout: 30000 });
    await waitForQuiescence(hits);
    const start = hits.length;
    await page.evaluate(({ markerPath, markerQuery }) => {
      const a = document.createElement("a");
      a.id = "privacy-proof-outbound";
      a.href = "https://example.org/" + markerPath + "?probe=" + markerQuery;
      a.textContent = "privacy proof outbound";
      a.addEventListener("click", event => event.preventDefault(), { once: true });
      document.body.appendChild(a);
      a.click();
    }, { markerPath, markerQuery });
    await new Promise(resolve => setTimeout(resolve, 2200));
    const scope = hits.slice(start);
    assertAbsent(scope, [markerPath, markerQuery], name);
  } catch (caught) {
    error = caught;
  }
  await finishContext(context, page, hits);

  const clickHits = hits.filter(hit => eventName(hit) === "click");
  if (error) {
    results.push({
      name,
      status: "FAIL",
      error: String(error && (error.message || error)),
      enhanced_measurement_click_observed: clickHits.length > 0,
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
    });
  } else {
    results.push({
      name,
      status: "PASS",
      enhanced_measurement_click_observed: clickHits.length > 0,
      collect_count: hits.length,
      events: hits.map(eventName),
      hits: hits.map(safeHitSummary),
    });
  }
}

(async () => {
  const report = {
    schema: "qv-ga4-public-privacy-proof-v1",
    generated_at: new Date().toISOString(),
    base_url: BASE.toString(),
    expected_main_sha: EXPECTED_MAIN_SHA,
    overall: "BLOCKED",
    results,
  };

  let browser;
  try {
    await publicFileParity();
    await fetchCandidateFixture();
    browser = await chromium.launch({ headless: true });

    await trackedScenario(browser, {
      name: "candidate-dirty-url",
      path: "candidato.html?id=QVPRIVACY_ID_91357&q=QVPRIVACY_Q_24680&tema=QVPRIVACY_TEMA_11223&partido=QVPRIVACY_PARTIDO_97531&cargo=QVPRIVACY_CARGO_31415&page=QVPRIVACY_PAGE_92653#QVPRIVACY_HASH_13579",
      markers: ["QVPRIVACY_ID_91357","QVPRIVACY_Q_24680","QVPRIVACY_TEMA_11223","QVPRIVACY_PARTIDO_97531","QVPRIVACY_CARGO_31415","QVPRIVACY_PAGE_92653","QVPRIVACY_HASH_13579"],
      expectedLocation: new URL("candidato.html", BASE).toString(),
      expectedTitle: "Entenda esta candidatura · Quem Votar?",
    });

    await trackedScenario(browser, {
      name: "candidate-sq-edge-cases",
      path: "candidato.html?SQ_CANDIDATO=QVPRIVACY_SQ_UPPER_12345&sq_candidato=QVPRIVACY_SQ_LOWER_54321&outros_dados=ok",
      markers: ["QVPRIVACY_SQ_UPPER_12345","QVPRIVACY_SQ_LOWER_54321"],
      expectedLocation: new URL("candidato.html", BASE).toString(),
      expectedTitle: "Entenda esta candidatura · Quem Votar?",
    });

    await trackedScenario(browser, {
      name: "listing-filters",
      path: "candidatos.html?q=QVPRIVACY_SEARCH_86420&tema=QVPRIVACY_TOPIC_11223&partido=QVPRIVACY_PARTY_97531&cargo=federal&page=QVPRIVACY_PAGE_11111",
      markers: ["QVPRIVACY_SEARCH_86420","QVPRIVACY_TOPIC_11223","QVPRIVACY_PARTY_97531","QVPRIVACY_PAGE_11111"],
      expectedLocation: new URL("candidatos.html", BASE).toString(),
      expectedTitle: "Candidaturas · Quem Votar?",
    });

    await trackedScenario(browser, {
      name: "compare-ids",
      path: "comparar.html?ids=QVPRIVACY_A_31415,QVPRIVACY_B_92653",
      markers: ["QVPRIVACY_A_31415","QVPRIVACY_B_92653"],
      expectedLocation: new URL("comparar.html", BASE).toString(),
      expectedTitle: "Comparar · Quem Votar?",
    });

    await reloadScenario(browser);
    await historyScenario(browser);
    await dynamicCandidateScenario(browser);
    await syntheticOutboundScenario(browser);

    await noTelemetryScenario(browser, {
      name: "social-wrapper",
      path: "social/" + encodeURIComponent(candidateFixture.id) + "/",
      markers: [candidateFixture.id, candidateFixture.name],
    });
    await noTelemetryScenario(browser, {
      name: "unknown-route",
      path: "QVPRIVACY_UNKNOWN_77889.html?id=QVPRIVACY_UNKNOWN_ID_77889",
      markers: ["QVPRIVACY_UNKNOWN_77889","QVPRIVACY_UNKNOWN_ID_77889"],
    });

    report.overall = results.every(item => item.status === "PASS") ? "PASS" : "FAIL";
  } catch (error) {
    results.push({
      name: "harness",
      status: "BLOCKED",
      error: String(error && (error.stack || error.message || error)),
    });
    report.overall = "BLOCKED";
  } finally {
    if (browser) await browser.close().catch(() => {});
    report.results = results;
    fs.writeFileSync(OUT, JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify(report, null, 2));
  }

  if (report.overall !== "PASS") process.exit(1);
})();
