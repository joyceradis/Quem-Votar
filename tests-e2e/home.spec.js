// Home — os contratos que a Fase 5 não pode quebrar no corte.
// Espelha o que `scripts/audit-site.py` exige da Home em produção
// (data-page, <h1> com conteúdo, type="search"+name="q", data-snapshot-date,
// ausência de listagem concentrada) e o que o `AGENTS.md` exige do conteúdo.
const { test, expect } = require("@playwright/test");

test.describe("Home", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("contratos exigidos pelo audit-site.py", async ({ page }) => {
    await expect(page.locator("body")).toHaveAttribute("data-page", "home");
    await expect(page.locator("h1")).not.toBeEmpty();
    await expect(page.locator('input[type="search"][name="q"]')).toBeVisible();
    await expect(page.locator("[data-snapshot-date]").first()).toBeAttached();
    // a Home não pode voltar a concentrar a listagem de candidaturas
    await expect(page.locator("#cards")).toHaveCount(0);
  });

  test("busca preserva o contrato de URL da listagem", async ({ page }) => {
    const form = page.locator("form.qv-pill-search");
    await expect(form).toHaveAttribute("action", "candidatos.html");
    await expect(form).toHaveAttribute("method", "get");
    await expect(form.locator('select[name="cargo"]')).toBeAttached();
    await expect(form.locator('select[name="cargo"] option')).toHaveText([
      "Deputado Federal",
      "Deputado Estadual",
    ]);
  });

  test("contagem e data vêm do snapshot, não do código", async ({ page }) => {
    // o valor tem de sair do "—" inicial e virar número lido de meta.json
    await expect(page.locator("#homeTotalCount")).toHaveText(/^\d+$/);
    await expect(page.locator(".home-snapshot [data-snapshot-date]")).not.toHaveText("—");
    await expect(page.locator(".home-snapshot a[data-tse-source]")).toHaveAttribute(
      "href",
      /dadosabertos\.tse\.jus\.br/
    );
  });

  test("assuntos só aparecem com evidência documentada", async ({ page }) => {
    const links = page.locator("#homeTopics a");
    const count = await links.count();
    const sectionVisible = await page.locator(".home-topics").isVisible();

    // contrato: ou há temas com evidência e a seção aparece, ou não há e a
    // seção some inteira — nunca uma lista vazia sugerindo "sem propostas"
    expect(sectionVisible).toBe(count > 0);

    if (count > 0) {
      await expect(links.first()).toHaveAttribute("href", /^temas\.html#/);
    }
  });

  test("não exibe nota, ranking nem recomendação de voto", async ({ page }) => {
    const text = (await page.locator("main").innerText()).toLowerCase();

    // Procurar pela palavra "ranking" não serve: a Home a usa justamente para
    // negar ("sem ranking"). O que não pode aparecer é a *coisa* — nota,
    // colocação, recomendação.
    const padroesProibidos = [
      /\bmelhor candidat[oa]\b/,
      /\bpior candidat[oa]\b/,
      /\bnota\s*[:é]\s*\d/,
      /\bpontuaç(ão|ao)\b/,
      /\b\d+\s*[º°]\s*lugar\b/,
      /\b\d+\s*\/\s*10\b/,
      /\brecomendamos\b/,
      /\bvote\s+(n[oa]|em)\b/,
    ];
    for (const padrao of padroesProibidos) {
      expect(text, `padrão proibido encontrado: ${padrao}`).not.toMatch(padrao);
    }

    // E as ressalvas exigidas pelo AGENTS.md §2 precisam estar visíveis.
    expect(text).toContain("sem ranking");
    expect(text).toContain("sem dizer em quem votar");
  });

  test("carrega sem erro de console nem requisição quebrada", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (err) => errors.push(String(err)));
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    page.on("response", (res) => {
      if (!res.ok()) errors.push(`${res.status()} ${res.url()}`);
    });

    await page.reload({ waitUntil: "networkidle" });
    expect(errors).toEqual([]);
  });
});
