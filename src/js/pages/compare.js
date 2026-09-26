// Comparação — portado de initCompare (app.js:904-985).
//
// Mesmas linhas, mesma ordem, mesmo vocabulário de ausência. A comparação
// mostra os mesmos campos factuais para todo mundo e **não** produz
// vencedor, nota, ranking ou ordenação valorativa (AGENTS.md §2,
// docs/GOVERNANCE.md "Comparação"). Nenhuma linha aqui pode virar
// pontuação ou destaque de "melhor".
import { $, esc, params } from "../core/dom.js";
import { loadCore, applyGlobalMeta } from "../core/data.js";
import { formatBRL, formatSnapshot } from "../core/format.js";
import { updateSearchParams } from "../core/url-state.js";
import { setupNavigation, setupTextSize } from "../core/a11y.js";
import {
  loadTopics,
  setTopics,
  currentActivity,
  hasInstitutional,
  prospectiveTopicEvidence,
  documentedActionEvidence,
  practicalAreasFromEvidence,
} from "../core/evidence.js";
import { normalizeCompareIds, getCompareIds, setCompareIds } from "../core/compare-state.js";

setupNavigation();
setupTextSize();

function photoMarkup(candidate) {
  const source =
    candidate.photo_url || candidate.photoUrl || candidate.foto_url || candidate.photo?.url || "";
  const name = candidate.ballot_name || candidate.full_name || "candidato";
  if (!source) return `<div class="profile-fallback">Imagem não disponível</div>`;
  return `<img src="${esc(source)}" alt="Foto de ${esc(name)}" loading="lazy" data-photo>`;
}

// Cada linha é um campo factual igual para todas as colunas.
const LINHAS = [
  ["Cargo", (c) => (c._kind === "federal" ? "Deputado Federal" : "Deputado Estadual")],
  ["Hoje", (c) => currentActivity(c, c._kind)],
  ["Escolaridade", (c) => c.education || "Não disponível"],
  [
    "Atuação pública",
    (c) =>
      hasInstitutional(c)
        ? "Há informação pública disponível"
        : "Ainda não encontramos atuação pública atual",
  ],
  [
    "O que diz que vai fazer",
    (c) => {
      const evidence = prospectiveTopicEvidence(c);
      if (!evidence.length) return "Ainda sem proposta ou declaração com fonte";
      const areas = practicalAreasFromEvidence(evidence);
      return areas.length ? areas.map((t) => t.label).join(" · ") : "Há proposta ou declaração documentada";
    },
  ],
  ["Partido e número", (c) => `${c.party || "Partido não informado"} · nº ${c.number || "—"}`],
  ["Ocupação declarada", (c) => c.occupation || "Não disponível"],
  [
    "Histórico eleitoral",
    (c) => {
      const count = (c.previous_elections || []).length;
      return count
        ? `${count} eleiç${count === 1 ? "ão" : "ões"} anterior${count === 1 ? "" : "es"} documentada${count === 1 ? "" : "s"}`
        : "Nenhuma eleição anterior documentada";
    },
  ],
  [
    "Bens declarados ao TSE",
    (c) => {
      const count = c.assets?.count || (c.assets?.items || []).length || 0;
      const total = formatBRL(c.assets?.total_declared_brl);
      return count
        ? `${count} ${count === 1 ? "bem declarado" : "bens declarados"}${total ? ` · valor declarado ao TSE: ${total}` : ""}`
        : "Nenhum bem declarado nesta base";
    },
  ],
  [
    "Redes sociais informadas ao TSE",
    (c) => {
      const count = (c.social_links || []).length;
      return count
        ? `${count} rede${count === 1 ? "" : "s"} ${count === 1 ? "social" : "sociais"} informada${count === 1 ? "" : "s"}`
        : "Nenhuma rede social informada";
    },
  ],
  [
    "Atuação documentada",
    (c) => {
      const count = documentedActionEvidence(c).length;
      return count
        ? `${count} registro${count === 1 ? "" : "s"} de atuação documentado${count === 1 ? "" : "s"}`
        : "Ainda sem atuação pública documentada";
    },
  ],
];

async function initCompare() {
  const [{ all, meta, comparisonReady }, topics] = await Promise.all([loadCore(), loadTopics()]);
  setTopics(topics);
  applyGlobalMeta(meta);

  const mount = $("compareMount");

  // Fail-closed: sem os dois conjuntos carregados, a seleção do usuário é
  // preservada em vez de ser silenciosamente esvaziada.
  if (!comparisonReady) {
    mount.textContent =
      "Não foi possível carregar todas as candidaturas. Sua seleção foi preservada. Tente novamente.";
    return;
  }

  const urlParams = params();
  const fromUrl = (urlParams.get("ids") || "").split(",").filter(Boolean).map(String);
  const validIds = all.map((candidate) => String(candidate.tse_id));
  const ids = normalizeCompareIds(urlParams.has("ids") ? fromUrl : getCompareIds(), validIds);
  const selected = ids.map((id) => all.find((c) => String(c.tse_id) === id)).filter(Boolean);

  setCompareIds(ids);
  if (urlParams.has("ids")) updateSearchParams({ ids: ids.join(",") || null });

  if (selected.length < 2) {
    mount.innerHTML = `
      <div class="compare-empty">
        <h2>${selected.length ? "Escolha mais 1 pessoa." : "Ninguém selecionado."}</h2>
        <p>Abra a lista e escolha de duas a três pessoas para comparar.</p>
        <a href="candidatos.html?cargo=federal">Escolher pessoas</a>
      </div>`;
    return;
  }

  const linha = (label, renderer) =>
    `<div class="row-label">${esc(label)}</div>${selected
      .map((candidate) => `<div class="compare-value">${esc(renderer(candidate))}</div>`)
      .join("")}`;

  mount.innerHTML = `
    <div class="comparison-wrap">
      <div class="comparison-grid" style="--compare-cols:${selected.length}">
        <div class="row-label">Candidato</div>
        ${selected
          .map(
            (candidate) => `
              <div class="compare-person">
                ${photoMarkup(candidate)}
                <h2>${esc(candidate.ballot_name || candidate.full_name)}</h2>
                <span>${esc(candidate.party || "—")} · Nº ${esc(candidate.number || "—")}</span>
                <a href="candidato.html?id=${encodeURIComponent(candidate.tse_id)}&cargo=${candidate._kind}">Abrir perfil</a>
              </div>`
          )
          .join("")}
        ${LINHAS.map(([label, renderer]) => linha(label, renderer)).join("")}
      </div>
    </div>
    <p class="comparison-note">Dados disponíveis em ${esc(formatSnapshot(meta?.collected_at))}. Falta de informação aqui não significa ausência de proposta, posição ou experiência.</p>`;

  mount.querySelectorAll("img[data-photo]").forEach((img) => {
    img.addEventListener("error", () => {
      img.outerHTML = '<div class="profile-fallback">Imagem não disponível</div>';
    });
  });
}

initCompare();
