// Build-time only. Eleventy compiles src/ into plain static HTML/CSS/JS —
// nothing from this config or its templating language ships to the browser.
// See docs/REBUILD_V6.md and Issue #167 for the phased rebuild this supports.
const fs = require("node:fs");
const path = require("node:path");

module.exports = function (eleventyConfig) {
  // Inlina um SVG de assets/ direto no HTML. Usado quando o SVG precisa ser
  // recolorido por CSS (ex.: a marca d'água do rodapé, que vira branca sobre
  // o fundo escuro): via <img> o CSS da página não alcança o interior do
  // SVG, e a alternativa seria manter um segundo arquivo quase idêntico —
  // exatamente o tipo de duplicação que esta reconstrução existe para acabar.
  eleventyConfig.addFilter("svgInline", (file) => {
    const full = path.join(__dirname, "assets", file);
    return fs.readFileSync(full, "utf8");
  });
  eleventyConfig.addWatchTarget("./assets/");

  // assets/ vive na raiz do repo (contrato atual de produção) — copiado tal
  // qual para a saída, sem duplicar arquivos de imagem/ícone dentro de src/.
  eleventyConfig.addPassthroughCopy({ assets: "assets" });
  eleventyConfig.addPassthroughCopy("src/styles");
  eleventyConfig.addPassthroughCopy("src/js");

  return {
    dir: {
      input: "src",
      output: "_site",
      includes: "_includes",
    },
  };
};
