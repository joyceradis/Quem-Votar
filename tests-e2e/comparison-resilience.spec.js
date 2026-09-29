const { test, expect } = require("@playwright/test");
const federal = require("../data/generated/candidates-federal.json");
const governors = require("../data/generated/candidates-governador.json");
const senators = require("../data/generated/candidates-senador.json");

const federalIds = federal.slice(0, 2).map((c) => String(c.tse_id));

async function seedSelection(page, ids) {
  await page.addInitScript((selection) => {
    localStorage.setItem("qv_compare", JSON.stringify(selection));
  }, ids);
}

for (const failure of ["write", "read-and-write"]) {
  test(`consulta e seleção continuam com storage indisponível: ${failure}`, async ({ page }) => {
    await page.addInitScript(({ ids, failure }) => {
      localStorage.setItem("qv_compare", JSON.stringify(ids));
      Storage.prototype.setItem = () => { throw new DOMException("Blocked", "QuotaExceededError"); };
      if (failure === "read-and-write") {
        Storage.prototype.getItem = () => { throw new DOMException("Blocked", "SecurityError"); };
      }
    }, { ids: federalIds, failure });
    const errors = [];
    page.on("pageerror", (error) => errors.push(String(error)));
    await page.goto("candidatos.html");
    await expect(page.locator(".qv-card")).toHaveCount(12);
    const buttons = page.locator("[data-compare-id]");
    if (failure === "write") await page.locator("#clearCompare").click();
    await buttons.nth(0).click();
    await expect(buttons.nth(0)).toHaveAttribute("aria-pressed", "true");
    await buttons.nth(1).click();
    await expect(page.locator("#openCompare")).toHaveAttribute("href", /comparar\.html\?ids=/);
    await buttons.nth(0).click();
    await expect(buttons.nth(0)).toHaveAttribute("aria-pressed", "false");
    expect(errors).toEqual([]);
    // O link leva a seleção da memória para a outra página sem depender do storage.
    await buttons.nth(0).click();
    await page.locator("#openCompare").click();
    await expect(page.locator(".compare-person")).toHaveCount(2);
    expect(errors).toEqual([]);
  });
}

for (const [kind, candidates] of [["governador", governors], ["senador", senators]]) {
  const ids = candidates.slice(0, 2).map((c) => String(c.tse_id));
  for (const fromUrl of [false, true]) {
    test(`${kind}: falha preserva seleção e link (${fromUrl ? "URL" : "storage"})`, async ({ page }) => {
      await seedSelection(page, ids);
      await page.route(`**/data/generated/candidates-${kind}.json**`, (route) =>
        route.fulfill({ status: 503, body: "temporarily unavailable" })
      );
      const route = `comparar.html${fromUrl ? `?ids=${ids.join(",")}` : ""}`;
      await page.goto(route);
      await expect(page.locator("#compareMount")).toContainText("Sua seleção foi preservada");
      expect(await page.evaluate(() => JSON.parse(localStorage.getItem("qv_compare")))).toEqual(ids);
      expect(new URL(page.url()).searchParams.get("ids")).toBe(fromUrl ? ids.join(",") : null);
      await page.unroute(`**/data/generated/candidates-${kind}.json**`);
      await page.reload();
      await expect(page.locator(".compare-person")).toHaveCount(2);
    });
  }

  test(`${kind}: falha não bloqueia comparação de candidatos já carregados`, async ({ page }) => {
    await page.route(`**/data/generated/candidates-${kind}.json**`, (route) => route.abort());
    await page.goto(`comparar.html?ids=${federalIds.join(",")}`);
    await expect(page.locator(".compare-person")).toHaveCount(2);
  });

  test(`${kind}: consulta da lista não elimina seleção de cargo indisponível`, async ({ page }) => {
    await seedSelection(page, ids);
    await page.route(`**/data/generated/candidates-${kind}.json**`, (route) => route.abort());
    await page.goto("candidatos.html");
    await expect(page.locator(".qv-card")).toHaveCount(12);
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem("qv_compare")))).toEqual(ids);
  });
}

test("snapshot completo remove IDs inexistentes e duplicados", async ({ page }) => {
  await page.goto(`comparar.html?ids=${federalIds[0]},missing,${federalIds[0]},${federalIds[1]}`);
  await expect(page.locator(".compare-person")).toHaveCount(2);
  expect(new URL(page.url()).searchParams.get("ids")).toBe(federalIds.join(","));
});

test("resposta vazia válida não é tratada como falha de rede", async ({ page }) => {
  const ids = governors.slice(0, 2).map((c) => String(c.tse_id));
  await seedSelection(page, ids);
  await page.route("**/data/generated/candidates-governador.json**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
  );
  await page.goto("comparar.html");
  await expect(page.locator(".compare-empty")).toBeVisible();
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem("qv_compare")))).toEqual([]);
});
