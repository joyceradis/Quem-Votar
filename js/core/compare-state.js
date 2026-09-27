// Estado da comparação — portado literalmente de app.js:236-316.
// É a máquina de estado que já estava correta e testada
// (tests/test_comparison_funnel.py): teto de 3, validação contra o dataset
// vivo, sincronização entre abas via storage/pageshow/focus.
import { $ } from "./dom.js";

let validCompareIds = null;

export function setValidCompareIds(ids) {
  validCompareIds = ids;
}

export function announceComparison(message) {
  const status = $("compareStatus");
  if (status) status.textContent = message;
}

export function normalizeCompareIds(ids, validIds = null) {
  if (!Array.isArray(ids)) return [];
  const allowed = validIds ? new Set(validIds.map(String)) : null;
  return [...new Set(ids.map(String))].filter((id) => !allowed || allowed.has(id)).slice(0, 3);
}

export function getCompareIds() {
  try {
    return normalizeCompareIds(JSON.parse(localStorage.getItem("qv_compare") || "[]"), validCompareIds);
  } catch {
    return [];
  }
}

export function setCompareIds(ids) {
  localStorage.setItem("qv_compare", JSON.stringify(normalizeCompareIds(ids, validCompareIds)));
}

export function comparisonState(ids) {
  const count = normalizeCompareIds(ids).length;
  return {
    count,
    canOpen: count >= 2,
    atLimit: count === 3,
    message:
      count === 1 ? "Escolha mais 1 pessoa" : count === 3 ? "Limite de 3 atingido" : `${count} selecionados`,
  };
}

export function toggleCompare(id) {
  const key = String(id);
  const ids = getCompareIds();
  const index = ids.indexOf(key);

  if (validCompareIds && !validCompareIds.includes(key)) return ids;
  if (index >= 0) {
    ids.splice(index, 1);
    announceComparison("Candidatura removida. " + comparisonState(ids).message);
  } else if (ids.length < 3) {
    ids.push(key);
    announceComparison("Candidatura adicionada. " + comparisonState(ids).message);
  } else {
    announceComparison("Limite de 3 atingido. Remova uma candidatura para escolher outra.");
  }

  setCompareIds(ids);
  return ids;
}

export function syncComparisonControls(updateTray) {
  const ids = getCompareIds();
  document.querySelectorAll("[data-compare-id],#profileCompare").forEach((button) => {
    const selected = ids.includes(String(button.dataset.compareId || button.dataset.candidateId));
    const limited = !selected && comparisonState(ids).atLimit;
    button.disabled = limited;
    button.setAttribute("aria-pressed", String(selected));
    button.setAttribute("aria-disabled", String(limited));
    button.classList.toggle("selected", selected);
    button.textContent = selected
      ? button.id === "profileCompare"
        ? "Remover da comparação"
        : "Remover"
      : limited
        ? button.id === "profileCompare"
          ? "Limite de 3 atingido"
          : "Limite de 3"
        : "Comparar";
  });
  if (typeof updateTray === "function") updateTray();
}

export function setupComparisonSync(updateTray) {
  const sync = () => syncComparisonControls(updateTray);
  window.addEventListener("storage", (event) => {
    if (event.key !== "qv_compare" && event.key !== null) return;
    sync();
    announceComparison("Seleção atualizada. " + comparisonState(getCompareIds()).message);
  });
  window.addEventListener("pageshow", sync);
  window.addEventListener("focus", sync);
}
