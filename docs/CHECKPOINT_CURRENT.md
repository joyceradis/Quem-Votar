# Checkpoint atual — V5.5

Data: 2026-09-25.

Estado auditado a partir de `main` em `c7760b33d4b93538b1374eedce1d8830b1a326a9` (PR #139 já integrado). Este checkpoint é atualizado por PR documental e, por isso, o merge documental subsequente pode avançar o SHA sem alterar o estado de produto descrito.

## Estado canônico

Branch: `main`.

Versão de produto: `5.5.0` ([`VERSION`](../VERSION)).

Baseline visual: V5.5.

Cache atual de assets públicos: `5.5.8`.

Feature freeze do núcleo eleitoral vigente até **04/10/2026**.

O produto informa e documenta. Não produz score, ranking, vencedor, previsão eleitoral ou recomendação de voto.

## Ficha por três perguntas, navegação e curadoria por recência — #127/#128, #138/#139, #35/#146 (2026-09-24/25)

Registro operacional para orientar agentes que chegarem depois: o que foi feito, por quem e onde está o estado, sem duplicar auditoria já concluída.

### #127/#128 — ficha reorganizada em HOJE → PROPÕE → IMPACTO

**Status: mergeado e publicado.** Merge commit `02cf25399b04330b0a79fd59c3cffa634f8b1472` em `main`.

- arquitetura da ficha: `IDENTIDADE → HOJE → PROPÕE → IMPACTO → HISTÓRICO → DADOS ELEITORAIS → FONTES`;
- ocupação TSE tratada como metadado, nunca como HOJE (`currentActivity()` não lê mais `candidate.occupation`);
- PROPÕE aceita somente `evidence_type=proposta|declaração`; atuação documentada fica em **Histórico → Atuação pública documentada**, nunca em PROPÕE/IMPACTO;
- gate final: Quality + Cerca + CommitCheck verdes no HEAD `fd57e5a3f7f52de172e8bfb7a96b4ba452552bd1`; runtime UI real pós-harness (#136) contra esse HEAD — run `36088073371`, `overall=PASS merge_gate=PASS`, 16/16 cenários, 0 erro material; artifact `10844568605` reconciliado (digest e manifest conferidos por três verificações independentes antes do merge);
- `pages build and deployment` do merge commit — run `36089534940` — **PASS**.

### #138/#139 — navegação direta em desktop + Home enxuta

**Status: mergeado e publicado.** Merge commit `c7760b33d4b93538b1374eedce1d8830b1a326a9` em `main` (base retargetada de `ux/127-three-questions` para `main` após o merge da #128).

- `.desktop-nav` visível a partir de 980px (`Pessoas | Assuntos | Comparar | Como funciona`), botão do drawer oculto quando a navegação direta cabe;
- mobile preserva o drawer; `Menu` ganhou contraste forte + `☰`;
- `aria-current="page"` com indicador não cromático (`text-decoration:underline`) além de cor;
- validação browser final feita localmente (Playwright/Chromium pré-instalado do ambiente, checkout isolado do HEAD exato via `git worktree`, servido em loopback) por não caber no `runtime-proof.yml` oficial — a matriz oficial é centrada na ficha do candidato (#128/`app.js`), não em nav/Home; 47/47 checks PASS, 0 erro material (`HANDOFF: CLAUDE_139_BROWSER_PASS`, PR #139);
- `Qualidade do site` e `pages build and deployment` do merge commit — runs `36090891177` e `36090890369` — **PASS**.

### #35/#146 — recência dentro da curadoria candidate-fair

**Status: PR #146 aberta/DRAFT, aguardando auditoria independente.** Branch `fix/35-curation-recent-first`, HEAD `c876468390edaa463b0d6657b2d7f3627198a73e`, base `main` atual (reconciliada sem conflito, diff restrito a `scripts/build_curation_batch.py` + `tests/test_wartime_throughput.py`).

- finding original: dentro da mesma lane/prioridade documental, o batch ordenava por `published_at` ascendente, então itens de 2023 venciam sistematicamente itens de 2025/2026 das mesmas 7 candidaturas Câmara (artifact `10825249130`, 81/81 selecionados eram de 2023);
- mudança: dentro da mesma lane/prioridade, a data válida mais recente vem primeiro; datas ausentes ficam atrás de datas válidas; recência nunca aprova, rejeita, pontua ou desqualifica — é só desempate;
- **finding 1 corrigido**: `publication_recency_key` aceitava qualquer string de 8 dígitos como data (ex.: `"2026-13-40"`, mês inexistente) — agora valida calendário real via `datetime.strptime`;
- **finding 2 corrigido** (encontrado pela auditoria independente): o bucket "tem data vs. não tem" usava uma checagem de string separada (`clean(published_at) == ""`) da usada por `publication_recency_key`, e uma data inválida não vazia ordenava **antes** de uma data ausente (`False < True`). Corrigido derivando o bucket diretamente de `publication_recency_key(row) == 0`, eliminando a segunda fonte de verdade;
- testes cobrindo os 4 casos exigidos (válida, inválida, ausente, empate) em `tests/test_wartime_throughput.py`; o teste do finding 2 foi verificado localmente como discriminante (falha contra o código anterior via `git stash`, passa com a correção);
- preservado sem alteração: lane/source quality, prioridade documental, round-robin candidate-fair, per-candidate limit, desempate por URL/draft_id, dedupe candidate-aware, `autoapproval=false`, zero canonical write;
- checks no HEAD atual: CommitCheck/Quality/Cerca **PASS**; passo de governança da Cerca (`scripts/audit-site.py` é caminho protegido, mas não faz parte do diff desta PR) veio `skipped`;
- **não mergeada.** Aguardando reconciliação da auditoria independente sobre o finding 2; PR permanece DRAFT por decisão da mantenedora.

Handoffs completos com evidência (runs, digests, hashes) estão nos comentários das respectivas PRs, não duplicados aqui.

## Snapshot eleitoral público

Universo atual:

- **547 candidaturas**;
- **137** para Deputado Federal;
- **410** para Deputado Estadual;
- **7** vínculos atuais com mandato federal na Câmara preservados;
- **26** evidências institucionais ALES 2025 vinculadas;
- **22** evidências temáticas canônicas em `data/reference/topic-evidence.json`.

`SQ_CANDIDATO` permanece a chave eleitoral canônica.

Nenhuma contagem acima deve ser tratada como avaliação de candidatura ou completude política.

## Contrato de situação da candidatura

A sentinela TSE `#NE` não é interpretada como situação jurídica.

Quando a fonte atual não resolve `DS_SITUACAO_CANDIDATURA`, o snapshot publica:

```
registration_status = "not_available"
```

A ficha traduz esse estado como **“Ainda não disponível na fonte atual”**.

Regras:

- sentinela não vira `null` silencioso;
- ausência não vira deferimento, regularidade, indeferimento ou qualquer conclusão jurídica;
- `audit-site.py` falha se `registration_status` desaparecer em `null` ou vazio;
- `#NE` e `#NULO` continuam proibidos no snapshot público.

Correção consolidada pela #91 / PR #92.

## Interface e distribuição

O contrato público continua:

- busca por nome/número;
- filtro factual por cargo e demais campos documentados;
- 12 resultados por página;
- comparação lado a lado de até 3 candidaturas;
- ficha vertical por camadas;
- temas somente quando há evidência documentada;
- ausência de evidência não é convertida em ausência de posição.

### Comparação

A #107 foi concluída após estabilização do funil factual de comparação pelo PR #112.

Estado validado em produção:

- seleção de até 3 candidaturas;
- feedback acessível de seleção/remoção e limite;
- foco preservado nas interações cobertas;
- normalização de URLs inválidas/duplicadas;
- `?ids=` vazio não reutiliza seleção antiga;
- sincronização entre abas;
- desktop, teclado e mobile 390×844 verificados em Chromium real;
- Quality pós-merge: run `35813620149` — **PASS**;
- Pages do merge: run `35813619940` — **PASS**;
- E2E de produção: run `35813830689` — **8/8 PASS**.

Merge canônico: `b4d314f22d513db0011e5718a179c6df4a7dc0ec`.

### Compartilhamento social

A limitação anterior de Open Graph dinâmico foi corrigida pela #93 / PR #94.

Estado atual:

- **547/547** candidaturas possuem entrada estática `/social/<SQ_CANDIDATO>/index.html`;
- geração é 1:1, sem seleção ou priorização de candidaturas;
- identidade específica da candidatura fica restrita aos metadados `og:*`;
- wrappers possuem `body` vazio e redirecionam tecnicamente para a ficha canônica;
- nenhum conteúdo visível de ficha, busca, comparação ou temas foi duplicado ou reformulado;
- artifact do GitHub Pages do deploy pós-merge contém as 547 páginas;
- Pages build/deploy do commit `e88c365ec013a0dbf1b60b21c21ea78ac696b545` concluiu com sucesso no run `35667171810`.

### Telemetria

Google Analytics 4 está instalado no site público com Measurement ID `G-2KY1FDKV88`.

A #108 permanece **aberta e bloqueada**. O PR #113 foi fechado **sem merge** e sua barreira client-side não está em `main`.

Estado comprovado até este checkpoint:

- GA4 Admin verificado;
- pageviews automáticos por alterações de histórico: desligados;
- Site Search: desligado;
- Data Redaction de e-mail: ativa;
- Data Redaction de query: ativa para `id`, `ids`, `q`, `tema`, `partido`, `cargo`, `page` e `institucional`;
- matriz real do HEAD #113: run `35812949635` — cenários principais sem dados proibidos;
- falsificação estrita de outbound click: run `35813126591` — `OUTBOUND_CLICK_NOT_OBSERVED`;
- matriz repetida após reconciliação com #112: run `35814096977` — outbound click continuou não observável.

Consequência: o gate de privacidade permanece incompleto. Não existe autorização para promover #113, ressuscitá-lo ou abrir substituto apenas para contornar a ausência de prova. A direção registrada na #108 é reduzir primeiro a superfície automática do GA4 no plano administrativo e repetir o gate empírico antes de nova implementação.

A telemetria não pode transmitir identidade de candidatura, busca, tema, partido, listas de IDs ou produzir interpretação política.


## Harness canônico de runtime — #117 / PR #118

O primeiro slice da #117 foi integrado em `main` pelo PR #118.

Escopo deste slice:

- validação UI sobre checkout de SHA/ref explícito;
- execução somente em loopback;
- bloqueio de saída não-loopback no browser;
- isolamento por `browserContext`;
- teardown fail-closed com observação de lifecycle;
- espera determinística de render assíncrono;
- artifact canônico com manifest e screenshots diagnósticas;
- `merge_gate=PASS|FAIL`, com incerteza impedindo PASS.

Estado integrado:

- HEAD final do PR #118: `8098972cb1e0c21fea01d44fba7e3531934d78e8`;
- Runtime UI proof final: run `35882212884` — **PASS**;
- artifact: `runtime-proof-35882212884`, ID `10761550164`;
- digest verificado: `sha256:682caf704b391d9d1b6c5b2dfdd3111b93f85124f2fb3532b7e16dec76bb6eda`;
- manifest: `overall=PASS`, `merge_gate=PASS`;
- invariantes do harness: 3/3 PASS;
- cenários UI: 10/10 PASS;
- mobile 390×844: sem overflow horizontal antes/depois da seleção;
- merge commit: `1de5c60bd11cb7c5bbb9d595e5155631772513a8`.

Como o executor manual pós-merge não estava disponível na sessão de reconciliação, foi registrada uma prova de equivalência, sem fingir um novo run:

- tree do HEAD efetivamente testado: `240b35809c6ceb8be7d6f70ef5f2b643b1df4443`;
- tree do merge commit em `main`: `240b35809c6ceb8be7d6f70ef5f2b643b1df4443`;
- portanto a árvore integrada é byte-equivalente à árvore exercitada pelo run final.

Sinais realmente pós-merge sobre `main@1de5c60...`:

- Quality: run `35883642699` — **PASS**;
- Pages build/deployment: run `35883637446` — **PASS**.

Isso satisfaz o gate material do primeiro slice UI/checkout. Não é descrito como um novo `workflow_dispatch`.

A #117 permanece aberta para o marco operacional ainda separado da #35. Network/privacy/GA4 continuam pertencendo à #108 e não foram absorvidos pelo harness.

### Simplificação do plano de execução — #117 / PRs #119 e #120

Após o harness do #118, dois slices adicionais foram integrados:

- PR #119 removeu exclusivamente os workflows encerrados da #86 (`issue86-sync-branch.yml` e `issue86-validation.yml`);
- PR #120 removeu o preflight noturno encerrado da #34 e tornou `evidence-discovery.yml` manual-only (`workflow_dispatch`), eliminando duplicação automática comprovada com o worker industrial;
- Quality e Pages pós-#120: runs `35888011140` e `35888009578` — **PASS**;
- merge do #120: `fb67c400b3e753add9f8ae6298d9ae5cb8a6dbb7`.

A auditoria de schedule/concurrency da #35 foi registrada, mas **nenhuma mudança de cadência foi aplicada** neste checkpoint.


## Reconciliação de PRs herdados

### PR #114 / #35

Permanece **OPEN + DRAFT + BLOCKED**.

O diff corrige corretamente o falso positivo que tratava falha de collection/materialização em fonte Câmara como falha de reacquisition. Porém o produtor operacional atual não emite `incident_type=institutional_reacquisition_failure`; portanto o ramo explícito proposto não é alcançável no input real.

Não mergear até existir contrato integrado produtor → guard. Não restaurar a inferência antiga.

### PR #115

Fechado **sem merge** como infraestrutura temporária superseded.

Nove dos onze paths do PR são byte-idênticos à `main`. Os dois únicos paths exclusivos eram um workflow E2E temporário e seu script de teste, substituídos pelo harness canônico do #118.

### PR #116

Mergeado em `c36c8c64e5c84e90a839dca08945a31ae2174993` como reconciliação documental pós-#118.

O checkpoint atual já incorpora também os slices posteriores #119/#120. Nenhum deles alterou dados eleitorais ou semântica pública.


## Evidências temáticas

Fonte canônica:

`data/reference/topic-evidence.json`

Cobertura canônica atual: **22 registros**.

Taxonomia pública congelada:

- `saude`;
- `educacao`;
- `seguranca`;
- `economia`;
- `infraestrutura`;
- `meio-ambiente`;
- `direitos`.

Não force-fit de tema durante o freeze.

A ausência de evidência continua significando apenas ausência de evidência integrada nas fontes verificadas, não ausência de proposta ou posição.

## Pipeline de evidências — War Time

A #35 permanece aberta em modo contínuo, read-only/artifact-only.

Invariantes:

- zero autoaprovação;
- zero escrita canônica pelo worker;
- promoção somente por PR rastreável + gates;
- falhas institucionais e de anchor permanecem explícitas;
- fila de curadoria é delta novo, não repetição de decisões já tomadas.

Resumabilidade está comprovada:

- run `35722612606` persistiu estado ao atingir o orçamento de ciclos;
- run independente `35724917391` restaurou a chave anterior, continuou do estado preservado e drenou o backlog;
- o worker permaneceu read-only/artifact-only e publicou artifacts auditáveis.

Estado operacional recente auditado:

- run `35792402700`: **SUCCESS** e backlog drenado;
- runs `35803561413` e `35876193462`: processamento chegou a `queued=0`, `eligible=0`, `progressed=0` no primeiro ciclo; o vermelho final continua vindo do mesmo gate de incidentes;
- `persistent_failures=45`;
- `actionable_incidents=14` nos runs vermelhos;
- os 14 continuam reportados como `institutional_reacquisition_failure` com detalhe `conteúdo institucional API insuficiente para revisão`;
- artifact plenamente auditado do run `35803561413`: `evidence-worker-35803561413`, ID `10726154995`, digest `sha256:214d1a3f01e211413a28c9e808fa7b8fe4bb275c37b703977cddf3f30a040a21`.

A auditoria de cadência mostrou que a concurrency serializa corretamente e que um run de ~2h28 reteve o seguinte até a liberação do grupo. A cadência wartime atual permanece inalterada até decisão separada da mantenedora.

A auditoria da #35 concluiu que esses 14 casos possuem aquisição/proveniência Câmara presentes e falham na materialização por conteúdo insuficiente; o `cruise_worker_guard` ainda os classifica como reacquisition failure pela origem da fonte, sem distinguir o estágio real da falha.

Portanto:

- o vermelho não deve ser apagado, ignorado ou transformado em whitelist;
- os registros permanecem nos artifacts/exception state;
- a próxima correção dessa lane deve tornar a classificação do guard explícita e testável, sem tocar evidência canônica, taxonomia ou UI.

Os arquivos versionados de staging no repositório não equivalem ao estado operacional do worker; o worker preserva estado não canônico em artifacts/cache.


## Enriquecimento TSE — #86

A #86 está **closed/completed**.

PR #105 mergeado em `main` no commit `cc7cafe5dda35d8514a053042ef5f02b1046c18e`.

Snapshot consolidado:

- 547 candidaturas processadas;
- 356 candidaturas com bens;
- 1.513 registros de bens;
- 447 candidaturas com redes;
- 1.253 links após normalização e deduplicação;
- 376 candidaturas com histórico;
- 1.138 registros históricos.

A proveniência preserva explicitamente a cadeia:

`TSE = fonte factual primária → bootstrap versionado = transporte contingencial → freshness + hashes`.

Contratos preservados:

- patrimônio com contagem e soma auditáveis;
- redes normalizadas e deduplicadas;
- histórico com chave `year/office/uf/party/result`, preservando `location` quando aplicável;
- ausência de CPF, título eleitoral e e-mail pessoal nos registros públicos;
- `registration_status = "not_available"` para sentinelas TSE, sem inferência jurídica.

Validação pós-merge contra o SHA canônico:

- cinco gates de dados: **OVERALL PASS**;
- patrimônio: PASS;
- redes: PASS, `duplicatas_casefold=0`;
- histórico: PASS;
- PII: PASS, zero hits;
- Quality: run `35686294433` — **SUCCESS**, 102 testes + `audit-site.py`.

A integração está consolidada em `main`; menções anteriores a “aguardando merge” estão obsoletas.


## Sync eleitoral — #88

A #88 está **closed/completed**.

A correção de `__pycache__` foi mergeada em `341251b52df06e8cf4884cb18b4a170b31657534`.

A prova operacional pós-merge foi concluída no run `35722902998` sobre `main`:

- conclusão: **success**;
- guard de escopo preservado;
- artifact: `sync-data-candidate-35722902998`;
- artifact ID: `10692007813`;
- digest: `sha256:e77df0c82462391a557a54ca9bd624e387a1026946638aa878339440df8da94e`;
- 137 federais + 410 estaduais = 547 candidaturas;
- 547/547 URLs HTTPS de foto;
- 7 vínculos Câmara;
- 26 evidências ALES;
- 22 evidências temáticas;
- 1.513 bens;
- 1.253 redes;
- 1.138 registros históricos.

A prova operacional exigida pela issue está completa; menções anteriores a “pendente” estão obsoletas.


## Governança executável

A #36 está concluída.

Ruleset ativo da `main`:

- nome: `Protecao-da-Main`;
- ruleset ID: `23730808`;
- enforcement: `active`;
- alvo: default branch;
- bypass actors: nenhum;
- `current_user_can_bypass: never`;
- deletion bloqueada;
- non-fast-forward/force push bloqueado;
- Pull Request obrigatório;
- required status checks em modo strict:
  - `audit`;
  - `🛑 Inspetor de Regras da IA`.

O endpoint clássico de branch protection pode retornar 403 para a integração GitHub App sem permissão administrativa; isso não invalida o ruleset observado pelo endpoint próprio de rulesets. A branch `main` retorna `protected: true`.

## Estado das frentes

### Concluídas / consolidadas

- #36 — proteção efetiva de `main`;
- #45 — topologia canônica multiagente;
- #86 / PR #105 — bens, redes e histórico TSE integrados e validados;
- #88 — sync eleitoral validado operacionalmente pós-merge;
- #91 — `registration_status` explícito;
- #93 — Open Graph estático 1:1 por candidatura;
- #95 — checkpoint obrigatório no mesmo PR de mudança em `data/generated/*`;
- #107 / PR #112 — funil factual de comparação validado em produção.
- #118 — primeiro slice do harness UI/checkout da #117 integrado em `main`;
- #115 — branch E2E temporária fechada sem merge após supersession pelo #118;
- #116 — checkpoint documental pós-#118 mergeado;
- #119 — workflows encerrados da #86 removidos;
- #120 — preflight noturno aposentado e discovery automático deduplicado;
- #127 / PR #128 — ficha reorganizada em HOJE → PROPÕE → IMPACTO, mergeada e publicada;
- #138 / PR #139 — navegação direta desktop + Home enxuta, mergeada e publicada;

### Em andamento

- #2 — expansão de propostas e declarações com fonte;
- #34 — tracking de escala da pipeline de evidências;
- #35 / PR #146 — recência dentro da curadoria candidate-fair; finding 2 (bucket de data inválida vs. ausente) corrigido e resubmetido, aguardando reconciliação da auditoria independente; worker contínuo War Time e classificação do cruise guard permanecem pendentes separadamente;
- #42 — benchmark semântico em shadow mode, disponível para triagem sem autorização de promoção automática;
- #117 — simplificação operacional em andamento; três slices (#118/#119/#120) integrados; revisão de cadência da #35 permanece separada;

### Bloqueada

- #108 — instrumentação GA4 com minimização de dados; #113 fechado sem merge e gate de outbound click não comprovado.
- #114 / #35 — guard de reacquisition bloqueado até existir sinal operacional produzido e testado end-to-end;

### Governança

- #44 — Governance Sentinel permanece aberto em `status:ready`; baseline documental reconciliado, implementação do sentinel ainda pendente;
- #43 — decisão de orquestração permanece pós-freeze.


## Critério de pronto para `data/generated/*`

A partir deste checkpoint, qualquer PR que toque `data/generated/*` deve atualizar **`docs/CHECKPOINT_CURRENT.md` no mesmo PR**.

Esse acoplamento é parte do DoD e deve ser aplicado fail-closed pela Cerca Elétrica.

Objetivo: impedir que snapshot público e documentação canônica avancem em estados diferentes.

## Gates de entrega

Antes de merge de mudança pública:

1. `node --check app.js` verde;
2. `scripts/audit-site.py` verde;
3. suíte determinística de testes verde;
4. Quality verde;
5. Cerca Elétrica verde quando aplicável;
6. `docs/CHECKPOINT_CURRENT.md` no mesmo PR quando `data/generated/*` for alterado;
7. Pages/deploy correspondente concluído quando houver superfície pública;
8. comportamento publicado verificado quando a mudança for de frontend/distribuição.

`CI verde != cobertura de dados completa`.

`feature no código != feature validada em produção`.

`placeholder != integração`.

## Feature freeze de produção

A V5.5 permanece congelada até 04/10/2026.

Exceções permitidas no núcleo eleitoral:

- segurança;
- atualização factual;
- proveniência;
- disponibilidade;
- acessibilidade/correção necessária já coberta pelas regras normativas.

Para os itens prioritários desta passagem, o PR deve registrar:

```
Freeze-exception: <categoria>
Justificativa: <por que não altera ordem, visibilidade, tratamento ou interpretação de candidaturas>
```

A justificativa precisa ser revisada antes do merge.

A camada de sustentabilidade permanece isolada e não pode modificar `topic-evidence.json`, ordenação, busca, comparação ou tratamento de candidaturas.

## Próximo passo seguro

Estado após a arrumação de governança:

1. manter o PR #114 em draft/BLOCKED até existir contrato produtor → guard para `institutional_reacquisition_failure`;
2. manter #108 separada: privacidade/GA4/network não voltam para #117 por conveniência;
3. manter #43 bloqueada até o pós-freeze;
4. #44 está pronta para implementação futura do Governance Sentinel, sem misturar isso com alterações eleitorais;
5. a revisão da cadência wartime da #35 fica como **unidade operacional separada**; este checkpoint não altera cron, concurrency ou timeout;
6. continuar #2/#35 sob os contratos do feature freeze, sem promoção automática de evidência política.

Nenhuma dessas frentes autoriza relaxamento dos gates de `main`.
