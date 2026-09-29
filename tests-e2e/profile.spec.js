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

const governadorPath = path.join(__dirname, "..", "data", "generated", "candidates-governador.json");
const governadores = fs.existsSync(governadorPath) ? JSON.parse(fs.readFileSync(governadorPath, "utf8")) : [];
// Governador que hoje não tem lacuna alguma (16/16 majoritários cobertos): a
// regra "lacuna nunca vira zero" continua exigindo teste, então a lacuna é
// simulada por interceptação de rede sobre este candidato.
const alvoGap = governadores[0];
const GAPS = ["assets", "social_links", "previous_elections"];
const simulaGap = (page) =>
  page.route("**/data/generated/candidates-governador.json**", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    const i = body.findIndex((c) => String(c.tse_id) === String(alvoGap.tse_id));
    body[i] = {
      ...body[i],
      assets: { total_declared_brl: null, count: 0, items: [], source: null },
      social_links: [],
      previous_elections: [],
      enrichment_gaps: GAPS,
    };
    await route.fulfill({ response, json: body });
  });

const senadorPath = path.join(__dirname, "..", "data", "generated", "candidates-senador.json");
const senadores = fs.existsSync(senadorPath) ? JSON.parse(fs.readFileSync(senadorPath, "utf8")) : [];
const comEvidenciaInstitucionalSemMandato = senadores.find(
  (c) => (c.institutional_evidence || []).length > 0 && !c.current_mandate
);

const comHistoricoCamara = federais.find((c) => c.institutional_history);

const fichaUrl = (c) => `candidato.html?id=${c.tse_id}&cargo=federal`;

// A foto da ficha vem de um host externo. A navegação só precisa do DOM;
// cada teste aguarda explicitamente o conteúdo da ficha que verifica.
const openProfile = (page, url) => page.goto(url, { waitUntil: "domcontentloaded" });

// Mesma regra de "ocupação utilizável" de src/js/pages/profile.js
// (GENERIC_OCCUPATIONS/isUsableOccupation) — replicada aqui só para decidir
// a expectativa do teste, nunca para gerar o dado.
const OCUPACOES_GENERICAS = new Set(["OUTROS", "OUTRO"]);
const normalizaOcupacao = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-zA-Z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toUpperCase();

test.describe("Ficha do candidato", () => {
  test("ordem normativa HOJE → PROPÕE → IMPACTO → HISTÓRICO → DADOS → FONTES", async ({ page }) => {
    await openProfile(page, fichaUrl(comEvidencia));
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
    await openProfile(page, fichaUrl(comEvidencia));
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
    await openProfile(page, fichaUrl(comEvidencia));
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
    await openProfile(page, fichaUrl(comEvidencia));
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
    await openProfile(page, fichaUrl(semEvidencia));
    await expect(page.locator("#vai-fazer")).toBeVisible();

    await expect(page.locator("#vai-fazer")).toContainText(
      "Isso não significa que a candidatura não tenha propostas ou posições."
    );
    // nunca um zero ou um traço no lugar da explicação
    await expect(page.locator("#vai-fazer .promise-list")).toHaveCount(0);
  });

  // Governador/Senador com enrichment_gaps (fonte TSE ainda não integrada
  // neste ciclo, ver meta.json not_available_for) não pode aparecer como
  // "não possui" bens/redes/histórico na ficha — mesmo caso real usado por
  // tests-e2e/pages.spec.js para o comparador.
  test("Histórico e Dados eleitorais avisam lacuna de fonte, nunca 'não possui'", async ({ page }) => {
    if (!alvoGap) test.skip();
    await simulaGap(page);
    await openProfile(page, fichaUrl({ ...alvoGap, tse_id: alvoGap.tse_id }).replace("cargo=federal", "cargo=governador"));

    const historico = page.locator("#historico");
    const dados = page.locator("#dados-eleitorais");
    await expect(historico).toContainText("Ainda não disponível na fonte atual");
    await expect(dados).toContainText("Ainda não disponível na fonte atual");
  });

  // S1 (Authorization-Issue #2/#160): institutional_evidence (vínculo ALES
  // datado) é dado canônico que a ficha ignorava. Precisa aparecer em
  // Histórico com fonte e aviso — e NUNCA em "O que essa pessoa faz hoje?",
  // que só pode vir de current_mandate. Caso real: candidato de Senador com
  // institutional_evidence e sem current_mandate. A ocupação autodeclarada ao
  // TSE é um dado diferente: pode legitimamente aparecer em "faz hoje" como
  // fato autodeclarado (nunca como atuação institucional confirmada), e isso
  // não é o mesmo que institutional_evidence vazar para lá — as duas coisas
  // são testadas separadamente aqui.
  test("institutional_evidence aparece em Histórico com fonte e aviso, nunca em 'faz hoje'", async ({ page }) => {
    if (!comEvidenciaInstitucionalSemMandato) test.skip();
    const c = comEvidenciaInstitucionalSemMandato;
    await openProfile(page, `candidato.html?id=${c.tse_id}&cargo=senador`);

    const record = c.institutional_evidence[0];
    const hoje = page.locator("#faz-hoje");
    const historico = page.locator("#historico");

    const ocupacaoUtilizavel =
      Boolean(c.occupation) && !OCUPACOES_GENERICAS.has(normalizaOcupacao(c.occupation));
    if (ocupacaoUtilizavel) {
      // Sem current_mandate, mas com ocupação utilizável: aparece como fato
      // autodeclarado, nunca como confirmação de atuação institucional.
      await expect(hoje).toContainText(c.occupation);
      await expect(hoje).toContainText("Autodeclarado no registro de candidatura ao TSE");
    } else {
      await expect(hoje).toContainText("Sem atuação pública atual confirmada nesta base");
    }
    // institutional_evidence nunca vaza para "faz hoje", com ou sem ocupação.
    await expect(hoje).not.toContainText(record.institution);
    await expect(hoje).not.toContainText(record.type);

    await expect(historico).toContainText(record.institution);
    await expect(historico).toContainText(record.type);
    if (record.warning) {
      await expect(historico).toContainText(record.warning);
    }
  });

  // S1: institutional_history (trajetória partidária/legislaturas da
  // Câmara) também vira conteúdo em Histórico, não só fonte de link.
  test("institutional_history aparece como trajetória em Histórico", async ({ page }) => {
    if (!comHistoricoCamara) test.skip();
    await openProfile(page, fichaUrl(comHistoricoCamara));
    await expect(page.locator("#historico")).toContainText("Trajetória institucional na Câmara");
  });

  test("IMPACTO não afirma benefício nem prejuízo", async ({ page }) => {
    await openProfile(page, fichaUrl(comEvidencia));
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
    await openProfile(page, fichaUrl(comEvidencia));
    const dados = page.locator("#dados-eleitorais");
    await expect(dados).toBeVisible();

    const texto = await dados.innerText();
    expect(texto).not.toContain("#NE");
    expect(texto).not.toContain("#NULO");
    if (!comEvidencia.registration_status || comEvidencia.registration_status === "not_available") {
      expect(texto).toContain("Ainda não disponível na fonte atual");
    }
  });

  // Renúncia ou indeferimento mudam o que a pessoa faz na urna: a situação sobe
  // para o topo da ficha, em caixa de frase. A sentinela não vira afirmação
  // (a seção de dados eleitorais é que diz "não disponível").
  test("situação da candidatura aparece no topo da ficha, sem virar afirmação quando indisponível", async ({ page }) => {
    const alterna = async (status) => {
      await page.unroute("**/data/generated/candidates-federal.json**").catch(() => {});
      await page.route("**/data/generated/candidates-federal.json**", async (route) => {
        const response = await route.fetch();
        const body = await response.json();
        const i = body.findIndex((c) => String(c.tse_id) === String(comEvidencia.tse_id));
        body[i] = { ...body[i], registration_status: status };
        await route.fulfill({ response, json: body });
      });
      await openProfile(page, fichaUrl(comEvidencia));
      await expect(page.locator("#dados-eleitorais")).toBeVisible();
    };

    await alterna("RENÚNCIA");
    await expect(page.locator(".hero-facts")).toContainText("Situação da candidatura");
    await expect(page.locator(".hero-facts")).toContainText("Renúncia");
    await expect(page.locator(".hero-facts")).not.toContainText("RENÚNCIA");

    await alterna("not_available");
    await expect(page.locator(".hero-facts")).not.toContainText("Situação da candidatura");
    await expect(page.locator("#dados-eleitorais")).toContainText("Ainda não disponível na fonte atual");
  });

  test("compartilhamento aponta para o stub estático de /social/", async ({ page }) => {
    await openProfile(page, fichaUrl(comEvidencia));
    await expect(page.locator("h1")).not.toBeEmpty();
    await expect(page.locator('meta[property="og:url"]')).toHaveAttribute(
      "content",
      new RegExp(`/social/${comEvidencia.tse_id}/$`)
    );
  });

  test("id inexistente e id ausente falham de forma explícita", async ({ page }) => {
    await openProfile(page, "candidato.html?id=000000000&cargo=federal");
    await expect(page.locator("#profileMount")).toHaveText("Candidato não encontrado na base atual.");

    await openProfile(page, "candidato.html");
    await expect(page.locator("#profileMount")).toHaveText("Candidato não informado.");
  });
});


test("bens têm atalho visível e detalhamento progressivo com total preservado", async ({ page }) => {
  const candidate = federais.find((c) => c.assets?.items?.length > 0);
  test.skip(!candidate, "Snapshot sem declaração de bens");
  await openProfile(page, fichaUrl(candidate));
  const jump = page.getByRole("navigation", { name: "Navegar pela ficha" });
  const assetsLink = jump.getByRole("link", { name: "Bens declarados", exact: true });
  await expect(assetsLink).toBeVisible();
  const navWidth = await jump.evaluate((el) => ({ scroll: el.scrollWidth, client: el.clientWidth }));
  expect(navWidth.scroll).toBeLessThanOrEqual(navWidth.client + 1);
  await assetsLink.click();
  await expect(page).toHaveURL(/#bens-declarados$/);
  const assets = page.locator("#bens-declarados");
  await expect(assets.locator(".declared-assets-total")).toBeVisible();
  await expect(assets.locator(".declared-assets-list")).not.toBeVisible();
  await assets.locator("summary").focus();
  await page.keyboard.press("Enter");
  await expect(assets.locator(".declared-assets-list")).toBeVisible();
  await expect(assets.locator(".declared-assets-list li")).toHaveCount(candidate.assets.items.length);
});
