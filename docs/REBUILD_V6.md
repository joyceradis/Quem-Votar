# Reconstrução V6 — arquitetura, design system e higiene de pipeline

Rastreamento: [Issue #167](https://github.com/joyceradis/Quem-Votar/issues/167).

Autorização: decisão direta de @joyceradis (mantenedora), registrada na Issue
#167, conforme `AGENTS.md` §8.

## Estado atual (reconciliado em 2026-09-26, pós-#170)

- **Fases 0–4 concluídas e em `main`.** PRs #168 e #170 mergeados.
- **Fase 5 (corte) date-gated:** `scripts/cutover-v6.sh` recusa rodar antes
  de 2026-10-04. A superfície pública (`index.html`, `app.js`, `styles.css`,
  as 7 rotas) permanece **V5.5** no ar, sem alteração.
- **`VERSION` = `6.0.0`** já está preparada na `main`, mas ainda **não é a
  versão publicada**: as páginas no ar servem `?v=5.5.8`. `VERSION` só passa
  a valer no corte — ver README, "produção V5.5 / V6.0.0 preparada".
- **Caminhos protegidos já aplicados** (não mais "patch pendente"): a
  auditoria desacoplada (`public_css`/`public_js`) e o job de CI
  `frontend-v6` entraram pelo #170, autorizados pela Issue #169. O diretório
  `docs/patches/` deixou de existir.
- **Cadência do worker (#133): concluída** — `evidence-industrial` passou de
  5 min para horário. O incidente #171 (reaquisição da Câmara) é lane de
  dados separada e **não** é bloqueador da V6.
- **Único item de #169 não aplicável aqui:** a troca da origem do Pages,
  recusada pelo proxy de rede do ambiente; não bloqueia o corte (ver seção
  própria ao fim).

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

**Fase 1 concluída — design system.**

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

**As 7 páginas estão portadas.**

| Página | O que foi verificado contra os dados reais |
|---|---|
| Home (`index.html`) | 547 candidaturas, 7 temas com evidência, data do snapshot |
| Candidaturas (`candidatos.html`) | 137 federais / 410 estaduais, 12 por página, busca, filtros, troca de cargo, funil de comparação com teto de 3 |
| Ficha (`candidato.html`) | ordem HOJE→PROPÕE→IMPACTO→HISTÓRICO→DADOS→FONTES; 7 de 8 evidências em PROPÕE e a 8ª ("atuação") no histórico |
| Comparar (`comparar.html`) | mesmos campos para todas as colunas, sem destaque/ordem, estados de 0 e 1 seleção |
| Assuntos (`temas.html`) | só temas com pelo menos uma candidatura com fonte |
| Como funciona (`sobre.html`) | data do snapshot e a negação explícita de nota/ranking |
| Apoiar (`apoio.html`) | deixa de ser órfã: mesmo casco, tokens e módulos; firewall editorial mantido |

Tudo roda sobre os módulos `core/` (`evidence.js`, `compare-state.js`,
`data.js`, `format.js`, `url-state.js`, `dom.js`, `a11y.js`), portados
literalmente do `app.js`. Cobertura: **84 casos de Playwright** em desktop e
mobile.

O que a Fase 3 eliminou, em números:
- nav/drawer/rodapé duplicados em 6-7 arquivos → **1** partial de cada;
- `app.js` de 992 linhas sem fronteira → **7 módulos `core/` + 7 de página**;
- 3 reimplementações de sync de URL → **1** (`url-state.js`);
- `?v=` divergente em 3 lugares → **1** (`VERSION`);
- `apoio.html` com CSS e JS inline próprios → **0** inline;
- 2 blocos de CSS colados por número de issue no fim do `styles.css` → integrados ao componente a que pertencem;
- SVG de marca d'água duplicado em segundo arquivo → **1** arquivo, recolorido por CSS.

## Estado no fim da Fase 1 (checkpoint para retomada)

- Fases 0, 1 e 2 commitadas na branch `claude/inspiring-keller-c98fd2`
  (PR #168, **mergeado**), com CI verde (`Qualidade do site` +
  `🛑 Inspetor de Regras da IA`) e zero arquivo público alterado.
  _(Registro histórico do fim da Fase 1; as Fases 3 e 4 vieram depois no
  mesmo PR — ver o banner "Estado atual" no topo.)_
- Design system utilizável hoje via `npm start` → `/styleguide/` (tokens,
  botão, busca em pílula, tag, card) e `/preview-shell/` (casco completo:
  nav, drawer, rodapé fat footer, ilustração).
- Duas ilustrações aprovadas e prontas para uso: `assets/v6-penha-line.svg`
  (minimalista) e `assets/v6-penha-sketch.svg` (esboço técnico).
- _(Resolvido.)_ As decisões de direção de arte que estavam em aberto no fim
  da Fase 1 — qual ilustração vai onde, fonte tipográfica, formato das tags,
  integração da ilustração no Home — foram fechadas ao longo das Fases 3 e 4,
  com o feedback da mantenedora, e estão refletidas nas páginas em `src/`.

## Fase 4 — verificação antes do corte

### Correções vindas da revisão de código (2026-09-26)

A revisão apontou uma classe inteira de problema que nenhum teste de página
pegava: **a prévia local servia a saída na raiz do domínio, mas a produção
serve sob `/Quem-Votar/`**. Caminho absoluto (`/styles/base.css`) funcionava
na prévia e viraria 404 em produção — todo CSS, módulo JS e fonte.

Correções aplicadas:

1. **Caminhos relativos em todo o markup gerado** (`base.njk`, `nav.njk`,
   `extraStyles`, `pageScript`, `fonts.css`). Como todas as rotas públicas
   são planas na raiz (`candidatos.html`, e não `candidatos/`), caminho
   relativo funciona sob qualquer prefixo de publicação — inclusive um
   eventual domínio próprio no futuro, sem reconfigurar nada.
   `preview-shell` e `styleguide` também passaram a ser planos, pela mesma
   razão.
2. **`pathPrefix: "/Quem-Votar/"`** no Eleventy. Ele não reescreve link
   nenhum (os links já são relativos): serve para o servidor de prévia e o
   Playwright montarem a saída **sob o mesmo subcaminho da produção**, que é
   onde o defeito aparecia. A partir daqui, a suíte exercita a forma real da
   URL.
3. **Arquivos públicos faltando na saída**: `manifest.webmanifest`,
   `sitemap.xml`, `METODOLOGIA.md`, `AUDITORIA.md`, `telemetry.js`, `docs/`
   e os 548 stubs de `social/`. Sem eles, entre outras coisas, o botão de
   compartilhar de toda ficha apontava para um 404.
4. **Preload de fonte sem `?v=`**: o `@font-face` não versiona a URL, então o
   arquivo pré-carregado nunca casava com o requisitado — a fonte baixava
   duas vezes e o FOUT que o preload existe para evitar acontecia mesmo assim.
5. **`?page=N` era descartado**: `setKind()` zerava a página antes do
   primeiro render. Agora só zera em troca de cargo feita pela pessoa.
6. **Filtro fantasma**: `tema`/`partido` eram relidos da URL original a cada
   remontagem do select, então limpar o filtro e trocar de cargo ressuscitava
   o valor antigo. O valor da URL agora vale só na primeira montagem.
   (5 e 6 existem igualmente no `app.js` de produção — foram portados fiéis e
   corrigidos aqui, onde o código estava sendo reescrito de qualquer forma.)
7. **Páginas internas fora do público**: `styleguide` e `preview-shell` só
   entram na saída com `QV_DEV=1` (`npm start` e o servidor do Playwright).

### `npm run verify`

`scripts/verify-build.mjs` transforma tudo isso em garantia permanente, contra
a **saída do build** e não contra o texto-fonte dos arquivos:

- as 10 rotas/arquivos públicos obrigatórios existem;
- nenhuma página interna vazou;
- nenhum caminho absoluto de asset próprio sobrou em HTML ou CSS;
- toda referência local do HTML gerado aponta para um arquivo que existe.

Estado da Fase 4: `npm run build && npm run verify` OK (635 arquivos),
`npx playwright test` 84 passando / 2 pulados, `scripts/audit-site.py` OK,
zero arquivo de produção alterado e zero caminho protegido tocado.

### Auditoria desacoplada do nome dos arquivos (aplicada em #170)

`scripts/audit-site.py` passou a resolver a superfície pública em vez de ler
um arquivo de nome fixo (`public_css()` / `public_js()`): enquanto `styles.css`
e `app.js` existirem na raiz, ele mede exatamente o que media antes; depois do
corte, passa a medir a pasta `styles/`+`js/` publicada. As asserções que
dependiam do texto *minificado* viraram regex tolerante a espaço — medem a
regra, não a formatação.

**Aplicada em 2026-09-26 pelo PR #170, autorizada pela Issue #169.** Não é mais
"patch pendente": `scripts/audit-site.py` e `.github/workflows/quality.yml`
(job `frontend-v6`) já estão na `main`. O diretório `docs/patches/`, que
guardava a mudança enquanto ela aguardava autorização, foi removido no mesmo
PR — a Cerca Elétrica validou a Issue #169 (`decision-recorded` + `risk:high`
+ decisão explícita da mantenedora) e liberou os caminhos protegidos.

O bloqueador do corte que esta seção registrava **deixou de existir**: a
auditoria no estado pós-corte simulado passa (`AUDITORIA OK`), provado no #170,
não argumentado.

O #170 foi além de trocar os nomes de arquivo: tornou as 6 asserções que liam
o texto-fonte do `app.js` **tolerantes à modularização**. Onde antes casavam
contra o texto minificado ou um nome de função específico, agora usam regex
tolerante a espaço ou aceitam o nome novo e o antigo — de modo que o mesmo
conteúdo, concatenado a partir de `js/`, continua satisfazendo a regra:

| Asserção | Como sobrevive ao corte |
| --- | --- |
| as três perguntas da ficha | strings preservadas em `js/pages/profile.js` |
| `id="dados-eleitorais"` depois de `id="impacto"` | ordem preservada no markup gerado |
| `type==="proposta"\|\|type==="declaracao"` | regex tolerante a espaço |
| `evidence_type==="atuacao"` com lane própria | regex tolerante a espaço |
| lanes prospectiva/atuação | aceita nomes V5 e V6 (`prospectiveTopicEvidence` etc.) |
| nomes das funções `init*` | `async function init*` em `js/pages/*` |

Cada uma continua **coberta em comportamento** por `profile.spec.js` e
`pages.spec.js`. A auditoria no estado pós-corte simulado passa — foi o que o
#170 provou. Substituir de vez cada `assert ... in app` pelo teste de
comportamento equivalente segue sendo uma melhoria desejável, mas **não é mais
pré-condição do corte**; pode acontecer em slice próprio, depois.

### Linguagem fácil

O rodapé trazia a coluna **"Snapshot"** — palavra em inglês, em todas as sete
páginas, para um público de eleitores capixabas. Virou **"Data dos dados"**.
O restante do vocabulário técnico (`metodologia`, `proveniência`) só aparece
em links para as páginas que existem justamente para explicá-lo, nunca no
caminho principal de quem só quer achar uma candidatura.

### `scripts/cutover-v6.sh`

O corte da Fase 5 é um comando só, com trava de data (recusa rodar antes de
2026-10-04): build, `verify`, suíte de comportamento, substituição da
superfície pública, regeração dos stubs sociais e auditoria pós-corte. O
commit final continua sendo manual e único, como exige
`docs/DELIVERY_GOVERNANCE.md`.


## O que a simulação do corte revelou

Antes de aplicar o patch autorizado por #169, simulei o estado pós-corte na
árvore de trabalho: `styles.css` e `app.js` removidos, `styles/` e `js/` e os
sete HTML vindos de `_site/`. Rodar a auditoria nesse estado encontrou três
problemas que nenhuma leitura de código tinha achado — e que teriam quebrado
o corte no dia 04/10, com o site já no ar.

### 1. Contrato de versão dos assets

`audit-site.py` exigia `styles.css?v=N` **e** `app.js?v=N`, por nome. Na V6 são
várias folhas em `styles/` e vários módulos em `js/`. A regra que importa —
"todo CSS e JS da aplicação carrega com `?v=` explícito, numa única versão em
todo o site" — foi reescrita sem depender de nome de arquivo.

`telemetry.js` ficou explicitamente de fora: é versionado à parte (`?v=1`) de
propósito, com ciclo de vida próprio, e não faz parte do pacote da aplicação.

### 2. `VERSION` andava para trás

`VERSION` era `5.5.0`; a produção publica `?v=5.5.8`. Como a V6 passou a ter
`VERSION` como fonte única do cache-bust — justamente a correção de três
valores divergentes —, o corte teria publicado assets com versão **menor** que
a atual. O navegador de quem já visitou o site não invalidaria o cache: CSS e
JS novos, HTML novo, e o navegador servindo o antigo. `VERSION` foi para
`6.0.0`.

### 3. A V6 tinha perdido a telemetria

As 7 páginas de produção carregam `telemetry.js`; nenhuma página da V6
carregava. O corte teria desligado a medição de audiência silenciosamente.
Restaurada em `base.njk`, na mesma posição e com a mesma versão.

Nada disso aparecia em revisão de código, em teste de página ou em CI. Só
aparece quando se coloca a árvore no estado exato do dia do corte e se roda o
que roda naquele dia. Fica como método para a Fase 5, não como episódio.

## Testes: coletor de erro unificado

Três specs tinham cada uma o seu coletor de `pageerror`/`console`/`response`, e
`candidates.spec.js` ainda trazia um filtro de "ruído externo" próprio, que
ignorava *qualquer* mensagem com `Failed to load resource` — inclusive de asset
nosso.

Agora há um `tests-e2e/externo.js` só. O critério de "terceiro" é a **origem**,
não uma lista de domínios: os retratos das candidaturas já migraram de host uma
vez, e um teste preso a lista desatualizada passa a ignorar o que deveria pegar.
Verificado pelos dois lados: com o filtro ativo, uma folha de estilo nossa
inexistente continua reprovando o teste.

## GitHub Pages: origem não alterada

A troca da origem do Pages para "GitHub Actions" foi autorizada em #169, mas
**não foi feita**: a API de configuração do Pages
(`PUT /repos/{owner}/{repo}/pages`) é recusada pelo proxy de rede do ambiente
do agente, com `403`, e nenhuma ferramenta disponível cobre essa configuração.

Isso não bloqueia o corte. Com a origem em "branch", `scripts/cutover-v6.sh`
escreve a saída do build nos caminhos atuais e o Pages publica como sempre —
exatamente o caminho alternativo já previsto no plano, que não exige nenhuma
mudança de configuração. A troca continua possível depois, com calma, e sem
prazo.
