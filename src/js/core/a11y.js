// Acessibilidade do casco — portado literalmente de app.js:152-218
// (setupNavigation/setupTextSize), já coberto por
// tests/test_accessibility_contract.py. Comportamento não muda: só passa a
// viver em módulo próprio em vez de dentro do monólito app.js.
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

export function setupTextSize() {
  const stored = localStorage.getItem("qv_text_scale");
  if (stored === "large") document.documentElement.dataset.scale = "large";

  const button = $("textSizeButton");
  if (!button) return;

  const refresh = () => {
    const large = document.documentElement.dataset.scale === "large";
    button.textContent = large ? "A" : "A+";
    button.setAttribute(
      "aria-label",
      large ? "Voltar ao tamanho normal do texto" : "Aumentar tamanho do texto"
    );
  };

  button.addEventListener("click", () => {
    const large = document.documentElement.dataset.scale === "large";

    if (large) {
      delete document.documentElement.dataset.scale;
      localStorage.removeItem("qv_text_scale");
    } else {
      document.documentElement.dataset.scale = "large";
      localStorage.setItem("qv_text_scale", "large");
    }
    refresh();
  });

  refresh();
}
