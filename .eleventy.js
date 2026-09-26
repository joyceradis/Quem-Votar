// Build-time only. Eleventy compiles src/ into plain static HTML/CSS/JS —
// nothing from this config or its templating language ships to the browser.
// See docs/REBUILD_V6.md and Issue #167 for the phased rebuild this supports.
module.exports = function (eleventyConfig) {
  return {
    dir: {
      input: "src",
      output: "_site",
      includes: "_includes",
    },
  };
};
