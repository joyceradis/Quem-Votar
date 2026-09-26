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

- Nova ilustração `assets/v6-penha-line.svg` (+ variante clara
  `assets/v6-penha-line-watermark.svg` para uso sobre fundo escuro):
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
- **Pendente de referência visual:** fonte tipográfica, formato das tags de
  tema e o modo exato de integrar a ilustração no Home (sem uma divisão
  fixa em caixa) ficam para quando a mantenedora compartilhar as
  referências salvas — não foram redesenhados por palpite para evitar
  repetir o mesmo problema que motivou esta reconstrução.
