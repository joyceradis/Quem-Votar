// Formaliza os testes comportamentais que vinham sendo rodados manualmente
// (scripts descartáveis) contra o casco compartilhado (src/_includes/base.njk
// + nav.njk + footer.njk + core/a11y.js). Mesmo contrato de
// tests/test_accessibility_contract.py hoje em produção — porte formal para
// o app real acontece página por página na Fase 3.
const { test, expect } = require("@playwright/test");
const { coletarErros } = require("./externo");

test.describe("casco compartilhado — /preview-shell/", () => {
  test("nav responde ao breakpoint (desktop vs. hambúrguer)", async ({ page }) => {
    await page.goto("preview-shell.html");
    const viewport = page.viewportSize();
    const isDesktop = viewport.width >= 980;

    await expect(page.locator(".desktop-nav")).toBeVisible({ visible: isDesktop });
    await expect(page.locator("#menuButton")).toBeVisible({ visible: !isDesktop });
  });

  test("item ativo do nav usa aria-current, não só cor", async ({ page }) => {
    await page.goto("preview-shell.html");
    const active = page.locator('[aria-current="page"]').first();
    await expect(active).toHaveText("Candidatos");
  });

  // O rodapé é informação e navegação, não vitrine: a ilustração de linha foi
  // retirada por decisão da mantenedora. O contrato que fica é marca +
  // navegação + data dos dados, num plano escuro legível, sem sangria lateral.
  test("rodapé entrega marca, navegação e data dos dados sem ilustração e sem sangrar no celular", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("preview-shell.html");

    const footer = page.locator(".qv-footer");
    await expect(footer.locator(".qv-footer-brand strong")).toHaveText("Quem Votar?");
    await expect(footer.getByRole("navigation", { name: "Navegação complementar" })).toBeVisible();
    await expect(footer.getByRole("navigation", { name: "Sobre o projeto" })).toBeVisible();
    await expect(footer.locator("[data-snapshot-date]")).toBeAttached();

    // Nenhuma arte decorativa voltou pelo caminho do SVG, do <img> ou do CSS.
    await expect(footer.locator("svg")).toHaveCount(0);
    await expect(footer.locator("img")).toHaveCount(0);
    await expect(footer.locator(".qv-fat-footer-line-art")).toHaveCount(0);
    await expect(footer.locator(".qv-footer-grid")).toHaveCSS("background-image", "none");

    // Plano escuro: o texto não pode ficar com a tinta clara do corpo.
    const plano = await footer.evaluate((el) => {
      const estilo = getComputedStyle(el);
      return { fundo: estilo.backgroundColor, tinta: estilo.color };
    });
    expect(plano.fundo).toBe("rgb(13, 44, 65)");
    expect(plano.tinta).not.toBe(plano.fundo);

    const dimensions = await page.evaluate(() => ({
      viewport: innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);
  });

  test("abrir o drawer move o foco e Esc devolve ao botão Menu", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("preview-shell.html");

    await page.click("#menuButton");
    await expect(page.locator("#drawer")).toHaveClass(/open/);
    await expect(page.locator("#drawer")).toHaveAttribute("aria-hidden", "false");
    await expect(page.locator("#menuButton")).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#closeMenu")).toBeFocused();

    await page.keyboard.press("Escape");
    await expect(page.locator("#drawer")).not.toHaveClass(/open/);
    await expect(page.locator("#menuButton")).toBeFocused();
  });

  test("carrega sem erro de console nem requisição quebrada", async ({ page }) => {
    const errors = coletarErros(page);

    await page.goto("preview-shell.html");
    await page.waitForLoadState("networkidle");

    expect(errors).toEqual([]);
  });
});

test.describe("design system — /styleguide/", () => {
  test("componentes principais renderizam", async ({ page }) => {
    const errors = coletarErros(page);

    await page.goto("styleguide.html");

    await expect(page.locator(".qv-btn--primary")).toBeVisible();
    await expect(page.locator(".qv-pill-search")).toBeVisible();
    await expect(page.locator(".qv-tag").first()).toBeVisible();
    await expect(page.locator(".qv-card")).toBeVisible();

    expect(errors).toEqual([]);
  });
});
