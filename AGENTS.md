# AGENTS.md — Regras para agentes de código e dados

Este arquivo é normativo para qualquer agente que altere o repositório `Quem-Votar`.

## 1. Objetivo do produto

Construir uma plataforma cívica capixaba para consulta factual e rastreável de candidaturas, histórico eleitoral, atuação institucional e fontes públicas.

A plataforma informa. Ela não decide pelo eleitor.

## 2. Escopo atual

- Eleições Gerais de 2026
- Espírito Santo
- Deputado Federal
- Deputado Estadual

A arquitetura deve permanecer extensível para Senado, Governo do Estado e Presidência sem acoplar regras específicas desses cargos ao núcleo do produto.

## 3. Regras políticas do produto

Não implementar:

- score de candidato;
- ranking;
- recomendação de voto;
- "melhor candidato";
- afinidade percentual;
- eliminação automática de candidatos com base em preferências pessoais;
- classificação própria de esquerda, direita, centro ou extremos;
- inferência ideológica a partir de partido, religião, profissão ou associação;
- previsão de eleição.

Pode implementar:

- filtros factuais por cargo, partido e situação documental;
- busca por nome/número;
- páginas temáticas com documentos e declarações identificadas por fonte, autor e data;
- histórico partidário documentado;
- histórico eleitoral;
- atuação parlamentar documentada;
- links para fontes primárias;
- indicadores de cobertura de dados.

## 4. Fonte antes de interface

Nenhum novo campo político entra na UI sem:

1. fonte identificada;
2. data de referência;
3. tipo de evidência;
4. regra de normalização;
5. tratamento de ausência;
6. teste contra inferência indevida.

Prioridade:
1. TSE/TRE
2. Câmara dos Deputados
3. ALES
4. diários e transparência oficiais
5. documentos oficiais do candidato/partido
6. fonte jornalística secundária, explicitamente marcada

## 5. Estados de evidência

Usar apenas:
- `verified`
- `dated`
- `not_integrated`
- `not_available`
- `secondary_source`

Nunca converter ausência em zero.

## 6. Temas e posições

A futura camada temática deve armazenar evidências, não rótulos opinativos.

Fonte canônica para evidências curadas: `data/reference/topic-evidence.json`. O sync deve anexar essa camada por `SQ_CANDIDATO` sem editá-la.

Modelo mínimo:
- `topic_id`
- `candidate_id`
- `evidence_type`
- `statement`
- `source_url`
- `source_title`
- `source_publisher`
- `published_at`
- `captured_at`
- `scope`
- `quote_or_summary`
- `verification_status`

Não criar `ideology_score`, `affinity_score` ou `recommended_for_user`.

## 7. Identidade e deduplicação

Chave eleitoral primária: `SQ_CANDIDATO`.

Vínculo entre bases institucionais deve ser conservador. Preferir identificador oficial; quando inexistente, usar correspondência nominal exata normalizada e registrar o método.

Correspondência ambígua não gera vínculo.

## 8. Privacidade

Não publicar dados pessoais desnecessários:
- CPF
- título eleitoral
- e-mail pessoal
- endereço
- data completa de nascimento
- telefone
- identificadores técnicos usados apenas para junção

## 9. Frontend

Requisitos:
- mobile first;
- acessibilidade por teclado;
- foco visível;
- `prefers-reduced-motion`;
- sem animação que impeça leitura;
- links compartilháveis para fichas;
- estados de carregamento e erro explícitos;
- nenhuma métrica sem fonte.

## 10. Alterações seguras

Antes de mergear:
- executar validação de sintaxe;
- conferir 137/410 apenas enquanto forem as contagens do snapshot vigente, sem hardcode permanente;
- validar unicidade de `SQ_CANDIDATO`;
- verificar ausência de sentinelas TSE;
- verificar que dados institucionais antigos não foram promovidos a mandato atual;
- impedir regressão de histórico por falha transitória de API.

## 11. Commits

Usar prefixos:
- `feat:`
- `fix:`
- `data:`
- `docs:`
- `ci:`
- `ux:`
- `refactor:`

Snapshots automáticos **não** usam `[skip ci]`. O sync executa testes e auditoria em modo read-only, gera um snapshot candidato como artifact e não escreve diretamente em `main`. A integração do snapshot na branch canônica ocorre por PR rastreável, sujeito aos mesmos gates da entrega.


## 12. Código de terceiros

Não copiar código de referência sem licença explícita compatível.

Antes de incorporar componente externo:
- identificar repositório e licença;
- registrar atribuição quando exigida;
- preferir implementação própria para padrões simples de interação;
- não copiar HTML/CSS/JS proprietário de sites usados apenas como benchmark visual.

Referências de UX ficam em `docs/DESIGN_REFERENCES.md`. Regras de entrega e pós-deploy ficam em `docs/DELIVERY_GOVERNANCE.md`. O objetivo e a linguagem pública do produto ficam em `docs/PRODUCT_NORTH_STAR.md`.


## 13. Governança operacional — entrega rápida com rastreabilidade

Estas regras existem para permitir que vários agentes trabalhem no projeto sem transformar rapidez em regressão.

### Fonte de verdade
- branch canônica de entrega: `main`;
- dados gerados não são editados manualmente para corrigir a UI;
- `SQ_CANDIDATO` permanece a identidade eleitoral canônica;
- documentação normativa não é substituída silenciosamente por decisões ad hoc de um agente.

### Antes de alterar
1. ler este arquivo e `docs/GOVERNANCE.md`;
2. inspecionar o estado atual dos arquivos afetados;
3. distinguir bug de interface, lacuna de dados e erro de normalização;
4. preservar trabalho válido já existente.

### Regra de mudança
- uma alteração deve ter objetivo delimitado;
- não reescrever pipeline, modelo de dados e interface ao mesmo tempo sem necessidade;
- mudanças visuais não podem inventar significado político;
- identidade visual de partido, quando usada, deve vir de fonte oficial e ser tratada como identidade partidária, não como classificação criada pela plataforma;
- dados faltantes continuam faltantes: placeholder visual não equivale a dado integrado.

### Critério de pronto
Uma mudança só pode ser descrita como pronta quando:
- código foi persistido no repositório;
- sintaxe/validação aplicável passou;
- Pages/deploy correspondente concluiu com sucesso;
- o comportamento publicado foi verificado quando a mudança for de frontend;
- limitações conhecidas foram registradas;
- todo PR que toque `data/generated/*` atualiza `docs/CHECKPOINT_CURRENT.md` no mesmo PR, mesmo quando a alteração preserve as contagens, para manter rastreabilidade entre snapshot publicável e checkpoint.

`CI verde != cobertura de dados completa`.
`feature no código != feature validada em produção`.
`placeholder != integração`.

### Auditoria por outro agente
Outro agente deve conseguir responder, apenas pelo repositório:
- qual é o estado canônico;
- o que mudou;
- qual fonte sustenta cada camada de dados;
- o que está integrado;
- o que está pendente;
- quais validações passaram;
- quais limitações permanecem.

Não esconder pendências para produzir aparência de conclusão.

## 14. Versionamento

Há três conceitos distintos:
- **commit**: mudança incremental;
- **deploy**: versão publicada pelo GitHub Pages;
- **release**: marco estável explicitamente versionado.

Não chamar uma sequência de commits de “V2” ou “V3” como se fosse release formal sem tag/release correspondente.

A branch canônica de entrega é `main`, mas alterações destinadas a ela devem ser desenvolvidas em branch e integradas por Pull Request conforme o ruleset ativo. Uma entrega lógica de frontend deve ser persistida como commit atômico; não fracionar cache-bust ou a mesma revisão visual em vários commits. Mudanças estruturais de alto risco continuam exigindo branch isolada, checkpoint recuperável e revisão proporcional ao risco.


## 15. Filtros, temas e comparação

Filtros podem reduzir o universo por **dados factuais/documentados**, sem ordenar valorativamente os candidatos.

Permitido:
- cargo, partido, nome e número;
- tema de política pública somente quando houver evidência temática individualizada e documentada;
- existência de mandato/vínculo/evidência institucional;
- existência de evidência temática documentada;
- posição documentada favorável/contrária a um tema, quando o registro possuir fonte, data e regra de classificação publicada;
- comparação lado a lado de campos documentais.

Não permitido:
- transformar filtros em score de afinidade;
- ordenar por “mais compatível”;
- perguntar preferências políticas pessoais para recomendar candidato;
- inferir posição temática pela legenda, profissão ou cor do card;
- tratar ausência de evidência como “não tem proposta” sem cobertura completa auditada.

A semântica operacional dos filtros fica em `docs/FILTERS.md`.

## 16. Acessibilidade de decisão

Para o fluxo eleitoral público:
- listagem deve ser paginada; padrão atual: 12 cards por página;
- controles principais devem ter alvo de toque de pelo menos ~44 px;
- oferecer aumento de texto sem quebrar layout;
- formulários relacionados devem ser agrupados semanticamente;
- evitar depender apenas de cor para transmitir informação;
- texto da interface deve ser curto e em português claro;
- fontes detalhadas ficam acessíveis, mas não devem dominar a navegação primária.

## 17. Semântica de cor

A identidade visual do projeto usa azul, branco e rosa, em referência à identidade capixaba já documentada. A base estrutural permanece branca/azul/navy/cinza; rosa aparece apenas como acento de marca, sem carregar significado político, de cargo, qualidade ou status.\n\nNão usar vermelho, verde, rosa ou qualquer gradiente estrutural para sugerir esquerda/direita/centro. Identidade visual partidária, se incorporada, precisa ser documentada como identidade da própria legenda e não como classificação ideológica produzida pela plataforma.


## 18. Regra visual da interface pública

A interface consolidada usa linguagem editorial, não gamificada.

Não reintroduzir:
- checkmarks como indicador de qualidade, completude ou seleção;
- bolinhas/status circulares decorativos;
- chips em excesso para dados básicos;
- cards arredondados empilhados como padrão para toda informação;
- vermelho/rosa ou verde como cor estrutural de cargo, qualidade ou orientação;
- ícones sem função informacional.

Preferir:
- tipografia e hierarquia;
- linhas divisórias;
- tabelas/listas editoriais;
- texto explícito;
- retângulos simples;
- navegação por páginas;
- comparação lado a lado.

Seleção para comparação deve usar texto como `Comparar` / `Remover`, não símbolo de aprovação.


## 19. Contrato visual V5

A V5 é o baseline de interface.

Requisitos:
- cargo, busca e caminhos principais visíveis sem parede de texto;
- snapshot datado e fonte TSE próximos das contagens;
- 12 resultados por página;
- busca dominante e filtros secundários progressivos;
- ficha vertical expansível com Visão geral, Trajetória, Temas e propostas, Registros públicos e Fontes;
- ocupação declarada é metadado; nunca gera tema;
- tema público só deriva de `topic_evidence` documentada;
- fonte auxiliar legível; não reduzir proveniência a texto minúsculo;
- ausência de checks, score, ranking e semáforo visual de qualidade;
- azul, branco e rosa compõem a identidade visual; rosa é apenas acento de marca, nunca significado político;
- ícones são funcionais e mínimos.


## 20. Governança multiagente

Este repositório pode ser alterado por diferentes agentes e sessões de IA. Nenhum agente, modelo ou conversa é fonte de verdade isolada.

### Ordem de autoridade
1. estado atual da branch canônica `main`;
2. `AGENTS.md`;
3. `docs/GOVERNANCE.md`;
4. `docs/CHECKPOINT_CURRENT.md`;
5. contratos e testes automatizados;
6. instrução específica da tarefa atual, desde que não contradiga os itens anteriores.

O checkpoint registra um estado datado. Se estiver desatualizado em relação à `main` ou a uma regra normativa posterior, ele não autoriza rollback.

### Regra de contexto
Antes de qualquer mudança substancial, o agente deve:
- ler este arquivo;
- ler `docs/GOVERNANCE.md` e `docs/CHECKPOINT_CURRENT.md`;
- inspecionar os arquivos diretamente afetados;
- distinguir estado atual de documentação histórica;
- preservar trabalho válido já consolidado.

Nenhum agente pode “corrigir” um estado que não compreendeu. Falta de contexto não autoriza reconstrução, rollback, substituição de arquitetura ou inferência.

### Risco proporcional
- **baixo risco**: CSS, copy, acessibilidade, documentação e bug local usam PR de menor escopo, após validação aplicável;
- **médio risco**: filtros, comparação, navegação, estrutura de página e comportamento de UI exigem preservação dos contratos e auditoria antes de serem declarados prontos;
- **alto risco**: pipeline eleitoral, normalização, `SQ_CANDIDATO`, vínculo TSE/Câmara/ALES, proveniência, privacidade e semântica de evidências exigem checkpoint e revisão explícita antes de consolidação.

### Conflito entre agentes
Sugestão de agente não revoga decisão documentada. Em conflito:
- primeiro aplicar os contratos do repositório;
- depois preservar o checkpoint canônico;
- se o conflito continuar, a decisão é humana.

### Identidade e rastreabilidade
Para alterações de alto risco, o registro da alteração deve permitir identificar:
- agente responsável;
- escopo da alteração;
- instrução de origem, como regra deste arquivo, checkpoint ou issue aplicável.

Para alterações de baixo e médio risco, essa identificação não é obrigatória.

### Agentes persistentes
Bot, Action, GitHub App ou automação com credencial de escrita deve ter:
- escopo mínimo de permissão e, quando tecnicamente aplicável, paths permitidos;
- histórico de ações;
- forma simples e documentada de desativação;
- proibição de merge destrutivo silencioso.

Sessões interativas não exigem kill switch.

### Autonomia operacional delegada

Issues marcadas como `status:in-progress` autorizam execução técnica contínua dentro do escopo aprovado, sem necessidade de nova autorização humana a cada etapa intermediária.

Essa autonomia inclui:

- criação de sub-issues;
- criação de branches e Pull Requests;
- correção de falhas de CI;
- ajustes e refatorações necessárias para cumprir o escopo;
- implementação e ajuste de coletores;
- criação e manutenção de camadas de staging;
- tratamento de formatos e fontes, como HTML, JSON, CSV e PDF;
- testes, validações e documentação técnica;
- investigação e correção de bloqueios técnicos encontrados durante a execução.

O agente deve continuar avançando autonomamente enquanto a próxima ação for consequência técnica razoável do escopo já aprovado.

Não é necessária nova autorização humana para cada commit, sub-issue, correção, teste ou PR intermediário.

### Gates humanos obrigatórios

A execução deve parar e solicitar decisão explícita da mantenedora quando houver:

1. alteração das regras de governança ou do control plane;
2. publicação de nova evidência política na fonte canônica;
3. mudança destrutiva ou irreversível relevante;
4. conflito entre contratos ou ambiguidade de produto que não possa ser resolvida pelo estado canônico do repositório;
5. funcionalidade completa que dependa de decisão final de publicação, consolidação ou mudança de escopo.

Descobrir uma limitação técnica durante a execução não constitui, por si só, motivo para interromper o trabalho. O agente deve registrar a limitação, criar a sub-issue apropriada quando necessário e continuar pelo próximo caminho seguro disponível.


## 21. Norte de produto público

A interface pública prioriza três perguntas: o que a pessoa faz hoje, o que diz que vai fazer e onde isso pode mexer na vida real.

Não transformar essa terceira pergunta em recomendação personalizada, score, ranking ou conclusão de benefício/prejuízo. A explicação de impacto é descritiva e vinculada a propostas/documentos com fonte.

Jargão técnico de governança de dados fica fora do primeiro nível da interface.


## 22. Limites do feature freeze e camada de sustentabilidade

Durante o feature freeze da V5.5, o congelamento se aplica ao **núcleo eleitoral do produto**, não a toda e qualquer superfície operacional do repositório.

### Núcleo eleitoral congelado

Permanecem congelados, salvo correção, segurança, acessibilidade, disponibilidade, atualização factual ou proveniência:

- busca e navegação eleitoral;
- fichas de candidaturas;
- comparação;
- temas e taxonomia política;
- regras editoriais;
- `topic_evidence` e sua semântica;
- pipeline de publicação canônica;
- qualquer mudança que altere ordem, visibilidade, tratamento ou interpretação de candidaturas.

### Camada de sustentabilidade isolada

Pode evoluir durante o freeze quando a alteração for estritamente separada do conteúdo eleitoral:

- `.github/FUNDING.yml`;
- GitHub Sponsors;
- seção de apoio no README;
- rota estática `apoio.html`;
- botão local de copiar PIX;
- documentação de transparência e sustentabilidade;
- link secundário de apoio em rodapé.

### Invariantes da camada financeira

- apoio financeiro nunca altera fontes, dados, metodologia, classificação, ordem ou apresentação de candidaturas;
- nenhum CTA financeiro pode aparecer dentro de ficha de candidato, busca, comparação ou páginas temáticas;
- não usar trackers publicitários, personalização política ou segmentação;
- valor financeiro não determina destaque;
- candidatura, campanha, partido, federação, coligação, comitê eleitoral ou intermediário desses atores não deve ser tratado como apoiador institucional neutro;
- a camada financeira não escreve nem modifica `data/reference/topic-evidence.json`;
- nenhuma mudança dessa camada reduz os gates humanos exigidos para publicação de evidência política.

A prioridade operacional durante o freeze continua sendo factualidade, proveniência e a frente de evidências #5/#2.


## 23. Governança executável

Regras críticas precisam de enforcement técnico sempre que a plataforma permitir.

- indisponibilidade transitória de fonte institucional não pode apagar enriquecimento previamente validado;
- sem estado anterior seguro, pipelines de snapshot devem falhar fechados em vez de publicar vazio;
- mudanças de governança, control plane ou evidência canônica em PR devem referenciar uma Issue de autorização por `Authorization-Issue: #N`;
- a Issue de autorização deve conter decisão explícita da mantenedora;
- `[skip ci]` é proibido em commits que alterem o estado público;
- rebase pós-auditoria é proibido: se `main` avançar durante um sync, o run deve abortar e ser regenerado;
- espelhos de dados devem usar revisão imutável e hash do conteúdo efetivamente processado;
- testes do pipeline fazem parte do significado de `CI verde`.

A proteção/ruleset da branch `main` é uma configuração externa do GitHub e deve ser verificada no estado real do repositório. No estado canônico atual, o ruleset `Protecao-da-Main` está ativo, sem bypass, exige Pull Request e os checks `audit` e `🛑 Inspetor de Regras da IA`. Divergência entre essa configuração, a documentação e `docs/CHECKPOINT_CURRENT.md` é drift de control plane e deve bloquear integração até reconciliação.


## 24. Topologia canônica de trabalho

A documentação e as Issues têm responsabilidades diferentes e não devem competir como fontes de verdade.

### Função de cada artefato

- `README.md`: estado estável do produto; não é backlog;
- `AGENTS.md` e `docs/GOVERNANCE.md`: regras normativas;
- `docs/ROADMAP_V1.md`: ordem macro, dependências e frentes;
- `docs/CHECKPOINT_CURRENT.md`: estado técnico datado da `main`;
- Issue de produto: resultado que precisa existir;
- Tracking Issue: coordena uma frente e suas dependências;
- Issue executável: uma responsabilidade principal com critério de pronto próprio;
- comentário: progresso, descoberta ou decisão dentro da Issue;
- PR/commit: implementação efetivamente proposta/persistida.

### Antes de criar Issue

1. pesquisar Issues abertas e fechadas por termos equivalentes;
2. identificar se a necessidade pertence a uma Issue existente;
3. se for nova, escolher uma única responsabilidade principal;
4. registrar relação com parent/tracking quando existir;
5. não duplicar critérios de pronto de outra Issue.

### Regra de decomposição

Uma Issue não deve misturar, salvo tracking explícito:

- descoberta de fontes;
- coleta;
- confiabilidade/reprocessamento;
- revisão semântica;
- fila de exceções;
- publicação canônica;
- decisão arquitetural;
- governança do repositório.

Essas responsabilidades possuem risco e critérios de pronto diferentes.

### Regra de escala

Não criar código específico por candidatura (`candidato_x.py`, fluxos especiais ou exceções codificadas por nome).

O modelo é:

`candidate → source → draft → review → evidence`

e a execução ocorre sobre o universo de `SQ_CANDIDATO`.

### Regra de prioridade

Dependência explícita prevalece sobre conveniência. Uma Issue marcada como bloqueada não deve ser executada em massa contornando a Issue que a bloqueia.

Se um agente encontrar uma dependência ausente, deve registrá-la e ajustar o mapa de execução antes de escalar o trabalho.
