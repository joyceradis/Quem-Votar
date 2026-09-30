const { test, expect } = require('@playwright/test');

test('Home aproveita a largura útil em monitores grandes', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('index.html');
  await page.evaluate(() => document.fonts.ready);
  const widths = await page.locator('.home-hero-copy, .home-topics, .home-choices').evaluateAll(nodes => nodes.map(node => {
    const style = getComputedStyle(node);
    return node.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
  }));
  for (const width of widths) expect(width).toBeGreaterThanOrEqual(1100);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(1920);
});

test('lista continua utilizável com texto ampliado em tela estreita', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('candidatos.html?cargo=federal');
  await expect(page.locator('.qv-card').first()).toBeVisible();
  await page.addStyleTag({ content: 'html { font-size: 34px !important; }' });
  const controls = page.locator('.office-button, #searchInput, #partyFilter, #filterToggle, .qv-btn--compare');
  for (const control of await controls.all()) {
    const box = await control.boundingBox();
    expect(box.height).toBeGreaterThanOrEqual(44);
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(320);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  await page.locator('#filterToggle').click();
  await expect(page.locator('#secondaryFilters')).toBeVisible();
});

test('atalho da ficha deixa o título acessível abaixo dos menus fixos', async ({ page }) => {
  await page.goto('candidato.html?id=80002542403&cargo=federal');
  await expect(page.locator('.profile-hero')).toBeVisible();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const jump = page.locator('.profile-jump a').first();
  const target = await jump.getAttribute('href');
  await jump.click();
  const heading = page.locator(`${target} h2`).first();
  await expect(heading).toBeInViewport();
  const headingBox = await heading.boundingBox();
  const navBox = await page.locator('.profile-jump').boundingBox();
  expect(headingBox.y).toBeGreaterThanOrEqual(navBox.y + navBox.height);
});
