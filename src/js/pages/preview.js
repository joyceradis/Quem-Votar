// Só para a prévia interna do casco (Fase 2) — nenhuma página pública usa
// este arquivo. Prova que core/a11y.js funciona igual ao app.js original
// quando ligado ao markup dos partials nav.njk/footer.njk.
import { setupNavigation, setupTextSize } from "../core/a11y.js";

setupNavigation();
setupTextSize();
