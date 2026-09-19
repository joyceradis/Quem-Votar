# Auditoria inicial — 2026-09-19

## Estado encontrado

O repositório `joyceradis/Quem-Votar-` continha apenas um README mínimo. A aplicação funcional anterior estava fora deste repositório.

## Problemas que a nova estrutura corrige

### 1. Mistura entre cargos
Deputado federal e deputado estadual precisam de conjuntos próprios, filtros próprios e fontes parlamentares diferentes.

### 2. Mistura entre candidatura e mandato
“Candidato em 2026” não significa “parlamentar em exercício”. O sistema passa a armazenar os dois conceitos separadamente.

### 3. Mandato atual versus eleição de origem
A composição parlamentar pode mudar por licença, posse em outro cargo, retotalização, decisão judicial e convocação de suplente. A ficha deve guardar uma linha do tempo e a data de referência.

### 4. Situação eleitoral mutável
A condição de registro pode mudar no curso do processo eleitoral. A interface exibe o rótulo oficial e a data da sincronização.

### 5. Dados sem proveniência
Campos sem URL de origem ou sem data de coleta não devem ser tratados como auditados.

### 6. Histórico incompleto
O histórico passa a ter duas trilhas distintas:
- histórico eleitoral TSE
- histórico de mandato/atividade parlamentar

### 7. Risco de inferência
Ausência de dado não equivale a zero, ausência de processo, ausência de gasto ou ausência de atividade.

## Escopo implementado

- separação Federal / Estadual
- busca textual
- filtros por partido, situação eleitoral e mandato atual
- ordenação alfabética
- marcador objetivo de parlamentar em exercício
- modal/ficha com candidatura e histórico
- comparação factual lado a lado, sem pontuação
- fonte oficial e data da coleta visíveis
- sincronização automatizada
- base de parlamentares atuais para enriquecimento
- documentação de metodologia

## Fontes configuradas

### Eleitoral
TSE DivulgaCandContas / Dados Abertos 2026.

### Federal
Câmara dos Deputados — Dados Abertos.

### Estadual
ALES / Diário do Poder Legislativo. A lista de parlamentares em exercício deve ser revisada contra a fonte institucional sempre que houver mudança de composição.

## Pendências estruturadas

Alguns dados não possuem endpoint estadual uniforme equivalente ao da Câmara. O projeto marca esses itens como indisponíveis até que sejam coletados de fonte oficial adequada.

Não preencher lacunas com estimativas.

## Regra de publicação

Antes de considerar uma ficha “auditada”, validar:

1. identidade da pessoa
2. cargo da candidatura
3. identificador TSE
4. situação eleitoral e timestamp
5. mandato atual, quando aplicável
6. fonte primária de cada bloco histórico
7. ausência de duplicação por variação de nome
