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
  // Snapshot público: copiado como está, para a prévia local consumir os
  // mesmos JSON que a produção. Nada aqui é gerado nem alterado pelo build.
  eleventyConfig.addPassthroughCopy({ "data/generated": "data/generated" });
  eleventyConfig.addPassthroughCopy({ "data/reference": "data/reference" });

  // Arquivos públicos que já existem na raiz e são linkados pelo casco ou
  // pelas páginas. Sem isso, a saída do build fica com links quebrados que a
  // prévia local (servida da raiz) não revelava.
  for (const file of [
    "manifest.webmanifest",
    "sitemap.xml",
    "METODOLOGIA.md",
    "AUDITORIA.md",
    "telemetry.js",
  ]) {
    eleventyConfig.addPassthroughCopy(file);
  }
  // Stubs de preview social (/social/<SQ_CANDIDATO>/): contrato de URL
  // preservado; serão regerados contra o markup definitivo na Fase 4.
  eleventyConfig.addPassthroughCopy("social");
  eleventyConfig.addPassthroughCopy("docs");

  // Páginas internas de revisão (styleguide e prévia do casco) não são rotas
  // públicas: só entram na saída quando QV_DEV=1 (npm start).
  if (process.env.QV_DEV !== "1") {
    eleventyConfig.ignores.add("src/styleguide.njk");
    eleventyConfig.ignores.add("src/preview-shell.njk");
  }

  return {
    // O site é publicado em https://joyceradis.github.io/Quem-Votar/ — nunca
    // na raiz do domínio. Com pathPrefix o servidor de prévia (e o Playwright)
    // montam a saída sob o mesmo subcaminho da produção, que é onde caminho
    // absoluto quebra. Os links do markup são relativos, então o prefixo não
    // precisa ser reescrito em lugar nenhum: serve para *testar* a forma real
    // da URL, não para gerá-la.
    pathPrefix: "/Quem-Votar/",
    dir: {
      input: "src",
      output: "_site",
      includes: "_includes",
    },
  };
};
