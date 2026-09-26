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

**Fase 2 concluída — casco compartilhado.**

- `src/_includes/nav.njk` + `src/_includes/footer.njk`: fonte única do
  header/drawer/rodapé hoje duplicados byte-a-byte em 6 dos 7 HTML.
  `src/_data/navLinks.js` é a lista única de links (antes copiada à mão em
  cada página e também em `telemetry.js`).
- `src/_includes/base.njk`: layout único que monta `<head>`, os partials
  acima e o carregamento do módulo JS da página.
- `src/js/core/{dom,a11y,data,url-state}.js`: `dom.js` e `a11y.js` portados
  **literalmente** de `app.js:10-14` e `app.js:152-218` (mesmo
  comportamento, só em módulo próprio); `url-state.js` é novo e substitui
  as duas implementações quase idênticas de "ajustar searchParams da URL +
  `history.replaceState`" que existiam separadas em `initCandidates` e
  `initCompare`.
- `src/_data/version.js`: fonte única de cache-busting. Antes, o `?v=`
  divergia em três lugares (`5.5.8` no HTML, `5.5` dentro do `app.js`,
  `5.5.0` no arquivo `VERSION`) sem nenhum aviso quando saíam de sincronia;
  agora todo template/módulo lê o mesmo `VERSION`.
- `src/styles/components/{nav,footer}.css`: portados literalmente de
  `styles.css` (mesmas classes que a produção já usa), para a Fase 3 poder
  trocar o markup das páginas reais sem reescrever este CSS.
- Validação comportamental (não só visual) via Playwright contra o casco
  real: nav desktop visível/hambúrguer oculto ≥980px e o inverso <980px,
  abrir o drawer move o foco para "Fechar", `Esc` fecha e devolve o foco ao
  botão "Menu", aumento de texto persiste — mesmo contrato de
  `tests/test_accessibility_contract.py` hoje em produção, sem nenhum erro
  de console. Porte formal desse teste para os novos módulos fica para a
  Fase 3, junto com o corte de cada página real (não faz sentido testar
  formalmente um casco que ainda não está no ar).

Nenhum arquivo público foi alterado por esta frente.

Confirmado em CI (não só localmente): `Qualidade do site` e
`🛑 Inspetor de Regras da IA` verdes no commit `9ea2785` (PR #168).

**Revisão de direção de arte (feedback direto da mantenedora sobre a Fase 1).**

- Nova ilustração `assets/v6-penha-line.svg`:
  single-line art, traço 1.2px azul-marinho, `fill:none`, sem sombra/
  hachura. Três elementos: vão da Terceira Ponte com pilares retos
  tracejados (sem cabos estaiados), domo único do Morro da Penha, e o
  Convento no topo (retângulo + triângulo + cruz centralizada, cruz em
  rosa como único destaque de cor) sobre uma linha de mar cinza-clara.
  Substitui a ilustração anterior, que não agradou.
- **Correção de processo:** a primeira tentativa desta ilustração
  sobrescreveu `assets/capixaba-line.svg` — que já está ao vivo em
  produção (usado no hero do `index.html` atual). Isso violava o
  compromisso de não tocar nenhum arquivo público antes da Fase 5. Foi
  revertido imediatamente (`git checkout -- assets/capixaba-line.svg`) e a
  nova ilustração foi movida para um caminho próprio da V6
  (`assets/v6-*.svg`), sem colidir com nada em produção. Daqui para frente,
  todo asset novo/experimental usa o prefixo `v6-` até o corte da Fase 5.
- Fat Footer institucional novo (`src/_includes/footer.njk` +
  `src/styles/components/footer.css`): várias colunas de link (Navegar,
  Sobre, Snapshot) sobre fundo escuro (`--blue-dark`), com a ilustração
  como marca d'água em opacidade 0.15 na última coluna
  (`.qv-fat-footer-illustration`). Responde também ao feedback de
  contraste fraco/excesso de branco, já que introduz uma seção escura real
  na página.
- Ilustração `v6-penha-line.svg` recebeu uma segunda rodada: sombra suave
  (`feDropShadow`) e contornos internos concêntricos na ponte/morro/parede
  do convento, dando sensação de volume sem virar hachura, a pedido da
  mantenedora (commit `74069ab`). **Aprovada.**
- Exploração paralela `assets/v6-penha-sketch.svg`: variante em estilo de
  esboço técnico a nanquim, a partir de referência do Pinterest —
  tabuleiro em perspectiva sobre pilares que diminuem ao fundo,
  guarda-corpo/postes de luz, morro com hachura de sombreado, barco e
  ondulações na água. Corrigida em uma segunda rodada (commit `33fa0b9`)
  para o tabuleiro pousar de fato na encosta do morro (antes ficava
  flutuando sem tocar) e para dar mais volume 3D (sombra do conjunto,
  sombreado cilíndrico dentro dos pilares, hachura sob a viga). **Aprovada
  pela mantenedora ("Beleza, ok").**
- **Decisão em aberto:** qual das duas ilustrações (`v6-penha-line.svg`
  minimalista ou `v6-penha-sketch.svg` estilo esboço técnico) vai para o
  Home — ou se as duas convivem em usos diferentes (ex.: uma no hero, outra
  em `sobre.html`/`apoio.html`) — fica para a Fase 3, quando a integração
  real de cada página for desenhada.
- **Ainda pendente de referência visual:** fonte tipográfica, formato das
  tags de tema e o modo exato de integrar a ilustração escolhida no Home
  (sem uma divisão fixa em caixa) ficam para quando a mantenedora
  compartilhar as referências salvas — não foram redesenhados por palpite
  para evitar repetir o mesmo problema que motivou esta reconstrução.

## Tipografia (feedback "fonte ruim")

O `:root` antigo apenas **nomeava** `"Inter"` numa pilha de fontes de sistema,
sem nunca carregá-la — então o site caía no fallback genérico de cada SO
(Arial/Liberation Sans), que é exatamente o aspecto de "sem tipografia" que a
mantenedora apontou. Corrigido:

- famílias de fato carregadas e **auto-hospedadas** em `assets/fonts/`
  (`src/styles/fonts.css`), sem nenhuma requisição ao CDN do Google — carregar
  de terceiros exporia o IP de cada visitante, contrariando
  `docs/TELEMETRY_PRIVACY.md` e `docs/GOVERNANCE.md`;
- subsets `latin` + `latin-ext` em `woff2`, com `unicode-range`: em português
  o navegador baixa só o `latin` (~47 KB Inter, ~65 KB display);
- `preload` apenas dos dois subsets `latin` críticos, para não haver "flash"
  de fonte de sistema;
- tokens novos `--font-sans` (texto/interface) e `--font-display` (títulos),
  com `font-optical-sizing: auto` nos títulos;
- origem, licença (todas OFL-1.1) e atribuição registradas em
  `assets/fonts/README.md`, como exige `docs/DESIGN_REFERENCES.md`.

**Decisão pendente:** a família de títulos. O styleguide mostra quatro
candidatas lado a lado com a mesma frase (`/styleguide/`): **A** Fraunces
(padrão atual), **B** Instrument Serif, **C** Bricolage Grotesque, **D** Inter
em peso alto. Escolhida uma, as outras saem de `assets/fonts/` e de
`src/styles/fonts.css`.

## Ilustração no rodapé — SVG corrigido

O rodapé e o styleguide ainda apontavam para a ilustração minimalista, não
para o esboço técnico aprovado. Corrigido, e a duplicação que existia para
isso foi eliminada: em vez de manter um segundo arquivo quase idêntico só
para a versão clara (`v6-penha-line-watermark.svg`, **removido**), o SVG passa
a ser inlinado pelo filtro `svgInline` (`.eleventy.js`) e recolorido por CSS
sobre o fundo escuro. Um arquivo, duas aparências.

## Verificação de ponta a ponta (Playwright, versionado)

As checagens comportamentais que vinham sendo rodadas como scripts
descartáveis em `/tmp` (e somem no fim da sessão) agora são testes reais
versionados:

- `@playwright/test` como devDependency (`package.json`), pinada na mesma
  versão já instalada globalmente no ambiente (`1.56.1`) para reaproveitar
  o cache de browsers sem novo download.
- `playwright.config.js`: sobe o próprio `npx eleventy --serve` como
  `webServer`, roda contra `http://127.0.0.1:4173`, dois projetos
  (`desktop` 1200×900, `mobile` 390×844 via `Pixel 5`). Não tem relação com
  a suíte Python em `tests/` (pipeline/produção atual) nem a substitui.
- `tests-e2e/shell.spec.js`: 6 testes × 2 viewports = 12 casos —
  breakpoint desktop/hambúrguer, `aria-current` no item ativo, foco ao
  abrir o drawer + `Esc` devolvendo foco ao botão Menu, persistência do
  aumento de texto entre recargas, zero erro de console/requisição
  quebrada no casco, e o styleguide renderizando os componentes
  principais. **12/12 passando** (`npm run test:e2e`).
- Roda hoje localmente (validado nesta sessão); ainda não está plugado em
  nenhum workflow do `.github/workflows/` (arquivo protegido por
  CODEOWNERS) — wiring em CI fica para a Fase 4 (verificação completa
  antes do corte), junto com o `runtime-proof` já existente.

## ⚠ Bloqueador conhecido da Fase 5: `audit-site.py` está acoplado ao formato

Achado durante a Fase 3, antes de virar problema no corte. Várias asserções de
`scripts/audit-site.py` não verificam **comportamento**, e sim o **texto
literal dos arquivos atuais**. Como a V6 gera esses arquivos a partir de
`src/`, elas quebram no corte mesmo que o site esteja idêntico para quem usa:

| Asserção | Por que quebra |
|---|---|
| `"const PAGE_SIZE=12" in app` | lê `app.js`; na V6 a constante vive em `src/js/pages/candidates.js` |
| `@media\(min-width:980px\)\{\.desktop-nav\{display:flex\}` | casa com o `styles.css` **minificado**; o CSS da V6 é formatado |
| `'.nav-toggle::before{content:"☰"' in styles` | idem, dependente de minificação |
| `"O que essa pessoa faz hoje?" in app` (e a ordem das 3 perguntas) | lê `app.js`; na V6 está no módulo da ficha |
| `'id="dados-eleitorais"' in app` depois de `id="impacto"` | idem |
| `public_markup.count('id="drawer"') == len(REQUIRED_PAGES)` | conta ocorrências somando os 6 HTML + `app.js` |

Nenhuma delas indica um contrato de produto quebrado — indicam que o teste
mede a implementação. O que essas asserções *querem* garantir (12 por página,
nav desktop visível ≥980px, ordem HOJE→PROPÕE→IMPACTO, drawer em toda página,
dados eleitorais na camada secundária) já está coberto por teste de
comportamento real em `tests-e2e/`.

**Encaminhamento:** a Fase 5 precisa atualizar `scripts/audit-site.py` no
mesmo PR do corte, reescrevendo essas asserções para lerem a saída construída
(`_site/`) em vez dos arquivos-fonte. `scripts/audit-site.py` é caminho
protegido por CODEOWNERS e pela Cerca Elétrica, então esse PR exige revisão de
@joyceradis e provavelmente `Authorization-Issue:`. Não fazer isso de véspera.

## Fase 3 — páginas portadas

| Página | Estado |
|---|---|
| Home (`index.html`) | ✅ portada, com dados reais (547 candidaturas, 7 temas) |
| Candidaturas (`candidatos.html`) | ✅ portada: busca, filtros, 12/página, troca de cargo, funil de comparação |
| Ficha (`candidato.html`) | ⬜ pendente |
| Comparar (`comparar.html`) | ⬜ pendente |
| Assuntos (`temas.html`) | ⬜ pendente |
| Como funciona (`sobre.html`) | ⬜ pendente |
| Apoiar (`apoio.html`) | ⬜ pendente |

Os módulos `core/` que as páginas restantes precisam já estão prontos e
testados (`evidence.js`, `compare-state.js`, `data.js`, `format.js`,
`url-state.js`, `dom.js`, `a11y.js`) — o que falta em cada página é markup e
a função de render, não regra de negócio.

## Estado no fim da Fase 1 (checkpoint para retomada)

- Fases 0, 1 e 2 commitadas na branch `claude/inspiring-keller-c98fd2`
  (PR #168, draft), todas com CI verde (`Qualidade do site` +
  `🛑 Inspetor de Regras da IA`) e zero arquivo público alterado.
- Design system utilizável hoje via `npm start` → `/styleguide/` (tokens,
  botão, busca em pílula, tag, card) e `/preview-shell/` (casco completo:
  nav, drawer, rodapé fat footer, ilustração).
- Duas ilustrações aprovadas e prontas para uso: `assets/v6-penha-line.svg`
  (minimalista) e `assets/v6-penha-sketch.svg` (esboço técnico).
- Em aberto antes de avançar para a Fase 3: (1) qual ilustração vai onde,
  (2) fonte tipográfica, (3) formato das tags, (4) integração exata da
  ilustração no Home sem divisão fixa — todos aguardando as referências
  salvas da mantenedora, ou uma decisão explícita dela para seguir sem
  elas.
