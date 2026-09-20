# Checkpoint atual — V5.5

Data: 2026-09-20.

## Estado canônico

Branch: `main`.

Baseline visual: `V5.5`. Cache de assets: `5.5.0`.

Versão canônica: [`VERSION`](../VERSION).

Este checkpoint não cria sozinho um GitHub Release formal.

## Contrato público

- Deputado Federal e Deputado Estadual no Espírito Santo;
- busca e cargo no primeiro fluxo;
- 12 resultados por página;
- comparação de até 3 candidaturas;
- ficha vertical por camadas;
- sem score, ranking, vencedor, previsão eleitoral ou recomendação.

## Semântica temática

`Saúde`, `Educação`, `Segurança`, `Economia` e demais temas representam propostas, declarações ou atuação documentada.

Ocupação declarada ao TSE é apenas metadado. Não gera tema, posição política ou avaliação.

Taxonomia temática pública: `data/reference/policy-topics.json`.

## Interface V5.5

- Home orientada às perguntas “o que faz hoje?”, “o que diz que vai fazer?” e “onde isso mexe na vida real?”;
- identidade regional capixaba leve no hero;
- wordmark `quem votar?` com badge `ES 2026`;
- azul conduz interação e rosa funciona apenas como acento de marca;
- menu principal lateral em todas as larguras;
- linguagem pública sem jargão de auditoria no primeiro nível;
- cargo e busca dominam o primeiro fluxo;
- filtros secundários aparecem sob demanda;
- assuntos e filtros temáticos só aparecem quando existe `topic_evidence` documentada para o recorte correspondente;
- cartões de candidatura usam hierarquia editorial, bordas discretas e tags temáticas apenas quando existe evidência documentada;
- nenhuma tag é derivada de partido, profissão, ocupação, religião ou associação;
- ausência de evidência não gera tag;
- não há selo visual de qualidade, checkmark ou semáforo de completude;
- nome/cargo/partido/número têm precedência sobre foto e ocupação;
- ficha: Visão geral -> Trajetória -> Temas e propostas -> Registros públicos -> Fontes e limitações;
- ficha possui ação de compartilhamento com URL direta e fallback de cópia de link;
- metadados sociais básicos são atualizados no navegador para a candidatura aberta;
- favicon SVG e manifesto web configurados;
- `prefers-reduced-motion` preservado.

## Dados preservados

- `SQ_CANDIDATO` continua chave canônica;
- snapshots TSE não foram reinterpretados;
- Câmara e ALES preservam critérios de vínculo;
- lacuna continua sendo lacuna.

## Limitação conhecida de compartilhamento

GitHub Pages é hospedagem estática. A ficha usa uma única página com query string e atualiza Open Graph no navegador; crawlers sociais que não executam JavaScript podem exibir preview genérico.

Preview social individualizado por candidatura exige geração estática por candidato ou camada de renderização no servidor e permanece pendente.

## Pendências de conteúdo

- histórico eleitoral TSE completo;
- bens;
- redes sociais;
- cobertura contemporânea completa da ALES;
- propostas/posições temáticas em escala;
- atividade parlamentar temática;
- registros públicos juridicamente qualificados.

## Gates

Antes de considerar uma mudança pública consolidada:

1. `node --check app.js` verde;
2. `scripts/audit-site.py` verde;
3. workflow Quality verde;
4. GitHub Pages correspondente concluído;
5. comportamento publicado verificado quando a mudança for de frontend.

## Camada de propostas e declarações

Fonte canônica: `data/reference/topic-evidence.json`.

O sync eleitoral anexa essa camada por `SQ_CANDIDATO` sem apagá-la.

No checkpoint atual, a cobertura canônica é **1 registro**. Isso significa apenas que ainda não há evidência promovida para a camada pública; não significa ausência de propostas ou posições das candidaturas.

A expansão dessa camada é acompanhada pela issue #2.

## Coleta em staging

A issue #5 mantém a infraestrutura de coleta separada da publicação canônica:

- `scripts/coletor_evidencias.py` lê os `SQ_CANDIDATO` do snapshot atual;
- redes sociais declaradas ao TSE entram como sementes de descoberta, não como evidência;
- URLs de conteúdo específico geram rascunhos em `data/staging/`;
- coleta bruta, revisão semântica e promoção canônica ficam separadas;
- HTML e texto são suportados;
- PDF textual é suportado via `pypdf`, sem OCR automático;
- PDF sem camada textual suficiente é rejeitado em vez de inferido;
- hash do arquivo bruto e hash do texto extraído são preservados;
- promoção é `dry-run` por padrão e exige `--write-canonical` explicitamente;
- revisão aprovada precisa estar ancorada em trecho coletado e respeitar o limite de até 3 tentativas;
- a cobertura canônica contém **1 registro aprovado**, usado para validar o pipeline ponta a ponta; isso não representa cobertura temática suficiente.

## Estado das frentes

- V5.4: concluída;
- V5.5 / Issue #11: concluída e consolidada em `main`;
- Issue #5: concluída; infraestrutura de coleta/staging/promoção entregue;
- Issue #2: aberta como frente de integração de evidências;
- Issue #34: aberta para escalabilidade e shadow mode;
- Issue #35: aberta para importação/cobertura operacional;
- Issue #36: hardening crítico de governança em execução;
- Issue #13: concluída; README sincronizado e com regra explícita de manutenção documental.

## Regra documental

Este checkpoint é datado. Se a `main` avançar, ele deve ser atualizado no próximo merge que altere de forma material:

- baseline/versionamento;
- arquitetura de dados;
- contrato público;
- estado das frentes macro;
- limitações conhecidas relevantes.

Microcommits sem mudança de estado não exigem novo checkpoint.


## Feature freeze de produção

A V5.5 permanece em regime de feature freeze até 04/10/2026, com fronteira explícita entre o **núcleo eleitoral** e a **camada de sustentabilidade**.

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

Pode evoluir durante o freeze sem alterar a versão V5.5 quando permanecer desacoplada do conteúdo eleitoral:

- `.github/FUNDING.yml`;
- GitHub Sponsors;
- seção de apoio no README;
- rota estática `apoio.html`;
- cópia local de chave PIX;
- documentação de transparência e sustentabilidade;
- link secundário de apoio no rodapé.

Essa camada não pode escrever na fonte canônica de evidências, aparecer como publicidade dentro de fichas/busca/comparação/temas nem conceder qualquer influência editorial.

Toda mudança durante o freeze deve usar o menor escopo efetivo possível.

Baseline canônico durante o freeze: **V5.5**.


## Hardening de governança — 20/09/2026

A auditoria da #36 confirmou regressão anterior de 7 → 0 vínculos federais quando a API da Câmara ficou indisponível.

Os 7 vínculos previamente validados foram restaurados após rechecagem institucional, e o sincronizador agora:

- preserva o último estado federal validado quando a lista da Câmara estiver temporariamente indisponível;
- aborta se a fonte falhar e não existir estado anterior seguro;
- impede rebase pós-auditoria;
- não usa `[skip ci]`;
- executa a suíte do pipeline antes da publicação;
- resolve o espelho eleitoral por revisão imutável e hash do conteúdo processado.

Quality do commit crítico `28eb787` concluiu com sucesso. A proteção/ruleset da branch `main` continua sendo configuração externa do GitHub e permanece requisito aberto do hardening até ser ativada.
