// Regras editoriais de evidência — portado literalmente de app.js:25-94.
//
// Este módulo é a tradução em código do `AGENTS.md` §2/§5 e do
// `docs/GOVERNANCE.md`: um tema só existe para uma candidatura quando há
// evidência individualizada documentada; ocupação declarada ao TSE é
// metadado e nunca gera tema; ausência de evidência é ausência de dado, não
// ausência de proposta. Não reescrever sem passar pela governança.
import { getJSON, DATA } from "./data.js";

let TOPICS = { version: "0", topics: [] };

export async function loadTopics() {
  if (TOPICS.topics.length) return TOPICS;
  TOPICS = await getJSON(DATA.topics, { version: "0", topics: [] });
  return TOPICS;
}

export function setTopics(topics) {
  TOPICS = topics;
}

export function allTopics() {
  return TOPICS.topics;
}

export function topicById(id) {
  return TOPICS.topics.find((topic) => topic.id === id) || null;
}

export function topicEvidence(candidate) {
  return Array.isArray(candidate?.topic_evidence) ? candidate.topic_evidence : [];
}

export function candidateTopicIds(candidate) {
  return [...new Set(topicEvidence(candidate).map((item) => item.topic_id).filter(Boolean))];
}

export function normalizedEvidenceType(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

export function isProspectiveEvidence(item) {
  const type = normalizedEvidenceType(item?.evidence_type);
  return type === "proposta" || type === "declaracao";
}

export function prospectiveTopicEvidence(candidate) {
  return topicEvidence(candidate).filter(isProspectiveEvidence);
}

export function documentedActionEvidence(candidate) {
  return topicEvidence(candidate).filter(
    (item) => normalizedEvidenceType(item?.evidence_type) === "atuacao"
  );
}

export function hasInstitutionalHistoryRecord(candidate) {
  const record = candidate?.institutional_history;
  return Boolean(record && ((record.history || []).length || (record.external_mandates || []).length));
}

export function hasInstitutional(candidate) {
  return Boolean(candidate?.current_mandate || hasInstitutionalHistoryRecord(candidate));
}

// Nunca lê candidate.occupation: ocupação declarada ao TSE é metadado, não
// atuação atual (contrato fixado pela #127/#128).
export function currentActivity(candidate, kind) {
  if (candidate?.current_mandate) {
    return kind === "federal" ? "Deputado federal em exercício" : "Mandato atual confirmado";
  }
  return "Atuação atual ainda não confirmada nesta base";
}

export function practicalAreasFromEvidence(evidence) {
  const ids = [...new Set((evidence || []).map((item) => item.topic_id).filter(Boolean))];
  return ids.map((id) => topicById(id)).filter(Boolean);
}

export function practicalAreas(candidate) {
  return practicalAreasFromEvidence(topicEvidence(candidate));
}

export function evidenceTypeLabel(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "proposta") return "Proposta";
  if (normalized === "declaração" || normalized === "declaracao") return "Declaração";
  if (normalized === "atuação" || normalized === "atuacao") return "Atuação pública";
  return "Registro documentado";
}
