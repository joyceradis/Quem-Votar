# Mapa do site — V5

## Princípio

A V5 organiza a consulta em três perguntas simples: quem é a candidatura, qual é sua trajetória documentada e o que existe de evidência sobre temas de política pública.

## Rotas

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

Parâmetros: `cargo`, `q`, `partido`, `tema`, `institucional=1`, `page`.

### `/temas.html`
Exploração por temas de política pública. A associação candidato-tema existe somente quando há `topic_evidence` individualizada e documentada.

Taxonomia: `data/reference/policy-topics.json`.

### `/candidato.html?id=<SQ_CANDIDATO>&cargo=<cargo>`
Ficha vertical em camadas:
1. Visão geral
2. Trajetória
3. Temas e propostas
4. Registros públicos
5. Fontes e limitações

### `/comparar.html?ids=<SQ_CANDIDATO,...>`
Comparação factual de até 3 candidaturas, sem score, ranking ou vencedor.

### `/sobre.html`
Recorte, snapshot, significado dos temas, fontes e regra de tratamento de lacunas.

## Identidade visual

Azul, branco e rosa formam a identidade visual capixaba do projeto. A home usa presença cromática azul com acento rosa, sem virar coleção de cards. Branco e tons neutros estruturam; azul conduz ações; rosa aparece como acento de marca. Nenhuma cor codifica qualidade, ideologia ou recomendação.

## Dados

Identidade canônica: `SQ_CANDIDATO`.

Fluxo: `fonte -> coleta -> normalização -> vínculo -> snapshot -> interface`.

Snapshot: `data/generated/meta.json`.

Semântica de filtros: `docs/FILTERS.md`.