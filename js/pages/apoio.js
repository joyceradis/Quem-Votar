// Apoio — portado do <script> inline que vivia dentro de apoio.html.
// A página era a única fora do roteador de páginas e a única com CSS e JS
// embutidos; agora usa o mesmo casco e os mesmos módulos das demais.
//
// Camada de sustentabilidade (AGENTS.md §9): nada aqui lê ou escreve dado
// eleitoral, e nenhum tracker é carregado.
import { $ } from "../core/dom.js";
import { loadCore, applyGlobalMeta } from "../core/data.js";
import { setupNavigation, setupTextSize } from "../core/a11y.js";

setupNavigation();
setupTextSize();

// Só a data do rodapé compartilhado. Nenhum dado de candidatura é lido,
// exibido ou alterado por esta página (AGENTS.md §9).
loadCore().then(({ meta }) => applyGlobalMeta(meta));

const PIX_PAYLOAD =
  "00020126580014br.gov.bcb.pix0136e5d18663-c4e4-4d42-9696-8827dbafb3245204000053039865802BR5925JOYCE_RADIS_DE_SOUZA_DE_O6005Serra610929161-78662290525MCDY32430233178986346970463043652";
const PIX_EMAIL = "contato@drajoyceradis.com";

const feedback = $("pixFeedback");

async function copyText(value, button, originalLabel) {
  let copied = false;

  try {
    await navigator.clipboard.writeText(value);
    copied = true;
  } catch {
    // Fallback para navegadores sem Clipboard API ou fora de contexto seguro.
    const input = document.createElement("textarea");
    input.value = value;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.select();
    copied = document.execCommand("copy");
    input.remove();
  }

  if (!copied) {
    feedback.textContent =
      "Não foi possível copiar automaticamente. Selecione a chave por e-mail acima.";
    return;
  }

  button.textContent = "Copiado";
  feedback.textContent = "Copiado para a área de transferência.";

  setTimeout(() => {
    button.textContent = originalLabel;
    feedback.textContent = "";
  }, 2200);
}

$("copyPayload")?.addEventListener("click", (event) =>
  copyText(PIX_PAYLOAD, event.currentTarget, "Copiar Pix Copia e Cola")
);
$("copyEmail")?.addEventListener("click", (event) =>
  copyText(PIX_EMAIL, event.currentTarget, "Copiar chave por e-mail")
);
