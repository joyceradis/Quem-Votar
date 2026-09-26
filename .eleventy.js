// Build-time only. Eleventy compiles src/ into plain static HTML/CSS/JS —
// nothing from this config or its templating language ships to the browser.
// See docs/REBUILD_V6.md and Issue #167 for the phased rebuild this supports.
module.exports = function (eleventyConfig) {
  // assets/ vive na raiz do repo (contrato atual de produção) — copiado tal
  // qual para a saída, sem duplicar arquivos de imagem/ícone dentro de src/.
  eleventyConfig.addPassthroughCopy({ assets: "assets" });
  eleventyConfig.addPassthroughCopy("src/styles");

  return {
    dir: {
      input: "src",
      output: "_site",
      includes: "_includes",
    },
  };
};
