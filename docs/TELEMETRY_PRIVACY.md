# Contrato de privacidade da telemetria GA4

Issue de origem: #108.

## Objetivo

Medir carregamentos de páginas sem transmitir identidade de candidatura, busca,
tema, partido ou lista de `SQ_CANDIDATO` ao GA4.

Durante o feature freeze, esta camada não amplia telemetria de comparação. O
único evento emitido pelo código é `page_view`.

## Contrato no cliente

`telemetry.js` é o único bootstrap do GA4 nas páginas públicas.

Invariantes:

- Measurement ID único: `G-2KY1FDKV88`;
- `send_page_view: false`;
- um `page_view` manual por carga;
- `page_location` usa allowlist de rotas públicas e nunca inclui query ou hash;
- rota desconhecida falha fechada para a raiz do projeto;
- `page_referrer` é vazio;
- `page_title` é genérico por rota e não usa nome de candidatura;
- `allow_google_signals: false`;
- `allow_ad_personalization_signals: false`;
- `ignore_referrer: true`;
- nenhuma alteração em `window.location` ou no histórico do navegador.

A URL funcional e compartilhável continua intacta no navegador.

## Configuração administrativa obrigatória antes de considerar a proteção completa

No fluxo Web do GA4:

1. Desativar a medição otimizada automática que não seja necessária. Para esta
   fase, a configuração mais simples e auditável é deixar Enhanced Measurement
   desligado e manter somente o `page_view` manual do projeto.
2. Se Enhanced Measurement permanecer ativo, desativar explicitamente
   "Page changes based on browser history events" e também os eventos que podem
   transportar URL/texto eleitoral, especialmente site search, outbound clicks,
   form interactions e file downloads.
3. Ativar Data redaction como defesa em profundidade para parâmetros de query
   conhecidos, incluindo `ids`, `id`, `q`, `tema`, `partido` e
   `SQ_CANDIDATO`. Isso não substitui a sanitização do cliente.
4. Confirmar que não existe uma segunda tag/GTM enviando dados fora deste
   contrato.

A configuração administrativa não corrige dados históricos já coletados.

## Gate de rede

Antes de fechar #108, inspecionar requisições reais de coleta em carga, reload,
back/forward e mudanças de histórico. Nenhum payload pode conter
`SQ_CANDIDATO`, nome, número, partido, busca, tema ou lista de IDs em
`page_location`, `page_referrer`, `page_title` ou parâmetros de evento.

Relatórios e DebugView não substituem a inspeção do payload.

## Fontes oficiais

- https://developers.google.com/analytics/devguides/collection/ga4/views
- https://support.google.com/analytics/answer/13544947
- https://support.google.com/analytics/answer/9216061
- https://developers.google.com/analytics/devguides/collection/ga4/reference/config
