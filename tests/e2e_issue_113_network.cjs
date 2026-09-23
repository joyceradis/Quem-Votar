const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const BASE = process.env.QV_BASE_URL || "http://127.0.0.1:8000/";
const hits = [];
const results = [];

function decoded(value) {
  let out = String(value || "");
  for (let i = 0; i < 3; i += 1) {
    try { out = decodeURIComponent(out.replace(/\+/g, "%20")); } catch { break; }
  }
  return out;
}

function payload(hit) { return decoded(`${hit.url}\n${hit.postData || ""}`); }
function eventName(hit) {
  const url = new URL(hit.url);
  return url.searchParams.get("en") || new URLSearchParams(hit.postData || "").get("en") || "unknown";
}
function assertAbsent(scope, markers, code) {
  const body = scope.map(payload).join("\n").toLocaleLowerCase("pt-BR");
  for (const marker of markers.filter(Boolean)) {
    assert.ok(!body.includes(String(marker).toLocaleLowerCase("pt-BR")), code);
  }
}
async function settle(page) {
  await page.waitForTimeout(2500);
}
async function scenario(name, page, path, markers, action) {
  const start = hits.length;
  await page.goto(BASE + path, { waitUntil: "networkidle" });
  if (action) await action(page);
  await settle(page);
  const scope = hits.slice(start);
  assert.ok(scope.length > 0, `${name}:NO_COLLECT`);
  assertAbsent(scope, markers, `${name}:FORBIDDEN_VALUE`);
  results.push({ name, collect: scope.length, events: scope.map(eventName) });
  return scope;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    context.on("request", request => {
      if (/google-analytics\.com\/.*collect/i.test(request.url())) {
        hits.push({ url: request.url(), postData: request.postData() });
      }
    });
    await context.route(/google-analytics\.com\/.*collect/i, route => route.abort());
    const page = await context.newPage();

    const candidateMarkers = ["SENTINEL_ID_91357", "SENTINEL_TEMA_24680", "SENTINEL_HASH_13579"];
    await scenario("candidate-initial", page,
      "candidato.html?id=SENTINEL_ID_91357&tema=SENTINEL_TEMA_24680#SENTINEL_HASH_13579",
      candidateMarkers);
    const reloadStart = hits.length;
    await page.reload({ waitUntil: "networkidle" });
    await settle(page);
    const reloadHits = hits.slice(reloadStart);
    assert.ok(reloadHits.length > 0, "candidate-reload:NO_COLLECT");
    assertAbsent(reloadHits, candidateMarkers, "candidate-reload:FORBIDDEN_VALUE");
    results.push({ name: "candidate-reload", collect: reloadHits.length, events: reloadHits.map(eventName) });

    await scenario("listing-query", page,
      "candidatos.html?cargo=federal&q=SENTINEL_Q_86420&partido=SENTINEL_PARTY_97531&tema=SENTINEL_TOPIC_11223",
      ["SENTINEL_Q_86420", "SENTINEL_PARTY_97531", "SENTINEL_TOPIC_11223"]);
    await scenario("compare-ids", page,
      "comparar.html?ids=SENTINEL_A_31415,SENTINEL_B_92653",
      ["SENTINEL_A_31415", "SENTINEL_B_92653"]);

    const historyStart = hits.length;
    await page.goto(BASE + "candidatos.html?cargo=federal&q=SENTINEL_HISTORY_44556", { waitUntil: "networkidle" });
    await settle(page);
    const initialPageViews = hits.slice(historyStart).filter(hit => eventName(hit) === "page_view").length;
    await page.evaluate(() => history.pushState({}, "", "?cargo=federal&q=SENTINEL_PUSH_77889"));
    await settle(page);
    await page.goBack(); await settle(page);
    await page.goForward(); await settle(page);
    const historyHits = hits.slice(historyStart);
    assert.equal(historyHits.filter(hit => eventName(hit) === "page_view").length, initialPageViews,
      "history:AUTOMATIC_PAGE_VIEW");
    assertAbsent(historyHits, ["SENTINEL_HISTORY_44556", "SENTINEL_PUSH_77889"], "history:FORBIDDEN_VALUE");
    results.push({ name: "history", collect: historyHits.length, events: historyHits.map(eventName) });

    const federal = JSON.parse(fs.readFileSync("data/generated/candidates-federal.json", "utf8"));
    const candidate = federal[0];
    const candidateId = String(candidate.tse_id);
    const candidateName = String(candidate.ballot_name || candidate.full_name);
    const dynamicStart = hits.length;
    await page.goto(BASE + "candidato.html?id=" + encodeURIComponent(candidateId), { waitUntil: "networkidle" });
    await page.waitForFunction(name => document.title.includes(name), candidateName);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await settle(page);
    const outbound = page.locator('.source-item a[target="_blank"]').first();
    let outboundUrl = "";
    if (await outbound.count()) {
      outboundUrl = await outbound.getAttribute("href") || "";
      await outbound.evaluate(el => el.addEventListener("click", event => event.preventDefault(), { once: true }));
      await outbound.click();
      await settle(page);
    }
    const dynamicHits = hits.slice(dynamicStart);
    assert.ok(dynamicHits.length > 0, "dynamic:NO_COLLECT");
    assertAbsent(dynamicHits, [candidateId, candidateName], "dynamic:CANDIDATE_IDENTITY_LEAK");
    assertAbsent(dynamicHits, [outboundUrl], "dynamic:OUTBOUND_LINK_URL_LEAK");
    results.push({ name: "dynamic-auto-events", collect: dynamicHits.length, events: dynamicHits.map(eventName) });

    console.log(JSON.stringify({ head: "753c754c4f150070c4dfeb36dc99fccf828f51e3", results }, null, 2));
    await context.close();
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(String(error.message || error));
  process.exit(1);
});
