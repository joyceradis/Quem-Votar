import fs from "node:fs/promises";
import path from "node:path";

const ROOT = process.cwd();
const OUT = path.join(ROOT, "data", "generated");
const TSE_BASE = "https://divulgacandcontas.tse.jus.br/divulga/rest/v1";
const CAMARA_BASE = "https://dadosabertos.camara.leg.br/api/v2";
const YEAR = 2026;
const UF = "ES";
const ELECTION_ID = "20322002026";
const CARGOS = {
  federal: { code: 6, label: "DEPUTADO FEDERAL" },
  estadual: { code: 7, label: "DEPUTADO ESTADUAL" }
};
const USER_AGENT = "Quem-Votar-ES/1.0 (+https://github.com/joyceradis/Quem-Votar-)";

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function fetchJson(url, { officialTse = false, retries = 3 } = {}) {
  let last;
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 30000);
      const headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": USER_AGENT
      };
      if (officialTse) {
        headers["Accept-Language"] = "pt-BR,pt;q=0.9";
        headers["Referer"] = "https://divulgacandcontas.tse.jus.br/divulga/";
        headers["Origin"] = "https://divulgacandcontas.tse.jus.br";
      }
      const response = await fetch(url, { headers, signal: controller.signal });
      clearTimeout(timer);
      if (!response.ok) throw new Error(`HTTP ${response.status} em ${url}`);
      return await response.json();
    } catch (error) {
      last = error;
      if (attempt < retries) await sleep(1000 * attempt);
    }
  }
  throw last;
}

function text(value) {
  return value === undefined || value === null ? null : String(value).trim() || null;
}

function isoFromEpoch(value) {
  if (!value) return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return text(value);
  const date = new Date(n);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function normalizeName(value = "") {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9 ]/g, " ")
    .replace(/\b(dr|dra|delegado|delegada|engenheiro|engenheira|capitao|coronel)\b/gi, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toUpperCase();
}

function priorElections(c) {
  const rows = Array.isArray(c.eleicoesAnteriores) ? c.eleicoesAnteriores : [];
  return rows.map(e => ({
    year: e.nrAno ?? null,
    election_id: text(e.idEleicao),
    office: text(e.cargo),
    party: text(e.partido),
    location: text(e.local || e.sgUe),
    ballot_name: text(e.nomeUrna),
    registration_status: text(e.descricaoSituacaoCandidato),
    result: text(e.situacaoTotalizacao),
    official_link: text(e.txLink)
  })).sort((a,b) => Number(b.year || 0) - Number(a.year || 0));
}

function assetSummary(c) {
  const bens = Array.isArray(c.bens) ? c.bens : [];
  const declared = bens
    .map(b => Number(b.valor))
    .filter(Number.isFinite)
    .reduce((a,b) => a + b, 0);
  const officialTotal = Number(c.totalDeBens);
  const total = Number.isFinite(officialTotal) ? officialTotal : declared;
  return {
    count: bens.length,
    total_declared_brl: Number.isFinite(total) ? total : null
  };
}

function normalizeCandidate(c, office) {
  const id = c.id ?? c.sq_CANDIDATO ?? c.sqCandidato ?? null;
  const party = c.partido || {};
  return {
    tse_id: id === null ? null : String(id),
    ballot_name: text(c.nomeUrna || c.nm_URNA),
    full_name: text(c.nomeCompleto || c.nm_CANDIDATO),
    number: c.numero ?? c.nr_CANDIDATO ?? null,
    office,
    uf: text(c.ufCandidatura || c.eleicao?.siglaUF || UF),
    party: text(party.sigla || c.sg_PARTIDO),
    party_name: text(party.nome || c.nm_PARTIDO),
    registration_status: text(c.descricaoSituacao),
    totalization_status: text(c.descricaoTotalizacao),
    education: text(c.grauInstrucao),
    occupation: text(c.ocupacao),
    campaign_spending_limit_1t: c.gastoCampanha1T ?? null,
    assets: assetSummary(c),
    previous_elections: priorElections(c),
    tse_last_update: isoFromEpoch(c.dataUltimaAtualizacao || c.dt_ULTIMA_ATUALIZACAO),
    photo_url: text(c.fotoUrl || c.urlFoto),
    source: {
      type: "official",
      institution: "TSE",
      name: "DivulgaCandContas",
      url: id === null
        ? "https://divulgacandcontas.tse.jus.br/divulga/"
        : `https://divulgacandcontas.tse.jus.br/divulga/#/candidato/${YEAR}/${ELECTION_ID}/${UF}/${id}`
    }
  };
}

async function listTseCandidates(kind) {
  const cargo = CARGOS[kind];
  const url = `${TSE_BASE}/candidatura/listar/${YEAR}/${UF}/${ELECTION_ID}/${cargo.code}/candidatos`;
  const payload = await fetchJson(url, { officialTse: true });
  const candidates = Array.isArray(payload?.candidatos) ? payload.candidatos : [];
  if (!candidates.length) throw new Error(`TSE retornou lista vazia para ${cargo.label}`);
  return { url, rows: candidates.map(c => normalizeCandidate(c, cargo.label)) };
}

function buildIncumbentIndex(incumbents) {
  const map = new Map();
  for (const chamber of ["federal", "estadual"]) {
    for (const p of incumbents[chamber] || []) {
      for (const alias of [p.name, ...(p.aliases || [])]) {
        map.set(normalizeName(alias), { ...p, chamber });
      }
    }
  }
  return map;
}

async function enrichIncumbentCandidate(candidate, rawListCandidate, incumbentIndex) {
  const match = incumbentIndex.get(normalizeName(candidate.ballot_name))
    || incumbentIndex.get(normalizeName(candidate.full_name));
  if (!match || !candidate.tse_id) return { ...candidate, current_mandate: match || null };

  try {
    await sleep(250);
    const url = `${TSE_BASE}/candidatura/buscar/${YEAR}/${UF}/${ELECTION_ID}/candidato/${candidate.tse_id}`;
    const detail = await fetchJson(url, { officialTse: true, retries: 2 });
    const normalized = normalizeCandidate(detail, candidate.office);
    return {
      ...candidate,
      ...normalized,
      current_mandate: match,
      source: candidate.source
    };
  } catch {
    return { ...candidate, current_mandate: match };
  }
}

async function chamberFederalHistory() {
  const listUrl = `${CAMARA_BASE}/deputados?siglaUf=ES&ordem=ASC&ordenarPor=nome&itens=100`;
  const payload = await fetchJson(listUrl);
  const deputies = Array.isArray(payload?.dados) ? payload.dados : [];

  const output = [];
  for (const d of deputies) {
    const row = {
      chamber_id: d.id,
      name: text(d.nome),
      party: text(d.siglaPartido),
      uf: text(d.siglaUf),
      photo_url: text(d.urlFoto),
      source_url: text(d.uri),
      details: null,
      historical_statuses: [],
      external_mandates: []
    };
    try {
      const [detail, history, external] = await Promise.all([
        fetchJson(`${CAMARA_BASE}/deputados/${d.id}`, { retries: 2 }),
        fetchJson(`${CAMARA_BASE}/deputados/${d.id}/historico`, { retries: 2 }).catch(() => ({dados:[]})),
        fetchJson(`${CAMARA_BASE}/deputados/${d.id}/mandatosExternos`, { retries: 2 }).catch(() => ({dados:[]}))
      ]);
      const x = detail?.dados || {};
      const s = x.ultimoStatus || {};
      row.details = {
        parliamentary_name: text(s.nomeEleitoral || x.nomeCivil),
        condition: text(s.condicaoEleitoral),
        status: text(s.situacao),
        party: text(s.siglaPartido),
        legislature_id: s.idLegislatura ?? null,
        office_email: text(s.email)
      };
      row.historical_statuses = (history?.dados || []).map(h => ({
        legislature_id: h.idLegislatura ?? null,
        party: text(h.siglaPartido),
        condition: text(h.condicaoEleitoral),
        status: text(h.situacao),
        status_date: text(h.data)
      }));
      row.external_mandates = (external?.dados || []).map(m => ({
        office: text(m.cargo),
        uf: text(m.uf),
        municipality: text(m.municipio),
        party: text(m.siglaPartido),
        start_year: m.anoInicio ?? null,
        end_year: m.anoFim ?? null
      }));
    } catch {
      // Mantém a linha básica da fonte oficial sem inventar dados.
    }
    output.push(row);
  }
  return { url: listUrl, rows: output };
}

async function main() {
  await fs.mkdir(OUT, { recursive: true });
  const incumbents = JSON.parse(await fs.readFile(path.join(ROOT, "data", "incumbents.json"), "utf8"));
  const incumbentIndex = buildIncumbentIndex(incumbents);

  const [federalList, stateList, chamber] = await Promise.all([
    listTseCandidates("federal"),
    listTseCandidates("estadual"),
    chamberFederalHistory()
  ]);

  const federal = [];
  for (const candidate of federalList.rows) {
    federal.push(await enrichIncumbentCandidate(candidate, null, incumbentIndex));
  }

  const estadual = [];
  for (const candidate of stateList.rows) {
    estadual.push(await enrichIncumbentCandidate(candidate, null, incumbentIndex));
  }

  const sortByName = (a,b) => (a.ballot_name || a.full_name || "").localeCompare(
    b.ballot_name || b.full_name || "", "pt-BR"
  );
  federal.sort(sortByName);
  estadual.sort(sortByName);

  const collectedAt = new Date().toISOString();
  await Promise.all([
    fs.writeFile(path.join(OUT, "candidates-federal.json"), JSON.stringify(federal, null, 2)),
    fs.writeFile(path.join(OUT, "candidates-estadual.json"), JSON.stringify(estadual, null, 2)),
    fs.writeFile(path.join(OUT, "federal-chamber.json"), JSON.stringify(chamber.rows, null, 2)),
    fs.writeFile(path.join(OUT, "meta.json"), JSON.stringify({
      collected_at: collectedAt,
      uf: UF,
      election_year: YEAR,
      election_id: ELECTION_ID,
      counts: { federal: federal.length, estadual: estadual.length },
      sources: {
        tse_federal: federalList.url,
        tse_estadual: stateList.url,
        camara_federal: chamber.url,
        tse_open_data: "https://dadosabertos.tse.jus.br/dataset/candidatos-2026"
      },
      normalizer_version: "1.0.0"
    }, null, 2))
  ]);

  console.log(`Sincronização concluída: ${federal.length} federais, ${estadual.length} estaduais.`);
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
