// Ficha — as regras editoriais do AGENTS.md §2/§5 viradas em teste.
// Estas são as que mais doem se regredirem: elas é que separam "informar"
// de "insinuar".
const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");

const federais = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "data", "generated", "candidates-federal.json"), "utf8")
);

const comEvidencia = federais.find((c) => (c.topic_evidence || []).length > 1) || federais[0];
const semEvidencia = federais.find((c) => (c.topic_evidence || []).length === 0);

const fichaUrl = (c) => `candidato.html?id=${c.tse_id}&cargo=federal`;

test.describe("Ficha do candidato", () => {
  test("ordem normativa HOJE → PROPÕE → IMPACTO → HISTÓRICO → DADOS → FONTES", async ({ page }) => {
    await page.goto(fichaUrl(comEvidencia));
    await expect(page.locator("#faz-hoje")).toBeVisible();

    const ordem = await page.locator(".answer-section").evaluateAll((els) => els.map((e) => e.id));
    expect(ordem).toEqual([
      "faz-hoje",
      "vai-fazer",
      "impacto",
      "historico",
      "dados-eleitorais",
      "fontes",
    ]);
  });

  test("PROPÕE só aceita proposta e declaração; atuação vai para histórico", async ({ page }) => {
    await page.goto(fichaUrl(comEvidencia));
    await expect(page.locator("#vai-fazer")).toBeVisible();

    const evidencias = comEvidencia.topic_evidence || [];
    const normaliza = (v) =>
      String(v || "").trim().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    const prospectivas = evidencias.filter((e) =>
      ["proposta", "declaracao"].includes(normaliza(e.evidence_type))
    );
    const atuacoes = evidencias.filter((e) => normaliza(e.evidence_type) === "atuacao");

    await expect(page.locator("#vai-fazer .promise-list article")).toHaveCount(prospectivas.length);
    await expect(page.locator("#historico .public-records article")).toHaveCount(atuacoes.length);
  });

  test("toda evidência em PROPÕE mostra tipo, fonte e link", async ({ page }) => {
    await page.goto(fichaUrl(comEvidencia));
    const itens = page.locator("#vai-fazer .promise-list article");
    const total = await itens.count();
    if (total === 0) test.skip();

    for (let i = 0; i < total; i++) {
      const item = itens.nth(i);
      await expect(item.locator("span").first()).not.toBeEmpty(); // tema
      await expect(item.locator("h3")).not.toBeEmpty(); // o que foi dito
      await expect(item.locator(".evidence-meta")).not.toBeEmpty(); // tipo · fonte · data
    }
  });

  test("ocupação declarada não é apresentada como atuação atual", async ({ page }) => {
    await page.goto(fichaUrl(comEvidencia));
    await expect(page.locator(".profile-now")).toBeVisible();

    const agora = (await page.locator(".profile-now").textContent()).trim();
    // "o que faz hoje" só pode ser mandato confirmado ou a frase de ausência
    expect(agora).toMatch(
      /^(Deputado federal em exercício|Mandato atual confirmado|Atuação atual ainda não confirmada nesta base)$/
    );

    if (comEvidencia.occupation) {
      // a ocupação existe na ficha, mas só na camada de dados eleitorais
      expect(agora).not.toContain(comEvidencia.occupation);
      await expect(page.locator("#dados-eleitorais")).toContainText(comEvidencia.occupation);
    }
  });

  test("ausência de evidência é dita como ausência de registro", async ({ page }) => {
    if (!semEvidencia) test.skip();
    await page.goto(fichaUrl(semEvidencia));
    await expect(page.locator("#vai-fazer")).toBeVisible();

    await expect(page.locator("#vai-fazer")).toContainText(
      "Ausência de registro não significa ausência de proposta."
    );
    // nunca um zero ou um traço no lugar da explicação
    await expect(page.locator("#vai-fazer .promise-list")).toHaveCount(0);
  });

  test("IMPACTO não afirma benefício nem prejuízo", async ({ page }) => {
    await page.goto(fichaUrl(comEvidencia));
    const impacto = page.locator("#impacto");
    await expect(impacto).toBeVisible();

    const texto = (await impacto.innerText()).toLowerCase();
    for (const padrao of [/\bvai beneficiar\b/, /\bvai prejudicar\b/, /\bgarante que\b/, /\bmelhora sua vida\b/]) {
      expect(texto).not.toMatch(padrao);
    }
    if ((await impacto.locator(".impact-list article").count()) > 0) {
      await expect(impacto).toContainText("não são previsão de benefício, prejuízo ou efeito individual");
    }
  });

  test("sentinela do TSE não vira conclusão jurídica", async ({ page }) => {
    await page.goto(fichaUrl(comEvidencia));
    const dados = page.locator("#dados-eleitorais");
    await expect(dados).toBeVisible();

    const texto = await dados.innerText();
    expect(texto).not.toContain("#NE");
    expect(texto).not.toContain("#NULO");
    if (!comEvidencia.registration_status || comEvidencia.registration_status === "not_available") {
      expect(texto).toContain("Ainda não disponível na fonte atual");
    }
  });

  test("compartilhamento aponta para o stub estático de /social/", async ({ page }) => {
    await page.goto(fichaUrl(comEvidencia));
    await expect(page.locator("h1")).not.toBeEmpty();
    await expect(page.locator('meta[property="og:url"]')).toHaveAttribute(
      "content",
      new RegExp(`/social/${comEvidencia.tse_id}/$`)
    );
  });

  test("id inexistente e id ausente falham de forma explícita", async ({ page }) => {
    await page.goto("candidato.html?id=000000000&cargo=federal");
    await expect(page.locator("#profileMount")).toHaveText("Pessoa não encontrada na base atual.");

    await page.goto("candidato.html");
    await expect(page.locator("#profileMount")).toHaveText("Pessoa não informada.");
  });
});
