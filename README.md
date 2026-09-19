# Quem-Votar — Espírito Santo

Plataforma cívica para consulta factual das candidaturas do Espírito Santo nas Eleições 2026.

## Escopo

O projeto separa explicitamente:

- **Deputado Federal** — candidaturas do ES e histórico institucional na Câmara dos Deputados.
- **Deputado Estadual** — candidaturas do ES e histórico institucional na Assembleia Legislativa do Espírito Santo (ALES).

A plataforma não atribui nota, ranking, recomendação, “melhor candidato” ou indicação de voto. A ordenação padrão é alfabética. A comparação, quando utilizada, mostra apenas dados documentais lado a lado.

## Camadas de informação

### 1. Candidatura 2026
Nome de urna, número, partido/federação, cargo, situação do registro, patrimônio declarado e demais campos publicados pela Justiça Eleitoral.

### 2. Histórico eleitoral
Participações em eleições anteriores e situações registradas pelo TSE.

### 3. Histórico de mandato
Para quem exerce ou exerceu mandato: legislaturas, cargos, filiações partidárias documentadas, votações nominais, despesas, presença, emendas e demais dados institucionais quando houver fonte pública verificável.

## Fontes prioritárias

1. TSE / DivulgaCandContas / Dados Abertos
2. TRE-ES
3. Câmara dos Deputados / Dados Abertos
4. ALES
5. Diários oficiais e portais públicos de transparência
6. Imprensa somente como apoio, identificada como fonte secundária

Cada informação deve preservar **fonte, data de atualização e natureza do dado**.

## Situação jurídica da candidatura

A situação eleitoral não é reduzida a “aprovado/reprovado”. Estados como **sub judice, indeferido com recurso, pendente de julgamento** e equivalentes devem ser exibidos conforme a terminologia da Justiça Eleitoral e acompanhados da data da consulta.

## Atualização

O workflow em `.github/workflows/sync-data.yml` consulta as fontes estruturadas e grava snapshots em `data/generated/`.

## Estrutura

- `index.html` — interface
- `styles.css` — apresentação responsiva
- `app.js` — filtros, fichas e comparação factual
- `data/incumbents.json` — parlamentares em exercício e metadados de mandato
- `data/generated/` — snapshots automáticos
- `scripts/sync-data.mjs` — ingestão e normalização
- `METODOLOGIA.md` — governança e proveniência
- `AUDITORIA.md` — diagnóstico e riscos de dados

## Uso local

O site é estático. Sirva a raiz por HTTP. Para atualizar dados:

`node scripts/sync-data.mjs`

## Nota metodológica

Dados eleitorais e jurídicos podem mudar durante o processo eleitoral. A interface sempre deve exibir a data da última sincronização e fornecer link para a fonte oficial correspondente.
