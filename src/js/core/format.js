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

// Rótulo legível de uma URL de rede social informada ao TSE.
export function socialLabel(url) {
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^(www|m|web|br|k|pt-br)\./, "");
    // Canal público do WhatsApp (whatsapp.com/channel/…): o "handle" da URL é a
    // palavra "channel", que não identifica nada.
    if (host === "whatsapp.com") return "WhatsApp · canal";
    const network = SOCIAL_NETWORKS[host] || host;
    const handle = u.pathname.split("/").filter(Boolean)[0];
    const isId = !handle || /^profile\.php$/i.test(handle);
    return isId ? network : `${network} · ${handle.startsWith("@") ? handle : "@" + handle.replace(/^@/, "")}`;
  } catch {
    return url;
  }
}
