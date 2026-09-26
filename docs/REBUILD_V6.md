# Reconstrução V6 — arquitetura, design system e higiene de pipeline

Rastreamento: [Issue #167](https://github.com/joyceradis/Quem-Votar/issues/167).

Autorização: decisão direta de @joyceradis (mantenedora), registrada na Issue
#167, conforme `AGENTS.md` §8.

## Por quê

O frontend acumulou fragmentação por patches sucessivos de múltiplos agentes:
nav/rodapé duplicados byte-a-byte em 6 dos 7 HTML públicos, `app.js` como
monólito de ~1.000 linhas sem fronteira de módulo, e `styles.css` com blocos
colados por número de issue em vez de integrados aos componentes. Os dados,
a proveniência e as regras editoriais (`AGENTS.md`) estão corretos e não são
o problema — o problema é manutenibilidade.

## Decisões

1. Build-time apenas: **Eleventy (11ty)**. A saída publicada continua
   HTML/CSS/JS puro, compatível com GitHub Pages; nenhum framework roda no
   navegador.
2. Janela de corte: todo o trabalho acontece em branch isolada; **produção
   não muda** até o feature freeze do núcleo eleitoral acabar em 04/10/2026.
   `https://joyceradis.github.io/Quem-Votar/` fica no ar sem alteração até o
   merge atômico final da Fase 5.

## Fases

| Fase | Escopo | Toca produção? |
|---|---|---|
| 0 | `package.json`/`.eleventy.js`, scaffold de build | Não |
| 1 | Design system (`tokens.css`, componentes, ilustração original) | Não |
| 2 | Casco compartilhado (partials nav/rodapé, módulos `core/*`) | Não |
| 3 | Página por página (Home → Candidatos → Ficha → Comparar → Temas → Como funciona → Apoiar), uma PR por página | Não |
| 4 | Verificação completa (testes, `audit-site.py`, `runtime-proof`, capturas de tela) | Não |
| 5 | Corte atômico em `main`, a partir de 04/10/2026 | **Sim** |
| 6 | Higiene de pipeline/CI (trilha paralela) | Não (decisões de cadência aguardam sinal explícito da mantenedora) |

## O que não muda

`SQ_CANDIDATO`, contrato JSON (`tse_id`, `ballot_name`, `topic_evidence`,
`current_mandate`, `assets`, `social_links`, ...), parâmetros de URL
(`cargo`, `q`, `partido`, `tema`, `institucional`, `page`, `id`, `ids`),
estrutura `/social/<SQ_CANDIDATO>/`, `data/reference/topic-evidence.json`, e
a ordem normativa da ficha (IDENTIDADE→HOJE→PROPÕE→IMPACTO→HISTÓRICO→DADOS
ELEITORAIS→FONTES). Esta é uma reconstrução de manutenibilidade e visual, não
uma reinterpretação de dado.

## Estado atual

**Fase 0 concluída.** `package.json`/`.eleventy.js` funcionando.

**Fase 1 em andamento — design system.**

- `src/styles/tokens.css`: cor, raio, sombra e movimento — valores idênticos
  ao `:root` canônico de `styles.css`, apenas nomeados e documentados.
- `src/styles/base.css`: reset e comportamento global, portado literalmente
  de `styles.css` (skip-link, foco visível, `prefers-reduced-motion`).
- `src/styles/components/{button,pill-search,tag,card}.css`: formalizam
  padrões já validados em produção (`.hero-search`, `.compare-button`,
  `.candidate-topic-tags`, `.candidate-card`) com nomenclatura `qv-*`
  reutilizável, sem inventar visual novo.
- `src/styleguide.njk`: página de revisão interna (não é rota pública,
  não referenciada por nenhum nav) para conferir os componentes via
  `npm start`. Reaproveita `assets/capixaba-line.svg` — a ilustração
  regional (Terceira Ponte + Convento da Penha) já existente e original do
  projeto — em vez de desenhar uma nova, já que a atual está correta e é
  a mesma direção visual que a mantenedora pediu.
- Validado localmente: `npm run build` + Playwright screenshot do
  styleguide renderizando corretamente; `scripts/audit-site.py` sem
  mudança (547/547, 22 evidências temáticas).

Nenhum arquivo público (`index.html`, `app.js`, `styles.css`, `data/*`) foi
alterado por esta frente.
