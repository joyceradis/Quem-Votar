// Acessibilidade do casco — drawer mobile (setupNavigation), portado
// literalmente de app.js:152-218, já coberto por
// tests/test_accessibility_contract.py. O botão de aumento de texto
// (setupTextSize) foi removido por pedido direto da mantenedora
// ("esse A+ eu não gosto" / "deixa sem"): o layout continua resiliente
// ao zoom nativo do navegador/SO (AGENTS.md §6), só deixou de ter um
// controle próprio no site.
import { $ } from "./dom.js";

export function setupNavigation() {
  const drawer = $("drawer");
  const backdrop = $("backdrop");
  const menuButton = $("menuButton");
  const closeButton = $("closeMenu");

  const syncBackdrop = () => {
    if (backdrop) backdrop.hidden = !drawer?.classList.contains("open");
  };

  const open = () => {
    if (!drawer) return;
    drawer.removeAttribute("inert");
    drawer.setAttribute("aria-hidden", "false");
    drawer.classList.add("open");
    menuButton?.setAttribute("aria-expanded", "true");
    document.body.classList.add("page-lock");
    syncBackdrop();
    closeButton?.focus();
  };

  const close = () => {
    if (!drawer) return;
    const wasOpen = drawer.classList.contains("open");
    if (wasOpen) menuButton?.focus();
    drawer.classList.remove("open");
    drawer.setAttribute("inert", "");
    drawer.setAttribute("aria-hidden", "true");
    menuButton?.setAttribute("aria-expanded", "false");
    document.body.classList.remove("page-lock");
    syncBackdrop();
  };

  menuButton?.addEventListener("click", open);
  closeButton?.addEventListener("click", close);
  backdrop?.addEventListener("click", close);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
}

