// Ruído de terceiros nos testes de "carrega sem erro".
//
// O que esses testes medem é se *os nossos* assets carregam. As fotos das
// candidaturas e a telemetria (Google Analytics, carregado por telemetry.js)
// vêm de hosts de terceiros: num runner sem saída para eles, falham por rede,
// não por defeito nosso. No caso das fotos, o fallback textual é justamente o
// comportamento esperado, e há teste próprio para ele.
//
// O critério é a origem, não uma lista de domínios: qualquer URL fora da
// origem da própria página é de terceiro. Lista de host envelhece — os
// retratos já migraram de domínio uma vez — e um teste que depende de lista
// desatualizada passa a ignorar o que deveria pegar.
//
// Toda requisição da nossa origem continua reprovando o teste, inclusive se
// falhar pelo mesmo motivo de rede. É por isso que este módulo não olha o
// código do erro.
const mesmaOrigem = (url, origem) => {
  try {
    return new URL(url, origem).origin === new URL(origem).origin;
  } catch {
    return false;
  }
};

// As mensagens de console "Failed to load resource: ..." não trazem a URL,
// então não dá para dizer de quem são. Descartamos: toda falha de rede já é
// capturada com precisão pelos handlers de response/requestfailed, que têm a
// URL. Nada deixa de ser verificado por causa disso.
const consoleDeRede = (texto) => /^Failed to load resource\b/.test(String(texto || ""));

/**
 * Liga os coletores de erro numa página e devolve a lista, já filtrada.
 * Uso: const errors = coletarErros(page); ... expect(errors).toEqual([]);
 */
function coletarErros(page) {
  const errors = [];
  const nosso = (url) => mesmaOrigem(url, page.url() || "http://127.0.0.1:4173/");

  page.on("pageerror", (err) => errors.push(String(err)));
  page.on("console", (msg) => {
    if (msg.type() === "error" && !consoleDeRede(msg.text())) errors.push(msg.text());
  });
  page.on("response", (res) => {
    if (!res.ok() && nosso(res.url())) errors.push(`${res.status()} ${res.url()}`);
  });
  page.on("requestfailed", (req) => {
    if (nosso(req.url())) errors.push(`falhou ${req.url()}`);
  });
  return errors;
}

module.exports = { coletarErros, mesmaOrigem };
