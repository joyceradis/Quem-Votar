# Checkpoint atual — V5.5

Data: 2026-09-23.

Estado auditado contra `main` em `b4d314f22d513db0011e5718a179c6df4a7dc0ec`.

## Estado canônico

Branch: `main`.

Versão de produto: `5.5.0` ([`VERSION`](../VERSION)).

Baseline visual: V5.5.

Cache atual de assets públicos: `5.5.4`.

Feature freeze do núcleo eleitoral vigente até **04/10/2026**.

O produto informa e documenta. Não produz score, ranking, vencedor, previsão eleitoral ou recomendação de voto.

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

Estado operacional mais recente auditado:

- run `35792402700`: **SUCCESS**;
- run `35803561413`: processamento, persistência, artifact e assert de repositório inalterado passaram; falha ocorreu somente no step `Page only on actionable cruise incidents`;
- `persistent_failures=45`;
- `actionable_incidents=14`;
- os 14 foram reportados como `institutional_reacquisition_failure` com detalhe `conteúdo institucional API insuficiente para revisão`;
- artifact do run `35803561413`: `evidence-worker-35803561413`, ID `10726154995`, digest `sha256:214d1a3f01e211413a28c9e808fa7b8fe4bb275c37b703977cddf3f30a040a21`.

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

### Em andamento

- #2 — expansão de propostas e declarações com fonte;
- #34 — tracking de escala da pipeline de evidências;
- #35 — worker contínuo War Time; classificação do cruise guard permanece pendente;
- #42 — benchmark semântico em shadow mode.

### Bloqueada

- #108 — instrumentação GA4 com minimização de dados; #113 fechado sem merge e gate de outbound click não comprovado.

### Governança

- #44 — Governance Sentinel permanece aberto e pronto para implementação incremental após esta reconciliação documental;
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

Ordem canônica após este checkpoint:

1. concluir esta reconciliação documental da #44 sem misturar código, dados ou UI;
2. na #35, corrigir de forma atômica o contrato de classificação do `cruise_worker_guard`, distinguindo reacquisition real de falha de collection/materialização e mantendo os registros de exceção;
3. depois, implementar o primeiro slice determinístico do Governance Sentinel da #44 para detectar novo drift material do checkpoint;
4. manter #108 bloqueada até reduzir a superfície automática do GA4 e repetir a prova real de rede; não criar patch substituto apenas para contornar a falsificação;
5. continuar #2/#35 sob os contratos do feature freeze, sem promoção automática de evidência política.

Nenhuma dessas frentes autoriza merge automático ou relaxamento dos gates de `main`.
