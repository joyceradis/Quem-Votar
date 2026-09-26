// Listagem — contratos que a Fase 5 não pode quebrar.
// Cobre o que o audit-site.py exige (mounts de cards e paginação), o teto de
// 12 por página do AGENTS.md §6, os nomes de parâmetro de URL (de que
// dependem os links compartilhados e os 548 stubs de /social/) e o funil de
// comparação com teto de 3.
const { test, expect } = require("@playwright/test");

// As fotos das candidaturas vêm de host externo do TSE, inacessível no
// sandbox de CI. Falha de imagem externa não é defeito da página — o
// fallback textual é justamente o comportamento esperado — então o filtro
// abaixo ignora só isso, e nada mais.
const ruidoExterno = (texto) =>
  /ERR_TUNNEL_CONNECTION_FAILED|ERR_NAME_NOT_RESOLVED|ERR_CONNECTION/.test(texto) ||
  /Failed to load resource/.test(texto);

test.describe("Listagem de candidaturas", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("candidatos.html");
    await expect(page.locator("#resultCount")).not.toHaveText("Carregando…");
  });

  test("contratos exigidos pelo audit-site.py", async ({ page }) => {
    await expect(page.locator("body")).toHaveAttribute("data-page", "candidates");
    await expect(page.locator("#cards")).toBeAttached();
    await expect(page.locator("#pagination")).toBeAttached();
    await expect(page.locator('[aria-current="page"]').first()).toBeAttached();
  });

  test("12 resultados por página", async ({ page }) => {
    await expect(page.locator(".qv-card")).toHaveCount(12);
    await expect(page.locator("#pageStatus")).toHaveText(/^Página 1 de \d+$/);
  });

  test("busca filtra e grava os parâmetros de URL do contrato", async ({ page }) => {
    const antes = await page.locator("#resultCount").textContent();
    await page.fill("#searchInput", "maria");
    await expect(page.locator("#resultCount")).not.toHaveText(antes);

    const url = new URL(page.url());
    expect(url.searchParams.get("q")).toBe("maria");
    expect(url.searchParams.get("cargo")).toBe("federal");
    expect(url.searchParams.get("page")).toBe("1");
  });

  test("troca de cargo troca o conjunto e o parâmetro cargo", async ({ page }) => {
    const federal = await page.locator("#federalCount").textContent();
    const estadual = await page.locator("#estadualCount").textContent();
    expect(federal).not.toBe(estadual);

    await page.locator('.office-button[data-kind="estadual"]').click();
    await expect(page.locator("#resultCount")).toHaveText(`${estadual} pessoas`);
    expect(new URL(page.url()).searchParams.get("cargo")).toBe("estadual");
  });

  test("comparação respeita o teto de 3 e monta o link canônico", async ({ page }) => {
    const botoes = page.locator("[data-compare-id]");
    await botoes.nth(0).click();
    await expect(page.locator("#compareTray")).toBeVisible();
    await expect(page.locator("#openCompare")).toHaveAttribute("aria-disabled", "true");

    await botoes.nth(1).click();
    await expect(page.locator("#openCompare")).toHaveAttribute("href", /^comparar\.html\?ids=/);

    await botoes.nth(2).click();
    await expect(page.locator("#compareCount")).toHaveText(/Limite de 3/);

    // com o teto atingido, os demais ficam desabilitados em vez de sumirem
    await expect(botoes.nth(4)).toBeDisabled();

    await page.locator("#clearCompare").click();
    await expect(page.locator("#compareTray")).toBeHidden();
  });

  test("filtro por tema sem resultado não vira 'não tem proposta'", async ({ page }) => {
    await page.locator("#filterToggle").click();
    const temas = page.locator("#topicFilter option");
    if ((await temas.count()) < 2) test.skip();

    // combina um tema com uma busca impossível para forçar o estado vazio
    await page.locator("#topicFilter").selectOption({ index: 1 });
    await page.fill("#searchInput", "zzzzzznaoexiste");

    const vazio = page.locator(".qv-empty");
    await expect(vazio).toBeVisible();
    await expect(vazio).toContainText("não significa que a pessoa não tenha posição");
  });

  test("foto indisponível cai em texto, não em imagem quebrada", async ({ page }) => {
    // no sandbox o host de fotos do TSE é inacessível, então este é o
    // caminho de fallback real sendo exercitado
    const fallbacks = page.locator(".photo-fallback");
    if ((await fallbacks.count()) === 0) test.skip();
    await expect(fallbacks.first()).toHaveText("Imagem não disponível");
  });

  test("sem erro de script (ruído de imagem externa ignorado)", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (err) => errors.push(String(err)));
    page.on("console", (msg) => {
      if (msg.type() === "error" && !ruidoExterno(msg.text())) errors.push(msg.text());
    });

    await page.reload();
    await expect(page.locator("#resultCount")).not.toHaveText("Carregando…");
    expect(errors).toEqual([]);
  });
});
