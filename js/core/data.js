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

// Cargos majoritários (#161/#186/#193): mesmos 4 cargos do OFFICE_REGISTRY
// em scripts/sync-data.py, na mesma ordem. Deputado Federal/Estadual
// continuam o contrato obrigatório (baseline V5/V5.5); Governador/Senador
// são a extensão do 1º turno autorizada pela #186 — se o arquivo de um
// deles falhar ao carregar, a lista fica vazia (fail-closed do próprio
// getJSON), nunca quebra a página nem promove dado indevido.
export const OFFICES = [
  { kind: "federal", label: "Deputado Federal" },
  { kind: "estadual", label: "Deputado Estadual" },
  { kind: "governador", label: "Governador" },
  { kind: "senador", label: "Senador" },
];

export const DATA = {
  federal: "data/generated/candidates-federal.json",
  estadual: "data/generated/candidates-estadual.json",
  governador: "data/generated/candidates-governador.json",
  senador: "data/generated/candidates-senador.json",
  meta: "data/generated/meta.json",
  chamber: "data/generated/federal-chamber.json",
  topics: "data/reference/policy-topics.json",
};

export function officeLabel(kind) {
  return OFFICES.find((office) => office.kind === kind)?.label || "Cargo não identificado";
}

export async function getJSON(path, fallback = []) {
  try {
    const response = await fetch(`${path}?v=${assetVersion()}`, { cache: "no-store" });
    return response.ok ? await response.json() : fallback;
  } catch {
    return fallback;
  }
}

// loadCore/applyGlobalMeta — portados literalmente de app.js:119-150, agora
// generalizados para os 4 cargos do registry (#193).
export async function loadCore() {
  const byKind = Object.fromEntries(
    await Promise.all(OFFICES.map(async ({ kind }) => [kind, await getJSON(DATA[kind])]))
  );
  const meta = await getJSON(DATA.meta, {});

  const { federal, estadual, governador, senador } = byKind;

  // Deputado Federal/Estadual continuam o par obrigatório para a
  // comparação: é o baseline vigente (AGENTS.md §6) e o que o audit-site.py
  // já exige presente em todo snapshot. Governador/Senador entram na
  // comparação assim que carregarem, sem bloquear os dois obrigatórios.
  if (federal.length && estadual.length) {
    setValidCompareIds(
      OFFICES.flatMap(({ kind }) => byKind[kind]).map((item) => String(item.tse_id))
    );
    setCompareIds(getCompareIds());
  }

  return {
    federal,
    estadual,
    governador,
    senador,
    meta,
    comparisonReady: Boolean(federal.length && estadual.length),
    all: OFFICES.flatMap(({ kind }) => byKind[kind].map((item) => ({ ...item, _kind: kind }))),
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
