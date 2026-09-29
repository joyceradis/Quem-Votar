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

// Rótulo legível de uma URL de rede social informada ao TSE.
export function socialLabel(url) {
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^(www|m|pt-br)\./, "");
    const network =
      { "instagram.com": "Instagram", "facebook.com": "Facebook", "twitter.com": "X (Twitter)", "x.com": "X (Twitter)", "tiktok.com": "TikTok", "youtube.com": "YouTube", "kwai.com": "Kwai", "threads.net": "Threads", "linkedin.com": "LinkedIn", "t.me": "Telegram" }[host] || host;
    const handle = u.pathname.split("/").filter(Boolean)[0];
    const isId = !handle || /^profile\.php$/i.test(handle);
    return isId ? network : `${network} · ${handle.startsWith("@") ? handle : "@" + handle.replace(/^@/, "")}`;
  } catch {
    return url;
  }
}
