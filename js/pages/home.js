// Home — portado de initHome (app.js:318-347). Mesmo comportamento: contagem
// e data sempre lidas do snapshot, e a seção de assuntos só aparece quando
// existe evidência temática documentada para pelo menos um tema.
import { $, esc } from "../core/dom.js";
import { loadCore, applyGlobalMeta } from "../core/data.js";
import { loadTopics, setTopics, allTopics, candidateTopicIds } from "../core/evidence.js";
import { setupNavigation, setupTextSize } from "../core/a11y.js";

setupNavigation();
setupTextSize();

async function initHome() {
  const [{ federal, estadual, meta, all }, topics] = await Promise.all([loadCore(), loadTopics()]);
  setTopics(topics);
  applyGlobalMeta(meta);

  const total = $("homeTotalCount");
  if (total) total.textContent = federal.length + estadual.length || "—";

  const evidencedTopicIds = new Set(all.flatMap((candidate) => candidateTopicIds(candidate)));
  const visibleTopics = allTopics().filter((topic) => evidencedTopicIds.has(topic.id));

  const mount = $("homeTopics");
  if (!mount) return;

  const section = mount.closest(".home-topics");

  // Sem evidência integrada, a seção inteira some — é melhor não mostrar nada
  // do que mostrar uma lista vazia que sugira "não há propostas".
  if (!visibleTopics.length) {
    if (section) section.hidden = true;
    mount.innerHTML = "";
    return;
  }

  if (section) section.hidden = false;
  mount.innerHTML = visibleTopics
    .map(
      (topic) => `
        <a href="temas.html#${encodeURIComponent(topic.id)}">
          <strong>${esc(topic.label)}</strong>
          <small>${esc((topic.life_areas || []).slice(0, 2).join(" · "))}</small>
        </a>`
    )
    .join("");
}

initHome();
