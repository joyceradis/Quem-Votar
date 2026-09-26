// Camada de dados — baseada em app.js:1-31 (getJSON/DATA), mas com uma
// única fonte de cache-busting em vez de literais "?v=..." espalhados em
// cada HTML e dentro do próprio app.js (ver src/_data/version.js e
// docs/REBUILD_V6.md). Comportamento de fetch idêntico ao original:
// GET sem cache do navegador, fallback silencioso em caso de erro/HTTP não-ok.

import { formatSnapshot } from "./format.js";
import { setValidCompareIds, setCompareIds, getCompareIds } from "./compare-state.js";

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

// loadCore/applyGlobalMeta — portados literalmente de app.js:119-150.
export async function loadCore() {
  const [federal, estadual, meta] = await Promise.all([
    getJSON(DATA.federal),
    getJSON(DATA.estadual),
    getJSON(DATA.meta, {}),
  ]);

  if (federal.length && estadual.length) {
    setValidCompareIds([...federal, ...estadual].map((item) => String(item.tse_id)));
    setCompareIds(getCompareIds());
  }

  return {
    federal,
    estadual,
    meta,
    comparisonReady: Boolean(federal.length && estadual.length),
    all: [
      ...federal.map((item) => ({ ...item, _kind: "federal" })),
      ...estadual.map((item) => ({ ...item, _kind: "estadual" })),
    ],
  };
}

// A data e a fonte vêm sempre do snapshot — o site nunca hardcoda contagem
// nem data (README, "Snapshot eleitoral").
export function applyGlobalMeta(meta) {
  const stamp = formatSnapshot(meta?.collected_at);
  document.querySelectorAll("[data-snapshot-date]").forEach((node) => {
    node.textContent = stamp;
  });

  const source = meta?.sources?.primary_tse_dataset;
  if (source) {
    document.querySelectorAll("[data-tse-source]").forEach((link) => {
      link.href = source;
    });
  }
}
