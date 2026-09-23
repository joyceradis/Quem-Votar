const { chromium } = require("playwright");
const assert = require("node:assert/strict");

const BASE = process.env.QV_BASE_URL || "http://127.0.0.1:8000/";
const results = [];
async function check(name, fn) {
  try { await fn(); results.push({ name, ok: true }); }
  catch (error) { results.push({ name, ok: false, error: String(error.message || error) }); throw error; }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    await context.route(/googletagmanager\.com|google-analytics\.com/, route => route.abort());
    await context.addInitScript(() => localStorage.removeItem("qv_compare"));
    const page = await context.newPage();
    await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("button[data-compare-id]");
    const buttons = page.locator("button[data-compare-id]");
    assert.ok(await buttons.count() >= 4);
    const ids = await buttons.evaluateAll(nodes => nodes.slice(0, 4).map(node => node.dataset.compareId));

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
      await button.focus(); await page.keyboard.press("Enter");
      assert.equal(await page.evaluate(() => document.activeElement?.dataset?.compareId), ids[1]);
      assert.equal(await page.locator(`[data-compare-id="${ids[3]}"]`).isDisabled(), false);
    });
    await check("canonical-invalid-duplicate-url", async () => {
      await page.goto(BASE + "comparar.html?ids=" + encodeURIComponent(`${ids[0]},${ids[0]},invalid,${ids[2]}`), { waitUntil: "domcontentloaded" });
      await page.waitForSelector("#compareMount:not(.loading)").catch(() => {});
      assert.equal(await page.locator(".compare-person").count(), 2);
      assert.equal(new URL(await page.url()).searchParams.get("ids"), `${ids[0]},${ids[2]}`);
      assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("qv_compare") || "[]")), [ids[0], ids[2]]);
    });
    await check("empty-ids-does-not-reuse-storage", async () => {
      await page.evaluate(values => localStorage.setItem("qv_compare", JSON.stringify(values)), [ids[0], ids[2]]);
      await page.goto(BASE + "comparar.html?ids=", { waitUntil: "domcontentloaded" });
      await page.waitForSelector("#compareMount:not(.loading)").catch(() => {});
      assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("qv_compare") || "[]")), []);
      assert.match(await page.locator("#compareMount").innerText(), /Ninguém selecionado/);
    });
    await check("cross-tab-storage-sync", async () => {
      await page.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
      await page.waitForSelector(`[data-compare-id="${ids[0]}"]`);
      const profile = await context.newPage();
      await profile.goto(BASE + "candidato.html?id=" + encodeURIComponent(ids[0]), { waitUntil: "domcontentloaded" });
      await profile.waitForSelector("#profileCompare");
      await profile.locator("#profileCompare").click();
      await page.bringToFront();
      await page.waitForFunction(id => document.querySelector(`[data-compare-id="${id}"]`)?.getAttribute("aria-pressed") === "true", ids[0]);
      assert.equal(await page.locator(`[data-compare-id="${ids[0]}"]`).innerText(), "Remover");
      await profile.close();
    });
    await context.close();

    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    await mobile.route(/googletagmanager\.com|google-analytics\.com/, route => route.abort());
    await mobile.addInitScript(() => localStorage.removeItem("qv_compare"));
    const m = await mobile.newPage();
    await check("mobile-390x844", async () => {
      await m.goto(BASE + "candidatos.html", { waitUntil: "domcontentloaded" });
      await m.waitForSelector("button[data-compare-id]");
      assert.ok(await m.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth) <= 1);
      const first = m.locator("button[data-compare-id]").first();
      await first.scrollIntoViewIfNeeded(); await first.tap();
      assert.equal(await first.getAttribute("aria-pressed"), "true");
      assert.equal(await m.locator("#compareTray").isVisible(), true);
    });
    await mobile.close();
    console.log(JSON.stringify({ head: "e0c0bcc61d21e5967add04254582cac59561933d", results }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(JSON.stringify({ results }, null, 2)); process.exit(1); });
