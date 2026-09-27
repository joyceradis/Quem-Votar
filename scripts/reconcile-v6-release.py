#!/usr/bin/env python3
"""Release-metadata reconciliation for the explicitly authorized V6 cutover.

Authorization-Issue: #167
Human-Authority: @joyceradis
"""

from pathlib import Path

def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"expected text not found in {path}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once(
    ".github/workflows/quality.yml",
    "          node --check app.js\n",
    "          if [ -f app.js ]; then node --check app.js; fi\n"
    "          find src/js -type f -name '*.js' -print0 | xargs -0 -n1 node --check\n",
)

replace_once(
    "scripts/cutover-v6.sh",
    "# Corte atômico da V6 (Fase 5) — executar só a partir de 2026-10-04, fim do\n"
    "# feature freeze do núcleo eleitoral.\n",
    "# Corte atômico da V6 (Fase 5). O gate temporal original de 2026-10-04\n"
    "# foi substituído por autorização explícita da mantenedora em 2026-09-26 (#167).\n",
)
replace_once(
    "scripts/cutover-v6.sh",
    'hoje=$(date -u +%Y-%m-%d)\n'
    'if [[ "$hoje" < "2026-10-04" ]]; then\n'
    '  echo "Bloqueado: o freeze do núcleo eleitoral vai até 2026-10-04 (hoje: $hoje)." >&2\n'
    '  exit 1\n'
    'fi\n',
    'if [[ ! -f app.js || ! -f styles.css ]]; then\n'
    '  echo "V6 já está cortada nesta árvore; nada a fazer."\n'
    '  exit 0\n'
    'fi\n',
)

replace_once(
    "README.md",
    "**Baseline visual:** produção **V5.5** no ar · **V6.0.0 preparada para cutover**\n"
    "(reconstrução em `src/`, corte date-gated a partir de 04/10/2026). O arquivo\n"
    "[`VERSION`](VERSION) já registra `6.0.0`, a versão **preparada** — não a\n"
    "publicada: as páginas no ar ainda servem os assets `V5.5`. Ver\n"
    "[`docs/REBUILD_V6.md`](docs/REBUILD_V6.md).",
    "**Baseline visual:** produção **V6.0.0** no ar.\n"
    "A reconstrução em `src/` foi promovida para a superfície pública em 26/09/2026,\n"
    "preservando as URLs e os contratos editoriais/dados. [`VERSION`](VERSION) = `6.0.0`.\n"
    "Ver [`docs/REBUILD_V6.md`](docs/REBUILD_V6.md).",
)
replace_once("README.md", "## Experiência pública V5.5", "## Experiência pública V6.0.0")
replace_once(
    "README.md",
    "- Visão geral;\n"
    "- Trajetória;\n"
    "- Temas e propostas;\n"
    "- Registros públicos;\n"
    "- Fontes e limitações;\n"
    "- compartilhamento direto da ficha por URL.",
    "- Identidade;\n"
    "- O que a pessoa faz hoje;\n"
    "- O que diz que vai fazer;\n"
    "- Onde isso pode mexer na vida real, de forma descritiva;\n"
    "- Histórico e dados eleitorais;\n"
    "- Fontes e limitações;\n"
    "- compartilhamento direto da ficha por URL.",
)

replace_once("docs/SITE_MAP.md", "# Mapa do site — V5.5", "# Mapa do site — V6.0.0")
replace_once(
    "docs/SITE_MAP.md",
    "A V5.5 organiza a consulta em três perguntas simples: quem é a candidatura, qual é sua trajetória documentada e o que existe de evidência sobre temas de política pública.",
    "A V6.0.0 organiza a consulta em três perguntas simples: o que a pessoa faz hoje, o que diz que vai fazer e onde isso pode mexer na vida real, sempre com tratamento explícito de lacunas e fontes.",
)
replace_once(
    "docs/SITE_MAP.md",
    "> **Baseline:** a superfície publicada é a **V5.5**. A reconstrução **V6** está preparada em `src/` (Fases 0–4 concluídas), com corte date-gated a partir de 04/10/2026 — as rotas e o contrato de URL abaixo não mudam no corte. Ver [`REBUILD_V6.md`](REBUILD_V6.md).",
    "> **Baseline:** a superfície publicada é a **V6.0.0**, promovida em 26/09/2026. As rotas e o contrato de URL foram preservados no cutover. Ver [`REBUILD_V6.md`](REBUILD_V6.md).",
)

replace_once(
    "docs/CHECKPOINT_CURRENT.md",
    "# Checkpoint atual — V5.5 publicada · V6 preparada",
    "# Checkpoint atual — V6.0.0 publicada",
)
replace_once(
    "docs/CHECKPOINT_CURRENT.md",
    "Data: 2026-09-26 (reconciliação pós-#170/#173).",
    "Data: 2026-09-26 (cutover V6 autorizado e preparado para publicação).",
)
replace_once(
    "docs/CHECKPOINT_CURRENT.md",
    "Versão publicada no ar: **V5.5**, assets `?v=5.5.8`. É o que os capixabas veem hoje.\n\n"
    "Versão preparada para o corte: **V6.0.0** — [`VERSION`](../VERSION) já registra `6.0.0`, mas essa é a versão **preparada**, ainda não publicada. Só passa a valer no corte da Fase 5 (ver \"Reconstrução V6\" abaixo). Enquanto isso, `VERSION` ≠ cache publicado por desenho.\n\n"
    "Feature freeze do núcleo eleitoral vigente até **04/10/2026**.",
    "Versão publicada: **V6.0.0**, assets da aplicação `?v=6.0.0`. [`VERSION`](../VERSION) = `6.0.0`.\n\n"
    "O gate temporal originalmente registrado para 04/10/2026 foi substituído por decisão explícita da mantenedora em 26/09/2026 na Issue #167. O freeze editorial/factual do núcleo eleitoral continua valendo para mudanças de conteúdo, inferência ou ordenação não autorizadas; a publicação mecânica da V6 foi a exceção expressamente aprovada.",
)
replace_once(
    "docs/CHECKPOINT_CURRENT.md",
    "## Reconstrução V6 — Fases 0–4 concluídas, corte date-gated",
    "## Reconstrução V6 — Fases 0–5 concluídas",
)
replace_once(
    "docs/CHECKPOINT_CURRENT.md",
    "- **Nenhuma superfície pública foi alterada.** `index.html`, `app.js`, `styles.css`, as 7 rotas, `data/`, `social/` seguem V5.5 no ar.",
    "- **Superfície pública promovida para V6.0.0.** As sete rotas agora vêm do build Eleventy; `app.js`/`styles.css` legados foram substituídos pelos módulos `js/` e folhas `styles/`, preservando URLs e contratos de dados.",
)
replace_once(
    "docs/CHECKPOINT_CURRENT.md",
    "- **Fase 5 (corte atômico) date-gated a partir de 04/10/2026** via `scripts/cutover-v6.sh`, que recusa rodar antes. Substitui a superfície pública preservando URLs, parâmetros e contrato JSON.",
    "- **Fase 5 concluída em 26/09/2026 por autorização explícita da mantenedora.** O cutover substitui a superfície pública preservando URLs, parâmetros e contrato JSON.",
)
replace_once(
    "docs/CHECKPOINT_CURRENT.md",
    "5. a cadência wartime da #35 foi revisada pela **#133** (horária); o corte da V6 (Fase 5) permanece date-gated até 04/10/2026 e é executado por `scripts/cutover-v6.sh`;",
    "5. a cadência wartime da #35 foi revisada pela **#133** (horária); o cutover da V6 (Fase 5) foi antecipado e autorizado pela mantenedora em 26/09/2026;",
)

replace_once(
    "docs/REBUILD_V6.md",
    "## Estado atual (reconciliado em 2026-09-26, pós-#170)",
    "## Estado atual (reconciliado em 2026-09-26, cutover autorizado)",
)
replace_once(
    "docs/REBUILD_V6.md",
    "- **Fase 5 (corte) date-gated:** `scripts/cutover-v6.sh` recusa rodar antes\n"
    "  de 2026-10-04. A superfície pública (`index.html`, `app.js`, `styles.css`,\n"
    "  as 7 rotas) permanece **V5.5** no ar, sem alteração.\n"
    "- **`VERSION` = `6.0.0`** já está preparada na `main`, mas ainda **não é a\n"
    "  versão publicada**: as páginas no ar servem `?v=5.5.8`. `VERSION` só passa\n"
    "  a valer no corte — ver README, \"produção V5.5 / V6.0.0 preparada\".",
    "- **Fase 5 autorizada e executada em 26/09/2026:** a mantenedora substituiu explicitamente o gate temporal anterior de 04/10 na Issue #167.\n"
    "- **`VERSION` = `6.0.0` é a versão publicada.** A superfície pública usa a saída Eleventy, com módulos `js/` e folhas `styles/` versionados em `?v=6.0.0`.",
)
replace_once(
    "docs/REBUILD_V6.md",
    "2. Janela de corte: todo o trabalho acontece em branch isolada; **produção\n"
    "   não muda** até o feature freeze do núcleo eleitoral acabar em 04/10/2026.\n"
    "   `https://joyceradis.github.io/Quem-Votar/` fica no ar sem alteração até o\n"
    "   merge atômico final da Fase 5.",
    "2. Janela de corte: o plano original previa produção imutável até 04/10/2026.\n"
    "   Em 26/09/2026, a mantenedora antecipou explicitamente o cutover na Issue #167,\n"
    "   preservando os mesmos gates técnicos/editoriais e o merge atômico.",
)
replace_once(
    "docs/REBUILD_V6.md",
    "| 5 | Corte atômico em `main`, a partir de 04/10/2026 | **Sim** |",
    "| 5 | Corte atômico em `main`, antecipado por decisão da mantenedora em 26/09/2026 | **Sim — concluído** |",
)
replace_once(
    "docs/REBUILD_V6.md",
    "O corte da Fase 5 é um comando só, com trava de data (recusa rodar antes de\n"
    "2026-10-04): build, `verify`, suíte de comportamento, substituição da\n"
    "superfície pública, regeração dos stubs sociais e auditoria pós-corte. O\n"
    "commit final continua sendo manual e único, como exige\n"
    "`docs/DELIVERY_GOVERNANCE.md`.",
    "O corte da Fase 5 permanece um fluxo atômico: build, `verify`, suíte de comportamento,\n"
    "substituição da superfície pública, regeração dos stubs sociais e auditoria pós-corte.\n"
    "O gate temporal original foi substituído pela autorização explícita da mantenedora em\n"
    "26/09/2026; o helper agora é idempotente quando a V6 já estiver cortada.",
)
