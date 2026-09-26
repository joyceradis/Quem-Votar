// Formaliza os testes comportamentais que vinham sendo rodados manualmente
// (scripts descartáveis) contra o casco compartilhado (src/_includes/base.njk
// + nav.njk + footer.njk + core/a11y.js). Mesmo contrato de
// tests/test_accessibility_contract.py hoje em produção — porte formal para
// o app real acontece página por página na Fase 3.
const { test, expect } = require("@playwright/test");

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

  test("aumento de texto persiste entre recarregamentos", async ({ page }) => {
    await page.goto("preview-shell.html");
    await page.click("#textSizeButton");
    await expect(page.locator("html")).toHaveAttribute("data-scale", "large");

    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-scale", "large");
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

    await page.goto("preview-shell.html");
    await page.waitForLoadState("networkidle");

    expect(errors).toEqual([]);
  });
});

test.describe("design system — /styleguide/", () => {
  test("componentes principais renderizam", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (err) => errors.push(String(err)));
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await page.goto("styleguide.html");

    await expect(page.locator(".qv-btn--primary")).toBeVisible();
    await expect(page.locator(".qv-pill-search")).toBeVisible();
    await expect(page.locator(".qv-tag").first()).toBeVisible();
    await expect(page.locator(".qv-card")).toBeVisible();

    expect(errors).toEqual([]);
  });
});
