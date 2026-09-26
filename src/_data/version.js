// Fonte única de verdade para o cache-busting de assets estáticos.
// Antes, cada HTML e o próprio app.js hardcodavam um "?v=" diferente
// (5.5.8 no HTML, 5.5 dentro do app.js, 5.5.0 no arquivo VERSION) — os três
// podiam divergir sem nenhum aviso. Agora todos os templates e módulos JS
// leem o mesmo VERSION do repositório, via este global data do Eleventy.
const fs = require("node:fs");
const path = require("node:path");

module.exports = () => {
  const raw = fs.readFileSync(path.join(__dirname, "..", "..", "VERSION"), "utf8");
  return raw.trim();
};
