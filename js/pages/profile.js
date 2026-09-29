// Ficha do candidato — portado de initProfile (app.js:710-902).
//
// Mesma ordem normativa fixada pela #127/#128 e verificada pelo
// audit-site.py: IDENTIDADE → HOJE → PROPÕE → IMPACTO → HISTÓRICO →
// DADOS ELEITORAIS → FONTES. O conteúdo é idêntico; a diferença é que a
// template string única de ~190 linhas virou uma função de render por
// seção.
//
// Regras editoriais que este arquivo não pode afrouxar (AGENTS.md §2/§5):
// - PROPÕE aceita só evidence_type proposta|declaração; atuação documentada
//   vai para HISTÓRICO, nunca para PROPÕE ou IMPACTO;
// - ocupação declarada ao TSE nunca vira atuação institucional verificada
//   (mandato em exercício continua o único sinal de "faz hoje" confirmado);
//   sem mandato, ela aparece em HOJE como fato autodeclarado e fonteado,
//   nunca como "não há dados" quando o dado existe;
// - ausência de evidência é dita como ausência de registro, nunca como
//   ausência de proposta ou posição;
// - IMPACTO descreve áreas relacionadas ao tema, sem afirmar benefício,
//   prejuízo ou efeito individual.
import { $, esc, norm, params } from "../core/dom.js";
import { loadCore, getJSON, DATA, applyGlobalMeta, officeLabel } from "../core/data.js";
import { formatBRL, formatSnapshot } from "../core/format.js";
import { buildUrl } from "../core/url-state.js";
import { setupNavigation } from "../core/a11y.js";
import {
  loadTopics,
  setTopics,
  topicById,
  topicEvidence,
  prospectiveTopicEvidence,
  documentedActionEvidence,
  practicalAreasFromEvidence,
  currentActivity,
  evidenceTypeLabel,
} from "../core/evidence.js";
import {
  getCompareIds,
  comparisonState,
  toggleCompare,
  syncComparisonControls,
  setupComparisonSync,
} from "../core/compare-state.js";

setupNavigation();

// A sentinela do TSE nunca é traduzida em conclusão jurídica (#91/PR #92).
function registrationStatusLabel(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized || normalized === "not_available") return "Ainda não disponível na fonte atual";
  return value;
}

function photoMarkup(candidate) {
  const source =
    candidate.photo_url || candidate.photoUrl || candidate.foto_url || candidate.photo?.url || "";
  const name = candidate.ballot_name || candidate.full_name || "candidato";
  if (!source) return `<div class="profile-photo profile-fallback">Imagem não disponível</div>`;
  return `<img class="profile-photo" src="${esc(source)}" alt="Foto de ${esc(name)}" loading="eager" data-photo>`;
}

function evidenceMetaLine(item) {
  return [evidenceTypeLabel(item.evidence_type), item.source_publisher, item.published_at]
    .filter(Boolean)
    .join(" · ");
}

function sourceLink(item) {
  return item.source_url
    ? `<a target="_blank" rel="noopener" href="${esc(item.source_url)}">Abrir fonte</a>`
    : "";
}

function renderHero(candidate, kind, name, socialName, currentActivityText) {
  const ids = getCompareIds();
  const selected = ids.includes(String(candidate.tse_id));
  const limited = !selected && comparisonState(ids).atLimit;
  const label = selected ? "Remover da comparação" : limited ? "Limite de 3 atingido" : "Comparar";

  return `
    <a class="back-link" href="candidatos.html?cargo=${kind}">Voltar para candidatos</a>
    <section class="profile-hero">
      <div class="profile-photo-wrap">${photoMarkup(candidate)}</div>
      <div class="profile-copy">
        <p class="qv-eyebrow">${esc(officeLabel(kind))} · Espírito Santo</p>
        <h1>${esc(name)}</h1>
        <p class="full-name">${esc(candidate.full_name || "")}</p>
        ${socialName ? `<p class="social-name">Nome social: ${esc(socialName)}</p>` : ""}
        <p class="identity-line"><strong>${esc(candidate.party || "Partido não informado")}</strong> <span>nº ${esc(candidate.number || "—")}</span></p>
        <p class="profile-now">${esc(currentActivityText)}</p>
        <div class="profile-actions">
          <button id="profileCompare" class="qv-btn qv-btn--primary" type="button" data-candidate-id="${esc(candidate.tse_id)}" aria-pressed="${selected}" aria-disabled="${limited}"${limited ? " disabled" : ""}>${label}</button>
          <button id="profileShare" class="qv-btn" type="button">Compartilhar ficha</button>
        </div>
      </div>
    </section>`;
}

// "Outros" é o código genérico do TSE para ocupação (nº 956): não descreve
// nada, então exibi-lo como fato de HOJE seria pior que a ausência honesta.
const GENERIC_OCCUPATIONS = new Set(["OUTROS", "OUTRO"]);

function isUsableOccupation(occupation) {
  return Boolean(occupation) && !GENERIC_OCCUPATIONS.has(norm(occupation));
}

// 01 — HOJE. Mandato em exercício é o único sinal de atuação institucional
// verificada e, quando existe, é o que aparece aqui. Sem mandato confirmado,
// mostramos a ocupação que a própria candidatura declarou ao TSE — como fato
// autodeclarado e fonteado, não como atuação verificada — em vez de dizer
// "sem dados" quando o dado existe (AGENTS.md §4: fonte, tipo e ausência
// tratados de forma explícita). Ocupações genéricas (ex.: "Outros") não
// contam como dado utilizável, pois não descrevem o que a pessoa faz.
function renderToday(institutional, currentActivityText, occupation, occupationSourceUrl) {
  if (!institutional) {
    if (!isUsableOccupation(occupation)) {
      return `<div class="plain-empty">
        <strong>Sem atuação pública atual confirmada nesta base.</strong>
        <p>Isso não significa ausência de atuação.</p>
      </div>`;
    }
    return `<div class="plain-fact">
      <span>Hoje</span>
      <strong>${esc(occupation)}</strong>
      <small>Autodeclarado no registro de candidatura ao TSE; sem confirmação de atuação institucional nesta base.</small>
      ${occupationSourceUrl ? `<a target="_blank" rel="noopener" href="${esc(occupationSourceUrl)}">Abrir fonte</a>` : ""}
    </div>`;
  }
  const detail = [institutional.party, institutional.status].filter(Boolean).join(" · ");
  return `
    <div class="plain-fact">
      <span>Hoje</span>
      <strong>${esc(currentActivityText)}</strong>
      <small>${esc(detail)}</small>
    </div>`;
}

// 02 — PROPÕE. Apenas proposta|declaração.
function renderProposes(prospective) {
  if (!prospective.length) {
    return `
      <div class="plain-empty">
        <strong>Nenhuma proposta ou declaração documentada nesta base ainda.</strong>
        <p>Sem registro não é o mesmo que sem proposta.</p>
      </div>`;
  }
  return `<div class="promise-list">${prospective
    .map((item) => {
      const topic = topicById(item.topic_id);
      return `
        <article class="evidence-item">
          <span>${esc(topic?.label || item.topic_id || "Assunto")}</span>
          <h3>${esc(item.statement || item.quote_or_summary || "Registro documentado sem resumo disponível.")}</h3>
          <p class="evidence-meta">${esc(evidenceMetaLine(item))}</p>
          ${sourceLink(item)}
        </article>`;
    })
    .join("")}</div>`;
}

// 03 — IMPACTO. Áreas relacionadas ao tema documentado; nunca previsão de
// benefício, prejuízo ou efeito individual.
function renderImpact(prospective, impactTopics) {
  if (!prospective.length) {
    return `<div class="plain-empty"><strong>Ainda não há registros suficientes nesta ficha para relacionar áreas da vida pública.</strong></div>`;
  }
  if (!impactTopics.length) {
    return `<div class="plain-empty"><strong>Há proposta ou declaração registrada, mas ainda não há áreas relacionadas nesta base.</strong></div>`;
  }
  return `
    <div class="impact-list">${impactTopics
      .map(
        (topic) => `
          <article>
            <h3>${esc(topic.label)}</h3>
            <p class="impact-context">Áreas relacionadas a este tema documentado</p>
            <ul class="life-areas">${(topic.life_areas || [])
              .map((area) => `<li>${esc(area)}</li>`)
              .join("")}</ul>
          </article>`
      )
      .join("")}</div>
    <p class="impact-note"><strong>Áreas relacionadas às propostas e declarações documentadas nesta ficha.</strong> Essas áreas vêm da taxonomia pública do tema e não são previsão de benefício, prejuízo ou efeito individual.</p>`;
}

// Ausência de fonte (16 candidatos de Governador/Senador cujo enriquecimento
// ainda não foi integrado, ver meta.json not_available_for) não pode
// aparecer como "não possui" (AGENTS.md §2/§5) — mesmo texto e mesmo critério
// já usados por compare.js para os campos assets/social_links/previous_elections.
const NAO_DISPONIVEL = "Ainda não disponível na fonte atual";
function hasGap(candidate, field) {
  return (candidate.enrichment_gaps || []).includes(field);
}

// reference_date de institutional_evidence é uma data de calendário
// ("2025-04-01"), não um instante — formatSnapshot() mostra hora:minuto e
// sugeriria precisão que a fonte não tem.
function formatReferenceDate(isoDate) {
  if (!isoDate) return null;
  try {
    return new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(isoDate));
  } catch {
    return isoDate;
  }
}

// institutional_evidence (S1, Authorization-Issue #2/#160): vínculo
// institucional datado (hoje só ALES) com fonte, tipo e aviso metodológico —
// nunca "faz hoje" (isso é current_mandate), sempre Histórico. O aviso do
// próprio registro ("não prova isoladamente exercício de mandato em X") é
// preservado literalmente, nunca resumido ou omitido.
function renderInstitutionalEvidence(records) {
  if (!records.length) return "";
  return `<div class="institutional-evidence">
      <h3>Vínculo institucional registrado</h3>
      <div class="public-records">${records
        .map(
          (item) => `
            <article>
              <span>${esc(item.institution || "Instituição")}${item.legislature ? ` · ${esc(item.legislature)}` : ""}</span>
              <strong>${esc(item.type || "Registro institucional documentado")}</strong>
              <p>${esc(formatReferenceDate(item.reference_date) || "Data não disponível")}</p>
              ${item.warning ? `<p class="evidence-warning">${esc(item.warning)}</p>` : ""}
              ${item.source?.url ? `<a target="_blank" rel="noopener" href="${esc(item.source.url)}">${esc(item.source.document || item.source.institution || "Abrir fonte")}</a>` : ""}
            </article>`
        )
        .join("")}</div>
    </div>`;
}

// institutional_history (S1): trajetória partidária/legislativa e mandatos
// externos já coletados da Câmara, hoje usados só como fonte (collectSources)
// — aqui viram conteúdo legível, sempre em Histórico. Entradas sem
// condition/status (mudança de filiação sem marco de mandato) são omitidas
// por ruído, não por descarte de dado: o registro completo continua citável
// via profile_url em Fontes.
function renderInstitutionalTrack(history) {
  if (!history) return "";
  const track = (history.history || []).filter((item) => item.condition || item.status);
  const external = history.external_mandates || [];
  if (!track.length && !external.length) return "";

  const trackList = track.length
    ? `<ul class="institutional-track-list">${track
        .map(
          (item) => `
            <li>Legislatura ${esc(item.legislature_id ?? "?")} · ${esc(item.party || "Partido não informado")} · ${esc([item.condition, item.status].filter(Boolean).join(" — "))}</li>`
        )
        .join("")}</ul>`
    : "";

  const externalList = external.length
    ? `<ul class="institutional-track-list">${external
        .map(
          (item) => `
            <li>${esc(item.office || "Cargo")}${item.start_year || item.end_year ? ` · ${esc([item.start_year, item.end_year].filter(Boolean).join("–"))}` : ""}${item.party ? ` · ${esc(item.party)}` : ""}</li>`
        )
        .join("")}</ul>`
    : "";

  return `<div class="institutional-track">
      <h3>Trajetória institucional na Câmara</h3>
      ${trackList}
      ${external.length ? `<h4>Outros mandatos</h4>${externalList}` : ""}
    </div>`;
}

// 04 — HISTÓRICO. Recebe também a atuação documentada, que nunca sobe para
// PROPÕE/IMPACTO.
function renderHistory(historyItems, actionEvidence, candidate) {
  const electoral = historyItems.length
    ? `<div class="timeline-list">${historyItems
        .map(
          (item) => `
            <div class="timeline-item">
              <strong>${esc(item.year || "Data não disponível")}</strong>
              <div>${esc(item.office || "Cargo")}<small>${esc([item.party, item.location, item.result].filter(Boolean).join(" · "))}</small></div>
            </div>`
        )
        .join("")}</div>`
    : "";

  const actions = actionEvidence.length
    ? `<div class="documented-actions">
        <h3>Atuação pública documentada</h3>
        <div class="public-records">${actionEvidence
          .map((item) => {
            const topic = topicById(item.topic_id);
            return `
              <article>
                <span>${esc(topic?.label || item.topic_id || "Assunto")}</span>
                <strong>${esc(item.statement || item.quote_or_summary || "Registro documentado sem resumo disponível.")}</strong>
                <p>${esc(evidenceMetaLine(item))}</p>
                ${sourceLink(item)}
              </article>`;
          })
          .join("")}</div>
      </div>`
    : "";

  const institutionalEvidence = renderInstitutionalEvidence(candidate.institutional_evidence || []);
  const institutionalTrack = renderInstitutionalTrack(candidate.institutional_history);

  if (!electoral && !actions && !institutionalEvidence && !institutionalTrack) {
    return hasGap(candidate, "previous_elections")
      ? `<p class="plain-empty">Histórico eleitoral: ${esc(NAO_DISPONIVEL)}.</p>`
      : `<p class="plain-empty">Sem histórico eleitoral ou atuação pública documentada nesta base ainda.</p>`;
  }
  return `${electoral}${actions}${institutionalTrack}${institutionalEvidence}`;
}

// Vice (Governador) e suplentes (Senador) — #186 item 4. É fato do próprio
// cadastro do titular (quem vota nele elege a chapa inteira), não avaliação:
// entra como linha a mais em "Dados eleitorais do TSE", nunca em comparação
// ou destaque próprio. Ambiguidade na fonte (AGENTS.md §3) é dita como tal —
// as duas versões lado a lado, sem escolher uma.
const RUNNING_MATE_LABELS = {
  "VICE-GOVERNADOR": "Vice",
  "1º SUPLENTE": "1º suplente",
  "2º SUPLENTE": "2º suplente",
};

function runningMateFacts(candidate) {
  const slots = candidate.running_mate
    ? [candidate.running_mate]
    : candidate.substitutes
      ? Object.values(candidate.substitutes)
      : [];

  return slots.map((slot) => {
    const label = RUNNING_MATE_LABELS[slot?.role] || slot?.role || "Chapa";
    if (slot?.status === "linked") {
      return {
        label,
        value: [slot.ballot_name, slot.party].filter(Boolean).join(" · ") || slot.full_name,
      };
    }
    if (slot?.status === "ambiguous_source") {
      const names = (slot.candidates || [])
        .map((c) => [c.ballot_name, c.party].filter(Boolean).join(" · "))
        .filter(Boolean);
      return {
        label,
        value: "Mais de um registro do TSE para este número de urna nesta função",
        note: `Nenhum foi escolhido — ambos ficam documentados${names.length ? `: ${names.join("; ")}` : ""}.`,
      };
    }
    return { label, value: NAO_DISPONIVEL };
  });
}

// 05 — DADOS ELEITORAIS: cadastro, bens declarados e redes informadas.
function renderElectoralData(candidate, assets) {
  const organization =
    candidate.coalition && norm(candidate.coalition) !== "PARTIDO ISOLADO"
      ? candidate.coalition_composition || candidate.coalition
      : candidate.coalition
        ? "Partido isolado"
        : null;

  const facts = [
    {
      label: "Partido",
      value: candidate.party_name
        ? [candidate.party, candidate.party_name].filter(Boolean).join(" · ")
        : candidate.party,
    },
    { label: "Federação / composição", value: organization },
    { label: "Escolaridade", value: candidate.education },
    {
      label: "Ocupação declarada",
      value: candidate.occupation,
      note: candidate.occupation
        ? "Autodeclarada no registro de candidatura ao TSE; não confirma atuação atual."
        : null,
    },
    { label: "Situação da candidatura", value: registrationStatusLabel(candidate.registration_status) },
    { label: "Situação de totalização", value: candidate.totalization_status },
    ...runningMateFacts(candidate),
  ].filter((item) => item.value);

  const factsBlock = facts.length
    ? `<div class="electoral-data" aria-label="Dados eleitorais do TSE">
        <div class="electoral-data-head">
          <strong>Dados eleitorais do TSE</strong>
          <span>Cadastro de candidaturas · 2026</span>
        </div>
        <dl class="electoral-data-grid">${facts
          .map(
            (item) =>
              `<div class="electoral-data-item"><dt>${esc(item.label)}</dt><dd>${esc(item.value)}${item.note ? `<small>${esc(item.note)}</small>` : ""}</dd></div>`
          )
          .join("")}</dl>
      </div>`
    : "";

  const assetsCount = assets?.count || (assets?.items || []).length || 0;
  const assetsTotal = formatBRL(assets?.total_declared_brl);
  const assetsBlock = assetsCount
    ? `<div class="declared-assets" aria-label="Bens declarados ao TSE">
        <div class="declared-assets-head">
          <strong>Bens declarados ao TSE</strong>
          <span>${esc(assets?.source?.dataset || "Bens de candidatos")}</span>
        </div>
        <p class="declared-assets-total">${assetsCount} ${assetsCount === 1 ? "bem declarado" : "bens declarados"} ao TSE${assetsTotal ? ` · valor total declarado ao TSE: ${esc(assetsTotal)}` : ""}</p>
        <details class="assets-breakdown"><summary>Ver bens e valores declarados</summary>
        <ul class="declared-assets-list">${(assets.items || [])
          .map(
            (item) =>
              `<li><span>${esc(item.description || item.type || "Bem declarado")}</span>${formatBRL(item.value_brl) ? `<strong>${esc(formatBRL(item.value_brl))}</strong>` : ""}</li>`
          )
          .join("")}</ul></details>
        ${assets?.source?.official_candidate_url ? `<a class="declared-assets-source" target="_blank" rel="noopener" href="${esc(assets.source.official_candidate_url)}">Abrir declaração de bens</a>` : ""}
      </div>`
    : hasGap(candidate, "assets")
      ? `<p class="plain-empty">Bens declarados ao TSE: ${esc(NAO_DISPONIVEL)}.</p>`
      : "";

  const social = candidate.social_links || [];
  const socialBlock = social.length
    ? `<div class="declared-social" aria-label="Redes sociais informadas ao TSE">
        <div class="declared-assets-head">
          <strong>Redes sociais informadas ao TSE</strong>
          <span>${social.length} link${social.length === 1 ? "" : "s"}</span>
        </div>
        <ul class="declared-social-list">${social
          .map((url) => `<li><a target="_blank" rel="noopener" href="${esc(url)}">${esc(url)}</a></li>`)
          .join("")}</ul>
      </div>`
    : hasGap(candidate, "social_links")
      ? `<p class="plain-empty">Redes sociais informadas ao TSE: ${esc(NAO_DISPONIVEL)}.</p>`
      : "";

  return `<div id="bens-declarados" class="assets-section">${assetsBlock || `<p class="plain-empty">Bens declarados ao TSE: ${esc(NAO_DISPONIVEL)}.</p>`}</div>${factsBlock}${socialBlock}`;
}

// 06 — FONTES. Toda afirmação da ficha tem de ser rastreável até aqui.
function renderSources(sources) {
  if (!sources.length) return `<p class="plain-empty">Nenhuma fonte adicional disponível.</p>`;
  return `<div class="source-list">${sources
    .map(
      (item) => `
        <div class="source-item">
          <div><strong>${esc(item.name)}</strong><span>${esc(item.detail)}</span></div>
          <a target="_blank" rel="noopener" href="${esc(item.url)}">Abrir</a>
        </div>`
    )
    .join("")}</div>`;
}

function collectSources(candidate, meta, chamberRow, assets, institutionalHistory, thematicEvidence) {
  return [
    candidate.source?.official_portal
      ? {
          name: "TSE · cadastro eleitoral",
          detail: `Atualizado em ${formatSnapshot(meta?.collected_at)}`,
          url: candidate.source.official_portal,
        }
      : null,
    candidate.photo_source?.official_archive_url
      ? {
          name: "TSE · foto",
          detail: candidate.photo_source.dataset || "Arquivo oficial",
          url: candidate.photo_source.official_archive_url,
        }
      : null,
    candidate.current_mandate?.profile_url || chamberRow?.profile_url || institutionalHistory?.profile_url
      ? {
          name: "Câmara dos Deputados",
          detail: "Perfil público",
          url:
            candidate.current_mandate?.profile_url ||
            chamberRow?.profile_url ||
            institutionalHistory?.profile_url,
        }
      : null,
    assets?.source?.official_candidate_url
      ? {
          name: "TSE · bens declarados",
          detail: assets.source.dataset || "Bens de candidatos",
          url: assets.source.official_candidate_url,
        }
      : null,
    ...thematicEvidence
      .filter((item) => item.source_url)
      .map((item) => ({
        name: topicById(item.topic_id)?.label || evidenceTypeLabel(item.evidence_type),
        detail: item.source_publisher || item.published_at || "",
        url: item.source_url,
      })),
  ].filter(Boolean);
}

function showMessage(text) {
  const mount = $("profileMount");
  mount.className = "qv-empty";
  mount.textContent = text;
}

async function initProfile() {
  const id = params().get("id");
  const requested = params().get("cargo");

  const [{ all, meta }, chamber, topics] = await Promise.all([
    loadCore(),
    getJSON(DATA.chamber),
    loadTopics(),
  ]);
  setTopics(topics);
  applyGlobalMeta(meta);

  if (!id) return showMessage("Candidato não informado.");

  const candidate = all.find((item) => String(item.tse_id) === String(id));
  if (!candidate) return showMessage("Candidato não encontrado na base atual.");

  const kind = candidate._kind || requested || "federal";
  const name = candidate.ballot_name || candidate.full_name || "Candidato";
  const institutional = candidate.current_mandate || null;
  const chamberRow =
    kind === "federal"
      ? chamber.find((item) => String(item.candidate_id || item.tse_id || "") === String(id)) || null
      : null;

  const thematicEvidence = topicEvidence(candidate);
  const prospective = prospectiveTopicEvidence(candidate);
  const actionEvidence = documentedActionEvidence(candidate);
  const impactTopics = practicalAreasFromEvidence(prospective);
  const assets = candidate.assets || null;
  const socialName =
    candidate.social_name && norm(candidate.social_name) !== norm(name) ? candidate.social_name : null;
  const currentActivityText = currentActivity(candidate, kind);

  // Metadados de compartilhamento: og:url aponta para o stub estático de
  // /social/<SQ_CANDIDATO>/, que é quem serve preview em rede social.
  document.title = `${name} · Quem Votar?`;
  const roleLabel = officeLabel(kind);
  const shareDescription = `${name} · ${roleLabel} · ${candidate.party || "Partido não informado"} · nº ${candidate.number || "—"}. Consulte dados públicos e fontes.`;
  const canonicalUrl = buildUrl(null, { id: String(candidate.tse_id), cargo: kind }).toString();
  const socialUrl = new URL(`social/${encodeURIComponent(candidate.tse_id)}/`, location.href).toString();

  document.querySelector('meta[property="og:title"]')?.setAttribute("content", document.title);
  document.querySelector('meta[property="og:description"]')?.setAttribute("content", shareDescription);
  document.querySelector('meta[property="og:url"]')?.setAttribute("content", socialUrl);
  document.querySelector('meta[name="twitter:title"]')?.setAttribute("content", document.title);
  document.querySelector('meta[name="twitter:description"]')?.setAttribute("content", shareDescription);
  document.querySelector('link[rel="canonical"]')?.setAttribute("href", canonicalUrl);

  const sources = collectSources(
    candidate,
    meta,
    chamberRow,
    assets,
    candidate.institutional_history || null,
    thematicEvidence
  );

  const mount = $("profileMount");
  mount.className = "";
  mount.innerHTML = `
    ${renderHero(candidate, kind, name, socialName, currentActivityText)}

    <nav class="profile-jump" aria-label="Navegar pela ficha">
      <a href="#faz-hoje">Hoje</a>
      <a href="#vai-fazer">Propõe</a>
      <a href="#impacto">Impacto</a>
      <a href="#historico">Histórico e trajetória</a>
      <a href="#bens-declarados">Bens declarados</a>
      <a href="#dados-eleitorais">Dados eleitorais</a>
      <a href="#fontes">Fontes</a>
    </nav>

    <section class="answer-section" id="faz-hoje">
      <p class="section-number">01</p>
      <div><h2>O que essa pessoa faz hoje?</h2>${renderToday(institutional, currentActivityText, candidate.occupation, candidate.source?.official_portal)}</div>
    </section>

    <section class="answer-section" id="vai-fazer">
      <p class="section-number">02</p>
      <div><h2>O que ela diz que vai fazer?</h2>${renderProposes(prospective)}</div>
    </section>

    <section class="answer-section impact-section" id="impacto">
      <p class="section-number">03</p>
      <div><h2>Onde isso pode mexer na vida real?</h2>${renderImpact(prospective, impactTopics)}</div>
    </section>

    <section class="answer-section secondary-answer" id="historico">
      <p class="section-number">04</p>
      <div><h2>Histórico</h2>${renderHistory(candidate.previous_elections || [], actionEvidence, candidate)}</div>
    </section>

    <section class="answer-section secondary-answer" id="dados-eleitorais">
      <p class="section-number">05</p>
      <div><h2>Dados eleitorais</h2>${renderElectoralData(candidate, assets)}</div>
    </section>

    <section class="answer-section secondary-answer" id="fontes">
      <p class="section-number">06</p>
      <div><h2>De onde saiu isso?</h2>${renderSources(sources)}</div>
    </section>`;

  mount.querySelectorAll("img[data-photo]").forEach((img) => {
    img.addEventListener("error", () => {
      img.outerHTML = '<div class="profile-photo profile-fallback">Imagem não disponível</div>';
    });
  });

  $("profileCompare")?.addEventListener("click", (event) => {
    toggleCompare(event.currentTarget.dataset.candidateId);
    syncComparisonControls();
  });

  $("profileShare")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const original = button.textContent;
    try {
      if (navigator.share) {
        await navigator.share({ title: document.title, text: shareDescription, url: socialUrl });
        return;
      }
      await navigator.clipboard.writeText(socialUrl);
      button.textContent = "Link copiado";
      setTimeout(() => (button.textContent = original), 1800);
    } catch (error) {
      if (error?.name === "AbortError") return;
      button.textContent = "Copie o link da barra";
      setTimeout(() => (button.textContent = original), 2200);
    }
  });

  setupComparisonSync();
}

initProfile();
