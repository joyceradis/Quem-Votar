// Testes de ponta a ponta do design system/casco da reconstrução V6
// (src/). Não têm relação com a suíte Python em tests/ (pipeline de dados,
// contratos da produção atual) nem a executam — rodam contra o build do
// Eleventy em localhost, nunca contra produção.
const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests-e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1200, height: 900 } } },
    { name: "mobile", use: { ...devices["Pixel 5"], viewport: { width: 390, height: 844 } } },
  ],
  webServer: {
    command: "npx eleventy --serve --port=4173 --quiet",
    url: "http://127.0.0.1:4173/preview-shell/",
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
