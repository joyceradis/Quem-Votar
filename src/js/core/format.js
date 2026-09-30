// Formatação — portado literalmente de app.js:95-117.
export function formatBRL(value) {
  if (typeof value !== "number" || !isFinite(value)) return null;
  try {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
  } catch {
    return `R$ ${value}`;
  }
}

export function formatSnapshot(iso) {
  if (!iso) return "data não disponível";
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      timeZone: "America/Sao_Paulo",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return new Date(iso).toLocaleString("pt-BR");
  }
}

// Iniciais do nome de urna para o fallback de foto. Puramente tipográfico:
// não carrega cor, ordem nem qualquer sinal editorial.
export function initials(name) {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter((part) => part.length > 2 || /^[A-Za-zÀ-ú]$/.test(part));
  if (!parts.length) return "?";
  const first = parts[0][0];
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

// "2025-07-02" -> "02/07/2025". Datas de calendário não têm hora nem fuso.
export function formatDateBR(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""));
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value || "";
}

// Situação da candidatura como o TSE a informa, em caixa de frase
// ("RENÚNCIA" -> "Renúncia"). A sentinela (not_available) e o vazio não viram
// afirmação: devolvem null e quem chama diz "não disponível".
export function registrationStatusText(value) {
  const raw = String(value || "").trim();
  if (!raw || raw.toLowerCase() === "not_available") return null;
  const lower = raw.toLocaleLowerCase("pt-BR");
  return lower.charAt(0).toLocaleUpperCase("pt-BR") + lower.slice(1);
}

// Só o que foge do "deferido" precisa de aviso na lista: é a exceção que muda
// o que a pessoa faz na urna (renúncia, indeferimento, julgamento pendente).
// Deferido é o estado comum e não recebe marcação — nada aqui é nota de qualidade.
export function registrationStatusException(value) {
  const text = registrationStatusText(value);
  return text && text !== "Deferido" ? text : null;
}

const SOCIAL_NETWORKS = {
  "instagram.com": "Instagram",
  "facebook.com": "Facebook",
  "twitter.com": "X (Twitter)",
  "x.com": "X (Twitter)",
  "tiktok.com": "TikTok",
  "youtube.com": "YouTube",
  "kwai.com": "Kwai",
  "kwai-video.com": "Kwai",
  "threads.net": "Threads",
  "threads.com": "Threads",
  "linkedin.com": "LinkedIn",
  "t.me": "Telegram",
  "linktr.ee": "Linktree",
};

// "ricardoferra%C3%A7oOficial" -> "ricardoferraçoOficial". Sequência inválida
// fica como veio, em vez de quebrar o rótulo.
function safeDecode(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

// Primeiro trecho do caminho que NÃO é o nome da pessoa/canal:
// - opaco: o que vem depois é token ou ID (facebook.com/share/<token>,
//   youtube.com/channel/UC…, kwai-video.com/u/<id>) — o rótulo é só a rede;
// - nomeado: o nome vem no trecho seguinte (linkedin.com/in/<nome>,
//   youtube.com/user/<nome>).
const OPAQUE_FIRST_SEGMENTS = new Set(["share", "sharer", "people", "groups", "pages", "pg", "channel", "watch", "profile.php", "u", "p"]);
const NAMED_FIRST_SEGMENTS = new Set(["in", "company", "school", "user", "c"]);

// Rótulo legível de uma URL de rede social informada ao TSE.
export function socialLabel(url) {
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^(www|m|web|br|k|pt-br)\./, "");
    // Canal público do WhatsApp (whatsapp.com/channel/…): o "handle" da URL é a
    // palavra "channel", que não identifica nada.
    if (host === "whatsapp.com") return "WhatsApp · canal";
    const network = SOCIAL_NETWORKS[host] || host;
    const segments = u.pathname.split("/").filter(Boolean).map(safeDecode);
    const first = segments[0];
    if (!first) return network;
    const key = first.toLowerCase();
    if (OPAQUE_FIRST_SEGMENTS.has(key)) return network;
    if (NAMED_FIRST_SEGMENTS.has(key)) return segments[1] ? `${network} · ${segments[1]}` : network;
    return `${network} · ${first.startsWith("@") ? first : "@" + first}`;
  } catch {
    return url;
  }
}
