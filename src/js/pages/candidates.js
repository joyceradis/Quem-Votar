// Listagem — portado de initCandidates/candidateCard/renderPagination
// (app.js:459-645). Mesmos filtros, mesma ordenação, mesmos parâmetros de
// URL, mesmo teto de 12 por página. As duas diferenças são estruturais, não
// de comportamento: o sync de URL usa core/url-state.js (antes reimplementado
// aqui) e o cartão virou função própria.
import { $, esc, norm, params } from "../core/dom.js";
import { loadCore, applyGlobalMeta } from "../core/data.js";
import { formatSnapshot } from "../core/format.js";
import { updateSearchParams } from "../core/url-state.js";
import { setupNavigation, setupTextSize } from "../core/a11y.js";
import {
  loadTopics,
  setTopics,
  allTopics,
  topicById,
  topicEvidence,
  candidateTopicIds,
  hasInstitutional,
  currentActivity,
} from "../core/evidence.js";
import {
  getCompareIds,
  setCompareIds,
  comparisonState,
  toggleCompare,
  syncComparisonControls,
  setupComparisonSync,
  announceComparison,
} from "../core/compare-state.js";

// Contrato público auditável: 12 resultados por página (AGENTS.md §6).
const PAGE_SIZE = 12;

setupNavigation();
setupTextSize();

function photoMarkup(candidate) {
  const source =
    candidate.photo_url || candidate.photoUrl || candidate.foto_url || candidate.photo?.url || "";
  const name = candidate.ballot_name || candidate.full_name || "candidato";
  if (!source) return `<div class="photo-fallback">Imagem não disponível</div>`;
  return `<img src="${esc(source)}" alt="Foto de ${esc(name)}" loading="lazy" data-photo>`;
}

function candidateCard(candidate, kind, selectedIds) {
  const name = candidate.ballot_name || candidate.full_name || "Nome não disponível";
  const selected = selectedIds.includes(String(candidate.tse_id));
  const limited = !selected && comparisonState(selectedIds).atLimit;
  const compareLabel = selected ? "Remover" : limited ? "Limite de 3" : "Comparar";
  const profileUrl = `candidato.html?id=${encodeURIComponent(candidate.tse_id)}&cargo=${kind}`;

  const documentedTopics = candidateTopicIds(candidate).map(topicById).filter(Boolean);
  const visibleTopics = documentedTopics.slice(0, 3);
  const remaining = Math.max(0, documentedTopics.length - visibleTopics.length);
  const topicTags = visibleTopics.length
    ? `<div class="qv-card-tags" aria-label="Temas com evidência documentada">${visibleTopics
        .map((topic) => `<span class="qv-tag">${esc(topic.label)}</span>`)
        .join("")}${remaining ? `<span class="qv-tag qv-tag--more">+${remaining} tema${remaining === 1 ? "" : "s"}</span>` : ""}</div>`
    : "";

  const proposalCount = topicEvidence(candidate).length;
  const electionsCount = (candidate.previous_elections || []).length;
  const assetsCount = candidate.assets?.count || (candidate.assets?.items || []).length || 0;
  const socialCount = (candidate.social_links || []).length;
  const density = [
    electionsCount
      ? `${electionsCount} eleiç${electionsCount === 1 ? "ão" : "ões"} anterior${electionsCount === 1 ? "" : "es"} documentada${electionsCount === 1 ? "" : "s"}`
      : null,
    assetsCount ? `${assetsCount} ${assetsCount === 1 ? "bem declarado" : "bens declarados"} ao TSE` : null,
    socialCount
      ? `${socialCount} rede${socialCount === 1 ? "" : "s"} ${socialCount === 1 ? "social" : "sociais"} informada${socialCount === 1 ? "" : "s"}`
      : null,
  ].filter(Boolean);

  return `
    <article class="qv-card" data-profile-url="${profileUrl}">
      <a class="qv-card-photo-link" href="${profileUrl}" aria-label="Entender candidatura de ${esc(name)}">
        <div class="qv-card-photo">${photoMarkup(candidate)}</div>
      </a>
      <div class="qv-card-body">
        <p class="qv-card-kicker">${kind === "federal" ? "DEPUTADO FEDERAL" : "DEPUTADO ESTADUAL"}</p>
        <h3><a href="${profileUrl}">${esc(name)}</a></h3>
        <p class="qv-card-electoral">${esc(candidate.party || "Partido não informado")} · nº ${esc(candidate.number || "—")}</p>
        <p class="qv-card-now">${esc(currentActivity(candidate, kind))}</p>
        ${candidate.occupation ? `<p class="qv-card-occupation">${esc(candidate.occupation)}</p>` : ""}
        ${topicTags}
        ${proposalCount ? `<p class="qv-card-meta">${proposalCount} registro${proposalCount === 1 ? "" : "s"} temático${proposalCount === 1 ? "" : "s"} com fonte</p>` : ""}
        ${density.length ? `<p class="qv-card-meta">${density.join(" · ")}</p>` : ""}
      </div>
      <div class="qv-card-actions">
        <a class="qv-card-link" href="${profileUrl}">Entender</a>
        <button class="qv-btn qv-btn--compare${selected ? " selected" : ""}" data-compare-id="${esc(candidate.tse_id)}" type="button" aria-pressed="${selected}" aria-disabled="${limited}"${limited ? " disabled" : ""}>${compareLabel}</button>
      </div>
    </article>`;
}

function renderPagination(total, page, onPage) {
  const mount = $("pagination");
  if (!mount) return;

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages <= 1) {
    mount.innerHTML = "";
    return;
  }

  const visible = [];
  for (let current = 1; current <= pages; current++) {
    if (current === 1 || current === pages || Math.abs(current - page) <= 2) visible.push(current);
  }

  const parts = [`<button type="button" data-page="${page - 1}" ${page === 1 ? "disabled" : ""}>Anterior</button>`];
  let previous = 0;
  visible.forEach((current) => {
    if (previous && current - previous > 1) parts.push('<span aria-hidden="true">…</span>');
    parts.push(
      `<button type="button" data-page="${current}" class="${current === page ? "active" : ""}" ${current === page ? 'aria-current="page"' : ""}>${current}</button>`
    );
    previous = current;
  });
  parts.push(`<button type="button" data-page="${page + 1}" ${page === pages ? "disabled" : ""}>Próxima</button>`);

  mount.innerHTML = parts.join("");
  mount.querySelectorAll("button[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      const next = Number(button.dataset.page);
      if (next >= 1 && next <= pages) onPage(next);
    });
  });
}

function updateCompareTray() {
  const tray = $("compareTray");
  if (!tray) return;

  const ids = getCompareIds();
  const state = comparisonState(ids);
  tray.hidden = !ids.length;
  $("compareCount").textContent = state.message;

  const openCompare = $("openCompare");
  openCompare.textContent = state.canOpen ? "Comparar" : "Escolha mais 1";
  openCompare.setAttribute("aria-disabled", String(!state.canOpen));
  if (state.canOpen) {
    openCompare.href = `comparar.html?ids=${encodeURIComponent(ids.join(","))}`;
    openCompare.removeAttribute("tabindex");
  } else {
    openCompare.removeAttribute("href");
    openCompare.setAttribute("tabindex", "-1");
  }
}

async function initCandidates() {
  const [{ federal, estadual, meta }, topics] = await Promise.all([loadCore(), loadTopics()]);
  setTopics(topics);
  applyGlobalMeta(meta);

  const datasets = { federal, estadual };
  const url = params();
  let kind = url.get("cargo") === "estadual" ? "estadual" : "federal";
  let page = Math.max(1, Number(url.get("page")) || 1);

  $("searchInput").value = url.get("q") || "";
  $("institutionalFilter").value = url.get("institucional") === "1" ? "1" : "";
  $("federalCount").textContent = federal.length;
  $("estadualCount").textContent = estadual.length;
  $("listUpdate").textContent = `Atualizado em ${formatSnapshot(meta?.collected_at)}`;

  function populateTopics() {
    const select = $("topicFilter");
    const requested = url.get("tema") || select.value;
    const availableIds = new Set(datasets[kind].flatMap((c) => candidateTopicIds(c)));
    const topicsForKind = allTopics().filter((topic) => availableIds.has(topic.id));
    select.innerHTML =
      '<option value="">Todos os assuntos com fonte</option>' +
      topicsForKind.map((topic) => `<option value="${esc(topic.id)}">${esc(topic.label)}</option>`).join("");
    select.value = topicsForKind.some((topic) => topic.id === requested) ? requested : "";
  }

  function populateParties() {
    const select = $("partyFilter");
    const requested = url.get("partido") || select.value;
    const parties = [...new Set(datasets[kind].map((item) => item.party).filter(Boolean))].sort();
    select.innerHTML =
      '<option value="">Todos os partidos</option>' +
      parties.map((party) => `<option value="${esc(party)}">${esc(party)}</option>`).join("");
    if (parties.includes(requested)) select.value = requested;
  }

  const filterToggle = $("filterToggle");
  const secondaryFilters = $("secondaryFilters");
  const activeFilterCount = $("activeFilterCount");

  function updateFilterDisclosure() {
    const count = [$("partyFilter").value, $("topicFilter").value, $("institutionalFilter").value].filter(
      Boolean
    ).length;
    activeFilterCount.textContent = count ? `(${count})` : "";
    if (count && secondaryFilters.hidden) {
      secondaryFilters.hidden = false;
      filterToggle.setAttribute("aria-expanded", "true");
    }
  }

  filterToggle?.addEventListener("click", () => {
    secondaryFilters.hidden = !secondaryFilters.hidden;
    filterToggle.setAttribute("aria-expanded", String(!secondaryFilters.hidden));
  });

  function activeFilters() {
    return {
      query: norm($("searchInput").value),
      party: $("partyFilter").value,
      topic: $("topicFilter").value,
      institutional: $("institutionalFilter").value === "1",
    };
  }

  function filteredRows() {
    const filters = activeFilters();
    return datasets[kind]
      .filter((candidate) => {
        const searchable = norm(
          [candidate.ballot_name, candidate.full_name, candidate.number, candidate.party, candidate.occupation].join(" ")
        );
        if (filters.query && !searchable.includes(filters.query)) return false;
        if (filters.party && candidate.party !== filters.party) return false;
        if (filters.topic && !candidateTopicIds(candidate).includes(filters.topic)) return false;
        if (filters.institutional && !hasInstitutional(candidate)) return false;
        return true;
      })
      .sort((a, b) =>
        (a.ballot_name || a.full_name || "").localeCompare(b.ballot_name || b.full_name || "", "pt-BR")
      );
  }

  function syncUrl() {
    const filters = activeFilters();
    updateSearchParams({
      cargo: kind,
      page: String(page),
      q: $("searchInput").value.trim() || null,
      partido: filters.party || null,
      tema: filters.topic || null,
      institucional: filters.institutional ? "1" : null,
    });
  }

  function render() {
    const rows = filteredRows();
    const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
    if (page > pages) page = pages;

    const start = (page - 1) * PAGE_SIZE;
    const visible = rows.slice(start, start + PAGE_SIZE);
    const selected = getCompareIds();

    $("resultCount").textContent = `${rows.length} pessoa${rows.length === 1 ? "" : "s"}`;
    $("pageStatus").textContent = rows.length ? `Página ${page} de ${pages}` : "Nenhum resultado";

    // Ausência de resultado por tema nunca vira "não tem proposta".
    $("cards").innerHTML = visible.length
      ? visible.map((candidate) => candidateCard(candidate, kind, selected)).join("")
      : `<p class="qv-empty">${
          activeFilters().topic
            ? "Ainda não encontramos fala, proposta ou atuação com fonte para este assunto e cargo. Isso não significa que a pessoa não tenha posição."
            : "Ninguém encontrado com esses filtros."
        }</p>`;

    $("cards")
      .querySelectorAll(".qv-card[data-profile-url]")
      .forEach((card) => {
        card.addEventListener("click", (event) => {
          if (!event.target.closest("a,button")) location.href = card.dataset.profileUrl;
        });
      });

    $("cards")
      .querySelectorAll("[data-compare-id]")
      .forEach((button) => {
        button.addEventListener("click", () => {
          toggleCompare(button.dataset.compareId);
          syncComparisonControls(updateCompareTray);
        });
      });

    // Fallback de foto sem handler inline: o app.js montava um onerror como
    // string escapada dentro do HTML gerado.
    $("cards")
      .querySelectorAll("img[data-photo]")
      .forEach((img) => {
        img.addEventListener("error", () => {
          img.outerHTML = '<div class="photo-fallback">Imagem não disponível</div>';
        });
      });

    renderPagination(rows.length, page, (nextPage) => {
      page = nextPage;
      render();
      const head = document.querySelector(".results-head");
      if (head) window.scrollTo({ top: head.offsetTop - 100, behavior: "smooth" });
    });

    updateFilterDisclosure();
    updateCompareTray();
    syncUrl();
  }

  function setKind(nextKind) {
    kind = nextKind;
    page = 1;
    document.querySelectorAll(".office-button").forEach((button) => {
      const active = button.dataset.kind === kind;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });
    populateTopics();
    populateParties();
    render();
  }

  const rerender = () => {
    page = 1;
    render();
  };

  document.querySelectorAll(".office-button").forEach((button) => {
    button.addEventListener("click", () => setKind(button.dataset.kind));
  });

  $("searchInput").addEventListener("input", rerender);
  $("partyFilter").addEventListener("change", rerender);
  $("topicFilter").addEventListener("change", rerender);
  $("institutionalFilter").addEventListener("change", rerender);

  $("clearFilters").addEventListener("click", () => {
    $("searchInput").value = "";
    $("partyFilter").value = "";
    $("topicFilter").value = "";
    $("institutionalFilter").value = "";
    page = 1;
    render();
  });

  $("clearCompare").addEventListener("click", () => {
    setCompareIds([]);
    syncComparisonControls(updateCompareTray);
    announceComparison("Seleção limpa. Escolha pelo menos 2 candidaturas.");
    $("searchInput").focus();
  });

  $("openCompare").addEventListener("click", (event) => {
    if (!comparisonState(getCompareIds()).canOpen) event.preventDefault();
  });

  setupComparisonSync(updateCompareTray);
  populateParties();
  setKind(kind);
}

initCandidates();
