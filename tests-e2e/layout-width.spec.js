const { test, expect } = require("@playwright/test");

const routes = [
  ["candidatos.html?cargo=senador", ".qv-card"],
  ["candidato.html?id=80002542401&cargo=senador", ".profile-hero"],
  ["comparar.html?ids=80002541012,80002551833", ".comparison-grid"],
  ["temas.html", ".qv-page"],
  ["sobre.html", ".qv-page"],
  ["apoio.html", ".qv-page"],
];

for (const [route, ready] of routes) {
  test(`casco mantém espaço de leitura em telas largas: ${route}`, async ({ page }) => {
    for (const width of [1366, 1920, 2560]) {
      await page.setViewportSize({ width, height: 1080 });
      await page.goto(route);
      await expect(page.locator(ready).first()).toBeVisible();
      const layout = await page.locator(".qv-page, .profile-shell").evaluate((shell) => {
        const style = getComputedStyle(shell);
        return {
          contentWidth: shell.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight),
          viewportWidth: innerWidth,
          documentWidth: document.documentElement.scrollWidth,
        };
      });
      // Ampliar a tela nunca deve comprimir os conteúdos em uma coluna móvel.
      expect(layout.contentWidth).toBeGreaterThanOrEqual(920);
      expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewportWidth);
    }
  });
}
