// Comparar, Assuntos, Como funciona e Apoiar.
// Verifica o contrato de cada uma e, principalmente, que o casco
// compartilhado (nav, drawer, rodapé) está em todas — inclusive na apoio.html,
// que antes era a única página fora do padrão.
const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");

const federais = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "data", "generated", "candidates-federal.json"), "utf8")
);
const doisIds = federais.slice(0, 2).map((c) => c.tse_id);

const TODAS = [
  ["/", "home"],
  ["/candidatos.html", "candidates"],
  ["/candidato.html", "profile"],
  ["/comparar.html", "compare"],
  ["/temas.html", "topics"],
  ["/sobre.html", "about"],
  ["/apoio.html", "apoio"],
];

test.describe("Casco em todas as páginas", () => {
  for (const [rota, dataPage] of TODAS) {
    test(`${rota} tem data-page, drawer e rodapé compartilhados`, async ({ page }) => {
      await page.goto(rota);
      await expect(page.locator("body")).toHaveAttribute("data-page", dataPage);
      await expect(page.locator("#drawer")).toBeAttached();
      await expect(page.locator("#menuButton")).toBeAttached();
      await expect(page.locator(".qv-fat-footer")).toBeAttached();
      await expect(page.locator(".skip-link")).toBeAttached();
    });
  }
});

test.describe("Comparar", () => {
  test("mostra os mesmos campos para todos e não elege vencedor", async ({ page }) => {
    await page.goto(`/comparar.html?ids=${doisIds.join(",")}`);
    await expect(page.locator(".comparison-grid")).toBeVisible();

    await expect(page.locator(".compare-person")).toHaveCount(2);
    const rotulos = await page.locator(".row-label").allTextContents();
    expect(rotulos).toContain("Hoje");
    expect(rotulos).toContain("O que diz que vai fazer");

    // cada linha tem exatamente um valor por pessoa: ninguém fica sem campo
    const linhas = rotulos.length - 1; // "Candidato" não é linha de valor
    await expect(page.locator(".compare-value")).toHaveCount(linhas * 2);

    // Neutralidade aqui é estrutural, não de vocabulário: a página *cita* as
    // palavras "nota final", "ranking" e "vencedor" justamente para negá-las.
    // O que precisa ser verdade é que nenhuma coluna recebe destaque,
    // posição ou pontuação.
    const classesDasColunas = await page
      .locator(".compare-person")
      .evaluateAll((els) => els.map((e) => e.className));
    expect(new Set(classesDasColunas).size).toBe(1); // todas idênticas

    const temPontuacao = await page.locator("main").evaluate((main) =>
      /\b\d+\s*(pontos?|\/\s*10|%\s*de afinidade)\b|\b\d+\s*[º°]\s*lugar\b/i.test(main.innerText)
    );
    expect(temPontuacao).toBe(false);

    await expect(page.locator(".comparison-note")).toContainText(
      "não significa ausência de proposta, posição ou experiência"
    );
  });

  test("menos de 2 selecionados leva de volta para a escolha", async ({ page }) => {
    await page.goto("/comparar.html?ids=");
    await expect(page.locator(".compare-empty")).toBeVisible();
    await expect(page.locator(".compare-empty a")).toHaveAttribute("href", /candidatos\.html/);
  });

  test("ids inválidos são descartados sem quebrar a página", async ({ page }) => {
    await page.goto("/comparar.html?ids=000,111,222");
    await expect(page.locator(".compare-empty")).toBeVisible();
  });
});

test.describe("Assuntos", () => {
  test("lista só temas com evidência e liga para a listagem filtrada", async ({ page }) => {
    await page.goto("/temas.html");
    await expect(page.locator("#topicCards")).toBeVisible();

    const linhas = page.locator(".topic-row");
    const total = await linhas.count();
    expect(total).toBeGreaterThan(0);

    for (let i = 0; i < total; i++) {
      // a contagem exibida é de pessoas com fonte, e nunca pode ser zero:
      // tema sem ninguém não deve ser listado
      const n = Number(await linhas.nth(i).locator(".topic-status strong").textContent());
      expect(n).toBeGreaterThan(0);
    }

    await expect(linhas.first().locator("a")).toHaveAttribute("href", /^candidatos\.html\?tema=/);
  });
});

test.describe("Como funciona", () => {
  test("explica ausência de dado e nega recomendação de voto", async ({ page }) => {
    await page.goto("/sobre.html");
    const texto = await page.locator("main").innerText();
    expect(texto).toContain("Não transforma ausência de informação");
    expect(texto.toLowerCase()).toContain("não existe nota, ranking");
    await expect(page.locator("#aboutUpdate")).not.toHaveText("—");
  });
});

test.describe("Apoiar", () => {
  test("usa o casco padrão e mantém o firewall editorial explícito", async ({ page }) => {
    await page.goto("/apoio.html");
    await expect(page.locator(".support-trust")).toContainText("Independência preservada");
    await expect(page.locator(".governance-details")).toBeAttached();
    // nenhum dado de candidatura é exibido nesta página
    await expect(page.locator(".qv-card")).toHaveCount(0);
    await expect(page.locator("#cards")).toHaveCount(0);
  });

  test("copiar chave Pix dá retorno visível", async ({ page, context, browserName }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]).catch(() => {});
    await page.goto("/apoio.html");
    await page.locator("#copyEmail").click();
    await expect(page.locator("#pixFeedback")).not.toBeEmpty();
  });
});
