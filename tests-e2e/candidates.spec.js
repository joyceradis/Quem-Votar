// Listagem — contratos que a Fase 5 não pode quebrar.
// Cobre o que o audit-site.py exige (mounts de cards e paginação), o teto de
// 12 por página do AGENTS.md §6, os nomes de parâmetro de URL (de que
// dependem os links compartilhados e os 548 stubs de /social/) e o funil de
// comparação com teto de 3.
const { test, expect } = require("@playwright/test");
const { coletarErros } = require("./externo");

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

  // Achado do Codex no #198: um candidato com institutional_history mas
  // sem current_mandate fazia hasInstitutional() liberar a linha 'agora',
  // mas currentActivity() ainda retornava o texto de ausência — exatamente
  // o texto repetitivo que esta mudança tentava tirar, só que rotulado
  // como se fosse sobre o presente. Nenhum candidato real tem hoje esse
  // formato, então simula via interceptação de rede.
  test("card não mostra 'atuação atual' pra quem só tem histórico, sem mandato atual", async ({ page }) => {
    await page.route("**/data/generated/candidates-federal.json**", async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      if (body.length) {
        body[0] = {
          ...body[0],
          current_mandate: null,
          institutional_history: { history: [{ year: 2020, office: "Vereador" }] },
        };
      }
      await route.fulfill({ response, json: body });
    });
    await page.goto("candidatos.html");
    await expect(page.locator("#resultCount")).not.toHaveText("Carregando…");

    const primeiroCard = page.locator(".qv-card").first();
    await expect(primeiroCard.locator(".qv-card-now")).toHaveCount(0);
    await expect(primeiroCard).not.toContainText("Atuação atual ainda não confirmada");
  });

  // Feedback direto da mantenedora: partido é critério de escolha para
  // muita gente e não pode ficar escondido atrás de "Mais filtros".
  test("filtro de Partido fica visível sem precisar abrir 'Mais filtros'", async ({ page }) => {
    await expect(page.locator("#secondaryFilters")).toBeHidden();
    await expect(page.locator("#partyFilter")).toBeVisible();

    const opcoes = await page.locator("#partyFilter option").allTextContents();
    expect(opcoes.length).toBeGreaterThan(1);

    const antes = await page.locator("#resultCount").textContent();
    await page.selectOption("#partyFilter", { index: 1 });
    await expect(page.locator("#resultCount")).not.toHaveText(antes);
    expect(new URL(page.url()).searchParams.get("partido")).toBeTruthy();
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
    await expect(page.locator("#resultCount")).toHaveText(`${estadual} candidaturas`);
    expect(new URL(page.url()).searchParams.get("cargo")).toBe("estadual");
  });

  // Cargos majoritários (#161/#186/#193): Governador e Senador entram no
  // mesmo seletor, com o mesmo contrato de URL/paginação/busca dos dois
  // cargos legislativos — sem tratamento especial.
  test("Governador e Senador aparecem no seletor de cargo com contagem própria", async ({ page }) => {
    await expect(page.locator('.office-button[data-kind="governador"]')).toBeAttached();
    await expect(page.locator('.office-button[data-kind="senador"]')).toBeAttached();

    const governador = await page.locator("#governadorCount").textContent();
    const senador = await page.locator("#senadorCount").textContent();
    expect(Number(governador)).toBeGreaterThan(0);
    expect(Number(senador)).toBeGreaterThan(0);

    await page.locator('.office-button[data-kind="governador"]').click();
    await expect(page.locator("#resultCount")).toHaveText(`${governador} candidaturas`);
    expect(new URL(page.url()).searchParams.get("cargo")).toBe("governador");
    await expect(page.locator(".qv-card-kicker").first()).toHaveText("GOVERNADOR");

    await page.locator('.office-button[data-kind="senador"]').click();
    await expect(page.locator("#resultCount")).toHaveText(`${senador} candidaturas`);
    expect(new URL(page.url()).searchParams.get("cargo")).toBe("senador");
    await expect(page.locator(".qv-card-kicker").first()).toHaveText("SENADOR");
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
    const errors = coletarErros(page);

    await page.reload();
    await expect(page.locator("#resultCount")).not.toHaveText("Carregando…");
    expect(errors).toEqual([]);
  });
});
