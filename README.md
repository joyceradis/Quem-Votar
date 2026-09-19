# Quem Votar? — Espírito Santo 2026

Plataforma cívica open source para consulta factual e rastreável de candidaturas a Deputado Federal e Deputado Estadual no Espírito Santo.

**Produção:** https://joyceradis.github.io/Quem-Votar/

**Baseline visual:** `V5.4` · assets `5.4.0`

## Onde acompanhar o projeto

- **README:** explica o produto e o estado estável atual.
- **Roadmap:** mostra a sequência de evolução e as prioridades maiores.
- **Issues:** são as tarefas concretas, com discussão, decisões e critérios de pronto.

**Próximos passos ativos:**
1. [#3 — concluir os critérios restantes da V5.4](https://github.com/joyceradis/Quem-Votar/issues/3);
2. [#5 — criar o coletor de evidências com etapa de staging/validação](https://github.com/joyceradis/Quem-Votar/issues/5);
3. [#2 — ampliar a cobertura de propostas, declarações e atuação com fonte](https://github.com/joyceradis/Quem-Votar/issues/2).

O detalhamento e o estado de cada tarefa ficam nas Issues; o [roadmap](docs/ROADMAP_V1.md) mantém a visão de sequência sem duplicar toda a implementação.

## Recorte desta versão

A versão atual cobre:
- Deputado Federal;
- Deputado Estadual;
- Espírito Santo;
- Eleições Gerais de 2026.

Outros cargos não aparecem na interface desta versão.

## Snapshot

A interface não publica contagens como números permanentes. Ela lê, no carregamento, a data e os totais do snapshot em:

`data/generated/meta.json`

O próprio site mostra:
- data e hora do snapshot;
- total federal;
- total estadual;
- link para a fonte primária do TSE.

A data é exibida no fuso `America/Sao_Paulo`.

## Experiência pública V5.4

### Home
- escolha de cargo e busca no primeiro viewport;
- contagens e snapshot ligados à fonte TSE;
- três caminhos simples: nome, tema ou comparação;
- temas de política pública apenas quando há evidência documentada, sem inferência por profissão.

### Candidatos
- 12 resultados por página;
- busca dominante;
- filtros secundários sob demanda;
- partido;
- tema documentado;
- registro institucional integrado;
- seleção de até 3 candidaturas para comparação.

### Temas
`Saúde`, `Educação`, `Segurança`, `Economia` e os demais temas representam **propostas, declarações ou atuação documentada** da candidatura.

A taxonomia pública fica em:

`data/reference/policy-topics.json`

Profissão/ocupação declarada ao TSE é apenas metadado da ficha e não associa uma candidatura a um tema.

### Ficha individual
Leitura em camadas:
- Visão geral;
- Trajetória;
- Temas e propostas;
- Registros públicos;
- Fontes e limitações;
- compartilhamento direto da ficha por URL.

### Comparação
Até 3 candidaturas lado a lado, com os mesmos campos factuais/documentais.

Não existe score, ranking, vencedor ou recomendação de voto.
## Fontes e proveniência

### TSE
Fonte eleitoral primária e origem das fotografias.

### Câmara dos Deputados
Dados institucionais federais vinculados de forma conservadora.

### ALES
Evidências documentais estaduais datadas. Evidência histórica não é promovida automaticamente a situação atual.

Quando uma imagem ou dado usa transporte intermediário por limitação operacional, a origem e o transporte ficam registrados separadamente.

## Regra de integridade

**Uma lacuna permanece lacuna até existir fonte identificável, vínculo justificável e tratamento documentado.**

## Governança

Leia antes de alterar:
- `AGENTS.md`
- `docs/GOVERNANCE.md`
- `docs/DELIVERY_GOVERNANCE.md`
- `docs/PRODUCT_NORTH_STAR.md`
- `docs/TOPIC_EVIDENCE.md`
- `docs/CHECKPOINT_CURRENT.md`
- `docs/FILTERS.md`
- `docs/DATA_MODEL.md`
- `docs/SITE_MAP.md`
- `METODOLOGIA.md`
- `AUDITORIA.md`
