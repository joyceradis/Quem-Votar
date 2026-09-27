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
