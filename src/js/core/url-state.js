// Estado em URL — novo módulo. Substitui as duas implementações
// praticamente idênticas de "pegar a URL atual, ajustar searchParams,
// history.replaceState" que existiam separadamente em initCandidates
// (app.js:539-553) e initCompare (app.js:919-923), e a construção manual de
// URL de compartilhamento em initProfile (app.js:769-773). Mesma semântica
// de parâmetros (cargo, q, partido, tema, institucional, page, id, ids) —
// só deixa de estar duplicada.

// Aplica um patch de parâmetros na URL atual sem navegar (sem recarregar a
// página). value === null | undefined | "" remove o parâmetro.
export function updateSearchParams(patch) {
  const next = new URL(location.href);
  for (const [key, value] of Object.entries(patch)) {
    if (value === null || value === undefined || value === "") {
      next.searchParams.delete(key);
    } else {
      next.searchParams.set(key, String(value));
    }
  }
  history.replaceState(null, "", next);
  return next;
}

// Constrói uma URL (para compartilhamento/OG/canonical) sem tocar o
// histórico do navegador. `path` ausente reaproveita a URL atual.
export function buildUrl(path, params = {}) {
  const url = path ? new URL(path, location.href) : new URL(location.href);
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") {
      url.searchParams.delete(key);
    } else {
      url.searchParams.set(key, String(value));
    }
  }
  return url;
}
