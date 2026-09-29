// Extensão do playwright.config.js do repositório para contêineres sem o build do Chromium que o
// Playwright fixado no package.json procura (aqui só existe o de /opt/pw-browsers, e o
// `playwright install` não alcança a rede). Aponta o Chromium pré-instalado e mantém o resto:
// mesmos projetos (desktop e mobile), mesmo baseURL, mesmo servidor Eleventy na 4173.
//
//   npx playwright test -c .claude/skills/run-quem-votar/playwright.local.config.js
//
// QV_CHROMIUM sobrescreve o caminho do executável.
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "../../..");
const base = require(path.join(root, "playwright.config.js"));
const executablePath =
  process.env.QV_CHROMIUM || ["/opt/pw-browsers/chromium"].find((candidate) => fs.existsSync(candidate));

module.exports = {
  ...base,
  // Os caminhos do config original são relativos a ele; este arquivo mora noutra pasta.
  testDir: path.join(root, "tests-e2e"),
  outputDir: path.join(root, "test-results"),
  use: {
    ...base.use,
    launchOptions: { ...(base.use && base.use.launchOptions), ...(executablePath ? { executablePath } : {}) },
  },
  webServer: { ...base.webServer, cwd: root },
};
