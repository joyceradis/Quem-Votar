# Contrato de privacidade da telemetria GA4

Issue de origem: #108.

## Objetivo

Medir carregamentos de páginas sem transmitir identidade de candidatura, termo de
busca, filtros eleitorais, lista de `SQ_CANDIDATO` ou estado derivado da URL ao
GA4.

Identificadores técnicos intrínsecos ao GA4, como `client_id`, podem existir se
o analytics continuar habilitado. O requisito é impedir que sejam acompanhados
por conteúdo que identifique qual candidatura, busca ou filtro eleitoral o
usuário consultou.

## Contrato no cliente

`telemetry.js` é o único bootstrap GA4 das páginas públicas.

Invariantes:

- origem canônica explícita: `https://joyceradis.github.io`;
- base canônica: `/Quem-Votar/`;
- pathname submetido a allowlist explícita;
- origin, pathname ou rota desconhecidos falham fechados para a raiz canônica;
- `page_location` nunca inclui query string ou hash;
- `page_referrer` é sanitizado separadamente: somente origem canônica + rota
  allowlistada; referrer externo/desconhecido vira string vazia;
- `page_title` é genérico por classe de página e nunca usa nome/número de candidatura;
- `send_page_view: false`;
- exatamente um `page_view` manual no bootstrap local;
- `allow_google_signals: false`;
- `allow_ad_personalization_signals: false`;
- nenhuma alteração em `window.location` ou History API;
- o cliente não emite eventos eleitorais customizados nesta fase.

A URL funcional e compartilhável continua intacta no navegador.

## Allowlist de rotas

- `/` / `index.html`;
- `candidatos.html`;
- `candidato.html`;
- `comparar.html`;
- `temas.html`;
- `sobre.html`;
- `apoio.html`.

Wrappers sociais e qualquer outra rota não entram na telemetria detalhada:
falham fechados para a raiz canônica.

## Enhanced Measurement e configuração administrativa

`send_page_view: false` controla o pageview automático do comando `config`,
mas não é prova de que nenhum outro evento automático seja emitido pela tag.

Antes de considerar #108 concluída, verificar no stream GA4:

1. mudanças de página por History API;
2. site search;
3. outbound clicks;
4. scroll;
5. form interactions/file downloads, se habilitados;
6. qualquer segunda tag ou GTM;
7. Data Redaction como defesa em profundidade, nunca como controle primário.

Nenhuma mudança no GA4 Admin está autorizada por este patch.

## Gate de rede

Testes unitários certificam a lógica local. O gate de privacidade exige captura
das requisições reais para `collect`, preferencialmente também na revisão
publicada que será aceita.

A captura deve cobrir:

- `?id=`;
- `?ids=`;
- `?q=`;
- `?tema=`;
- `?partido=`;
- `?cargo=`;
- `?page=`;
- hash;
- rota social;
- rota desconhecida;
- History API/back/forward;
- scroll;
- outbound click;
- qualquer `page_view` automático.

Inspecionar em cada request, quando aplicável:

- nome do evento;
- `page_location`;
- `page_referrer`;
- `page_title`;
- parâmetros de evento;
- URLs de click;
- duplicidade.

Nenhum payload pode carregar `SQ_CANDIDATO`, nome/número de candidatura,
termo de busca, valor de filtro ou URL/estado capaz de revelar interesse
eleitoral específico.

## Estado de aceite

Sem captura de rede publicada e reconciliação do SHA servido:

`IMPLEMENTAÇÃO PRONTA / PRIVACY GATE BLOCKED`.
