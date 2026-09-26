// Assuntos — portado de initTopics (app.js:646-677).
//
// A contagem por tema é de *candidaturas com evidência*, não de evidências:
// o número diz "quantas pessoas têm registro com fonte neste assunto", e
// nunca é usado para ordenar tema por relevância ou qualidade.
import { $, esc } from "../core/dom.js";
import { loadCore, applyGlobalMeta } from "../core/data.js";
import { setupNavigation, setupTextSize } from "../core/a11y.js";
import { loadTopics, setTopics, allTopics, topicEvidence } from "../core/evidence.js";

setupNavigation();
setupTextSize();

async function initTopics() {
  const [core, topics] = await Promise.all([loadCore(), loadTopics()]);
  setTopics(topics);
  applyGlobalMeta(core.meta);

  const stats = {};
  allTopics().forEach((topic) => {
    stats[topic.id] = { candidates: new Set(), evidence: 0 };
  });

  core.all.forEach((candidate) => {
    topicEvidence(candidate).forEach((item) => {
      if (stats[item.topic_id]) {
        stats[item.topic_id].candidates.add(String(candidate.tse_id));
        stats[item.topic_id].evidence += 1;
      }
    });
  });

  // Tema sem nenhuma candidatura com evidência não é listado — listar com
  // zero sugeriria que ninguém se posiciona sobre ele.
  const visibleTopics = allTopics().filter((topic) => stats[topic.id]?.candidates.size);

  $("topicCards").innerHTML = visibleTopics.length
    ? visibleTopics
        .map((topic) => {
          const count = stats[topic.id].candidates.size;
          return `
            <article class="topic-row" id="${esc(topic.id)}">
              <div class="topic-main">
                <h2>${esc(topic.label)}</h2>
                <p>${esc(topic.description)}</p>
                <ul class="life-areas">${(topic.life_areas || [])
                  .map((area) => `<li>${esc(area)}</li>`)
                  .join("")}</ul>
              </div>
              <p class="topic-status">
                <strong>${count}</strong>
                <span>pessoa${count === 1 ? "" : "s"} com fonte neste assunto</span>
              </p>
              <a href="candidatos.html?tema=${encodeURIComponent(topic.id)}">Ver pessoas</a>
            </article>`;
        })
        .join("")
    : `<p class="qv-empty">Ainda não há propostas, declarações ou atuações temáticas integradas com fonte. A ausência de registro não significa ausência de posição.</p>`;
}

initTopics();
