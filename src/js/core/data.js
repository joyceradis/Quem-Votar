// Camada de dados — baseada em app.js:1-31 (getJSON/DATA), mas com uma
// única fonte de cache-busting em vez de literais "?v=..." espalhados em
// cada HTML e dentro do próprio app.js (ver src/_data/version.js e
// docs/REBUILD_V6.md). Comportamento de fetch idêntico ao original:
// GET sem cache do navegador, fallback silencioso em caso de erro/HTTP não-ok.

function assetVersion() {
  return document.querySelector('meta[name="qv-asset-version"]')?.content || "dev";
}

export const DATA = {
  federal: "data/generated/candidates-federal.json",
  estadual: "data/generated/candidates-estadual.json",
  meta: "data/generated/meta.json",
  chamber: "data/generated/federal-chamber.json",
  topics: "data/reference/policy-topics.json",
};

export async function getJSON(path, fallback = []) {
  try {
    const response = await fetch(`${path}?v=${assetVersion()}`, { cache: "no-store" });
    return response.ok ? await response.json() : fallback;
  } catch {
    return fallback;
  }
}
