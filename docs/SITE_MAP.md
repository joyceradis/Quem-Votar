# Mapa do site — V5.5

## Princípio

A V5.5 organiza a consulta em três perguntas simples: quem é a candidatura, qual é sua trajetória documentada e o que existe de evidência sobre temas de política pública.

O mapa descreve superfícies públicas. Rotas técnicas de compartilhamento não substituem a ficha canônica.

> **Baseline:** a superfície publicada é a **V5.5**. A reconstrução **V6** está preparada em `src/` (Fases 0–4 concluídas), com corte date-gated a partir de 04/10/2026 — as rotas e o contrato de URL abaixo não mudam no corte. Ver [`REBUILD_V6.md`](REBUILD_V6.md).

## Rotas públicas

### `/index.html`
- escolha de cargo;
- busca por nome, número ou partido;
- totais e snapshot;
- caminhos por candidatura, tema e comparação;
- acesso aos temas de política pública.

### `/candidatos.html?cargo=federal|estadual`
- 12 candidaturas por página;
- busca dominante;
- filtros progressivos por partido, tema documentado e registro institucional;
- seleção de até 3 candidaturas para comparação.

Parâmetros públicos: `cargo`, `q`, `partido`, `tema`, `institucional=1`, `page`.

### `/temas.html`
Exploração por temas de política pública. A associação candidatura-tema existe somente quando há `topic_evidence` individualizada e documentada.

Taxonomia: `data/reference/policy-topics.json`.

### `/candidato.html?id=<SQ_CANDIDATO>&cargo=<cargo>`
Ficha vertical em camadas, na ordem normativa consolidada pelas #127/#128:

1. Identidade
2. O que a pessoa faz hoje (HOJE)
3. O que diz que vai fazer (PROPÕE)
4. Onde isso pode mexer na vida real (IMPACTO — descritivo, não valorativo)
5. Histórico
6. Dados eleitorais
7. Fontes e limitações

A URL usa o identificador público da candidatura como chave de navegação. A ausência de informação não é convertida em inferência.

### `/comparar.html?ids=<SQ_CANDIDATO,...>`
Comparação factual de até 3 candidaturas, sem score, ranking ou vencedor.

O contrato consolidado inclui normalização de IDs inválidos/duplicados, estado vazio explícito, sincronização entre abas e comportamento preservado em desktop/mobile/teclado.

### `/sobre.html`
Recorte, snapshot, significado dos temas, fontes e regra de tratamento de lacunas.

### `/apoio.html`
Página de sustentabilidade e transparência do apoio ao projeto.

Apoio financeiro não altera fontes, metodologia, ordenação, comparação, evidências ou tratamento das candidaturas.

## Rotas técnicas de compartilhamento

### `/social/<SQ_CANDIDATO>/index.html`
Entrada estática 1:1 por candidatura para metadados Open Graph.

Contrato:
- identidade específica fica restrita aos metadados sociais;
- o `body` não replica conteúdo editorial;
- a rota direciona tecnicamente para a ficha canônica;
- não cria ranking, priorização ou versão paralela da candidatura.

## Sitemap XML

O arquivo público `/sitemap.xml` contém as rotas indexáveis e as fichas canônicas de candidatura. Ele é diferente deste documento arquitetural e não deve ser editado apenas para refletir mudanças de governança interna.

## Identidade visual

Azul, branco e rosa formam a identidade visual capixaba do projeto. Branco e tons neutros estruturam; azul conduz ações; rosa aparece como acento de marca. Nenhuma cor codifica qualidade, ideologia ou recomendação.

## Dados

Identidade canônica: `SQ_CANDIDATO`.

Fluxo público: `fonte → coleta → normalização → vínculo → snapshot → interface`.

Evidência temática: `fonte → staging → validação → revisão → promoção explícita → sync → interface`.

Snapshot: `data/generated/meta.json`.

Semântica de filtros: `docs/FILTERS.md`.

Estado técnico datado: `docs/CHECKPOINT_CURRENT.md`.
