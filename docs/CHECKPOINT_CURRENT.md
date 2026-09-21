# Checkpoint atual — V5.5

Data: 2026-09-21.

Estado auditado contra `main` em `49a46286e1b54de970cf71fe9d6c8c5ca2dfce57`.

## Estado canônico

Branch: `main`.

Versão de produto: `5.5.0` ([`VERSION`](../VERSION)).

Baseline visual: V5.5.

Cache atual de assets públicos: `5.5.2`.

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

A telemetria não altera conteúdo eleitoral, ordenação ou critérios editoriais.

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
- falhas institucionais e de anchor são incidentes explícitos;
- fila de curadoria é delta novo, não repetição de decisões já tomadas.

Último worker concluído e auditável no momento deste checkpoint:

- run: `35665676445`;
- commit: `c1b664ffe8b1e49036b78b1b4759cfa13bfb2ad8`;
- artifact: `10668973576`;
- drafts acumulados no artifact: **751**;
- evidências canônicas observadas: **22**;
- URLs não canônicas acumuladas: **624**;
- novo lote de curadoria: **99 itens**, **11 candidaturas**;
- incidentes institucionais acionáveis: **0**;
- transporte Câmara observado nesse run: `api_fallback`.

A infraestrutura bulk oficial da Câmara está em `main`, mas o último run concluído acima caiu para o fallback de API. Portanto o bulk não deve ser descrito como transporte efetivamente usado enquanto um artifact posterior não demonstrar `camara_bulk_daily`.

Os arquivos versionados de staging no repositório não equivalem ao estado operacional do worker; o worker preserva estado não canônico em artifacts/cache.

## Enriquecimento TSE — #86

A #86 permanece **em andamento** e fora do snapshot canônico.

Cobertura observada na branch de trabalho:

- 547 candidaturas processadas;
- 356 candidaturas com bens;
- 1.513 registros de bens;
- 447 candidaturas com redes;
- 1.266 links;
- 376 candidaturas com histórico;
- 1.138 registros históricos.

Esses números são cobertura de dados, não interpretação política.

O transporte de contingência deve declarar explicitamente a cadeia:

`TSE = fonte factual primária → bootstrap versionado = transporte contingencial → freshness + hashes`.

O run `35663835538` falhou e não é prova de promoção. A correção de isolamento de fixture foi aplicada depois, e o run de branch `35663986139` concluiu verde.

Nenhum dado da #86 está autorizado como canônico até patrimônio, redes, histórico e PII/freshness passarem pelos gates separados e um PR de promoção explícito ser aprovado.

## Sync eleitoral — #88

A correção de `__pycache__` foi mergeada em `341251b52df06e8cf4884cb18b4a170b31657534`.

A #88 permanece **aberta** porque merge não equivale a prova operacional.

Critério restante:

- run novo em `main` contendo a correção;
- conclusão verde;
- guard fail-closed preservado;
- artifact auditável;
- SHA, run ID e artifact registrados na issue.

Reexecução de payload antigo não satisfaz esse critério.

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
- #91 — `registration_status` explícito;
- #93 — Open Graph estático 1:1 por candidatura;
- #95 — checkpoint obrigatório no mesmo PR de qualquer mudança em `data/generated/*`.

### Em andamento

- #2 — expansão de propostas e declarações com fonte;
- #34 — tracking de escala da pipeline de evidências;
- #35 — worker contínuo War Time;
- #86 — bens, redes e histórico TSE em staging/validação;
- #88 — prova operacional pós-merge do sync;

### Ainda não consolidada

- #44 — Governance Sentinel periódico permanece aberto.

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

Com o enforcement da #95 consolidado, a ordem volta para:

1. resolver a prova operacional pendente da #88 quando houver novo run;
2. concluir os gates da #86 sem promoção prematura;
3. seguir a expansão de cobertura temática da #2/#35 sob os contratos do freeze.
