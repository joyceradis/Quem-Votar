// Como funciona — portado de initAbout (app.js:987-994).
// Só preenche a data do snapshot; todo o resto é conteúdo estático.
import { $ } from "../core/dom.js";
import { loadCore, applyGlobalMeta } from "../core/data.js";
import { formatSnapshot } from "../core/format.js";
import { setupNavigation, setupTextSize } from "../core/a11y.js";

setupNavigation();
setupTextSize();

async function initAbout() {
  const { meta } = await loadCore();
  applyGlobalMeta(meta);
  const stamp = $("aboutUpdate");
  if (stamp) stamp.textContent = formatSnapshot(meta?.collected_at);
}

initAbout();
