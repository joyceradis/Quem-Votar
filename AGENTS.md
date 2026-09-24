# AGENTS.md — Regras para agentes de código e dados

Este arquivo é normativo para qualquer agente que altere o repositório `Quem-Votar`. Detalhes especializados vivem nos documentos referenciados ao final; este arquivo deve permanecer curto, estável e operacional.

## START HERE — roteador de 60 segundos

1. **Autoridade humana:** `@joyceradis` é a mantenedora e decide produto, escopo, exceções e conflitos.
2. **Papéis separados:** `Executor != Auditor != Release Arbiter`. Quem produz mudança material não certifica o próprio HEAD.
3. **System of record:** GitHub. Issue ativa = contrato; PR = implementação; checks/artifacts/runtime = evidência.
4. **Ordem de leitura:** `main → AGENTS.md → docs/GOVERNANCE.md → Issue/PR ativa → checks/artifacts/runtime`.
5. **Checkpoint é histórico:** `docs/CHECKPOINT_CURRENT.md` nunca prevalece sobre `main`, regra normativa posterior ou contrato ativo mais recente.
6. **Não duplicar trabalho:** confirme lane, owner e HEAD antes de abrir Issue, branch ou PR.
7. **Roteamento:** UI não corrige dados; dados não são alterados para satisfazer UI; lacuna de evidência não é conclusão.
8. **Gate:** sem PASS sem evidência ligada ao SHA aplicável. Mudança material de HEAD invalida prova anterior.

Antes de editar, o agente deve saber: quem decide, qual é a lane, onde registrar, o que não tocar e qual é o próximo gate.

## 1. Objetivo e escopo

Produto cívico factual e rastreável para Eleições Gerais de 2026 no Espírito Santo, atualmente Deputado Federal e Deputado Estadual.

A plataforma **informa; não decide pelo eleitor**.

O núcleo deve continuar extensível a outros cargos sem acoplar regras específicas ao modelo base.

## 2. Regras políticas e editoriais

É proibido implementar:
- score, ranking, “melhor candidato” ou recomendação de voto;
- afinidade percentual ou eliminação por preferência pessoal;
- inferência ideológica por partido, profissão, religião, associação ou cor;
- classificação própria de esquerda/direita/centro/extremos;
- previsão eleitoral;
- ausência de evidência apresentada como ausência de proposta/posição.

É permitido, quando factual e documentado:
- busca e filtros por cargo, partido, nome, número e situação documental;
- histórico eleitoral, partidário e parlamentar;
- temas/posições com evidência individualizada, fonte, data e regra publicada;
- comparação lado a lado sem ordenação valorativa;
- indicadores de cobertura documental.

A interface pública prioriza:
1. o que a pessoa faz hoje;
2. o que diz que vai fazer;
3. onde isso pode mexer na vida real.

A terceira pergunta é descritiva: não implica benefício, prejuízo, recomendação ou preferência.

## 3. Identidade e vínculo

Chave eleitoral canônica: `SQ_CANDIDATO`.

Vínculos entre bases devem ser conservadores:
- preferir identificador oficial;
- na ausência, usar correspondência exata normalizada e registrar o método;
- ambiguidade não gera vínculo.

Nunca criar fluxo/código específico por nome de candidatura. O modelo de evidência é:

`candidate → source → draft → review → evidence`

## 4. Fonte antes de interface

Nenhum novo campo político entra na UI sem:
1. fonte identificada;
2. data de referência;
3. tipo de evidência;
4. regra de normalização;
5. tratamento explícito de ausência;
6. teste contra inferência indevida.

Prioridade de fontes:
1. TSE/TRE;
2. Câmara dos Deputados;
3. ALES;
4. diários/transparência oficiais;
5. documento oficial da candidatura/partido;
6. fonte jornalística secundária, marcada como secundária.

Fonte canônica de evidência temática curada: `data/reference/topic-evidence.json`.

O sync pode anexar essa camada por `SQ_CANDIDATO`; não pode reclassificá-la ou editá-la para satisfazer UI.

## 5. Estados de evidência

Vocabulário:
- `verified`
- `dated`
- `not_integrated`
- `not_available`
- `secondary_source`

Ausência nunca vira zero, posição política ou conclusão.

Uma evidência temática deve preservar, quando aplicável:
`candidate_id`, `topic_id`, `evidence_type`, statement/resumo, fonte/publicador, datas, escopo e `verification_status`.

Privacidade: não publicar CPF, título eleitoral, e-mail pessoal, endereço, telefone, data completa de nascimento ou identificador técnico sem necessidade pública explícita.

## 6. Interface pública

Requisitos mínimos:
- mobile first;
- teclado, foco visível e `prefers-reduced-motion`;
- alvos de toque principais ~44 px;
- aumento de texto sem quebrar layout;
- links compartilháveis e estados claros de loading/erro;
- nenhuma informação importante dependente apenas de cor;
- proveniência acessível, sem dominar a navegação primária.

Linguagem visual:
- editorial, não gamificada;
- azul/branco/navy/cinza como base; rosa apenas como acento de marca;
- cor não comunica ideologia, qualidade ou ranking;
- evitar checkmarks de qualidade, semáforos, bolinhas de status, chips excessivos e cardificação indiscriminada;
- seleção para comparação usa texto (`Comparar` / `Remover`).

Baseline funcional V5/V5.5:
- busca e caminhos principais visíveis;
- snapshot e fonte próximos às contagens;
- 12 resultados por página enquanto este for o contrato vigente;
- filtros secundários progressivos;
- ocupação declarada é metadado e não gera tema;
- tema público deriva apenas de evidência temática documentada.

## 7. Mudança segura e entrega

Branch canônica: `main`.

Toda mudança deve:
- ter objetivo delimitado;
- preservar trabalho válido já existente;
- separar bug de UI, lacuna de dados e erro de normalização;
- evitar reescrever pipeline, modelo de dados e interface na mesma unidade sem necessidade.

Dados gerados não são editados manualmente para “corrigir” a interface.

Antes de consolidar, execute validações aplicáveis: sintaxe, testes, unicidade de `SQ_CANDIDATO`, ausência de sentinelas inválidas e regressões de vínculo/histórico.

Se um PR tocar `data/generated/*`, deve atualizar `docs/CHECKPOINT_CURRENT.md` no mesmo PR enquanto esse contrato estiver vigente.

Snapshots automáticos:
- não usam `[skip ci]`;
- são gerados/auditados antes de integração;
- não escrevem diretamente em `main`;
- entram por PR rastreável e gates normais.

Mudanças protegidas de governança, control plane ou evidência canônica devem referenciar `Authorization-Issue: #N` com decisão humana rastreável.

Após auditoria, **não rebasear** silenciosamente. Se o HEAD material mudar, revalidar.

Para frontend, “pronto” exige comportamento publicado verificado quando aplicável. `CI verde != cobertura completa`; `feature no código != feature validada em produção`.

Commit, deploy e release são conceitos distintos. Release formal exige tag/release correspondente.

Código de terceiros só entra com licença compatível identificada; não copiar HTML/CSS/JS proprietário usado apenas como referência visual.

## 8. Governança multiagente

Ordem de autoridade:
1. `main`;
2. `AGENTS.md`;
3. `docs/GOVERNANCE.md`;
4. contrato ativo da Issue/PR;
5. checks, artifacts e runtime ligados ao SHA aplicável;
6. `docs/CHECKPOINT_CURRENT.md` como histórico;
7. instrução da tarefa atual, se não contrariar os itens anteriores.

Antes de executar:
- ler este arquivo e `docs/GOVERNANCE.md`;
- ler a Issue/PR da lane;
- confirmar owner e HEAD;
- inspecionar apenas os arquivos necessários;
- consultar checkpoint/roadmap quando histórico ou dependência macro for necessário.

Uma lane ativa tem **um executor por mudança**. Outro agente só entra com handoff explícito.

Issues `status:in-progress` autorizam execução técnica dentro do escopo já aprovado: branches, PRs, testes, correções de CI, staging, coletores e documentação técnica não exigem nova autorização a cada etapa.

Parar para decisão humana quando houver:
1. mudança de governança/control plane;
2. publicação de nova evidência política canônica;
3. mudança destrutiva/irreversível relevante;
4. conflito de contratos ou ambiguidade real de produto;
5. decisão final de publicação ou mudança de escopo.

Agentes persistentes/bots com escrita devem usar permissão mínima, histórico de ações e desativação simples. Merge destrutivo silencioso é proibido.

## 9. Feature freeze e sustentabilidade

Durante o freeze V5.5, o núcleo eleitoral permanece congelado salvo correção, segurança, acessibilidade, disponibilidade, atualização factual ou proveniência.

Núcleo eleitoral inclui busca, fichas, comparação, temas/taxonomia, regras editoriais, `topic_evidence`, publicação canônica e qualquer mudança que altere ordem, visibilidade, tratamento ou interpretação de candidaturas.

A camada de sustentabilidade pode evoluir separadamente (`FUNDING.yml`, Sponsors, `apoio.html`, PIX, transparência), desde que:
- não altere conteúdo/metodologia/ordem de candidaturas;
- não apareça dentro de ficha, busca, comparação ou tema;
- não use tracker publicitário, personalização política ou segmentação;
- não conceda influência editorial a apoiadores;
- não escreva em `topic-evidence.json`.

## 10. Topologia de trabalho

Função dos artefatos:
- `README.md`: produto estável, não backlog;
- `AGENTS.md` + `docs/GOVERNANCE.md`: normas;
- `docs/ROADMAP_V1.md`: ordem macro;
- `docs/CHECKPOINT_CURRENT.md`: snapshot técnico datado;
- Issue: contrato/resultado;
- Tracking Issue: coordenação de frente;
- comentário: evidência, finding, decisão ou handoff;
- PR/commit: implementação.

Antes de criar Issue/PR:
1. pesquisar unidades equivalentes;
2. reutilizar lane existente quando couber;
3. atribuir uma responsabilidade principal;
4. registrar dependências;
5. não duplicar critério de pronto.

Não misturar, salvo tracker explícito: descoberta, coleta, confiabilidade, revisão semântica, exceções, publicação canônica, decisão arquitetural e governança.

Dependência explícita prevalece sobre conveniência. Não contornar Issue bloqueadora para “andar mais rápido”.

## Referências especializadas

- `docs/GOVERNANCE.md`: proveniência, editorial, multiagente e fail-closed.
- `docs/DELIVERY_GOVERNANCE.md`: entrega técnica, pré/pós-auditoria e deploy.
- `docs/FILTERS.md`: semântica de filtros e comparação.
- `docs/DESIGN_REFERENCES.md`: referências visuais/licenças.
- `docs/PRODUCT_NORTH_STAR.md`: objetivo e linguagem pública.
- `docs/ROADMAP_V1.md`: dependências macro.
- `docs/CHECKPOINT_CURRENT.md`: histórico técnico datado.

Quando houver conflito, aplique a ordem de autoridade acima; não use documentação antiga para sobrescrever estado mais novo.
