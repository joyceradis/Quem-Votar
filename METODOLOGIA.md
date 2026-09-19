# Metodologia — Quem-Votar ES

Atualizado em: 2026-09-19.

## Objetivo

Organizar dados públicos sobre candidaturas do Espírito Santo sem produzir recomendação de voto, ranking, nota, inferência de qualidade ou juízo sobre candidatos.

## Separação obrigatória

Todo registro eleitoral é classificado por cargo:

- DEPUTADO_FEDERAL
- DEPUTADO_ESTADUAL

Mandato atual e candidatura atual são campos independentes. Uma pessoa pode, por exemplo, exercer mandato estadual e concorrer a cargo federal.

## Hierarquia de fontes

### Nível A — fonte primária
- TSE / DivulgaCandContas / Dados Abertos
- TRE-ES
- Câmara dos Deputados / Dados Abertos
- Assembleia Legislativa do Espírito Santo
- Diário Oficial / Diário Legislativo
- Portais oficiais de transparência

### Nível B — fonte institucional secundária
- órgãos de controle e demais bases públicas oficiais

### Nível C — fonte secundária
- veículos jornalísticos e bases de terceiros, sempre identificados como tal

Informação de nível C não substitui uma fonte primária quando esta estiver disponível.

## Tipos de dado

Cada campo deve poder ser classificado como:

- `eleitoral_atual`
- `historico_eleitoral`
- `mandato_atual`
- `historico_mandato`
- `atividade_parlamentar`
- `financeiro_eleitoral`
- `patrimonio_declarado`
- `juridico_eleitoral`
- `fonte_secundaria`

## Situação jurídica

A aplicação preserva a terminologia da Justiça Eleitoral. Não converter:

- deferido
- indeferido
- indeferido com recurso
- sub judice
- renúncia
- cancelamento
- cassação
- outros estados oficiais

em rótulos simplificados que alterem o significado jurídico.

A data da coleta deve ser exibida porque a situação pode mudar.

## Histórico eleitoral

Quando disponível, o histórico deve vir do conjunto oficial de Histórico de Candidaturas do TSE ou do próprio DivulgaCandContas.

Campos desejados:

- ano
- eleição
- UF/município
- cargo
- partido
- número
- situação da candidatura
- resultado eleitoral
- identificador TSE
- fonte e data de coleta

## Histórico parlamentar federal

A Câmara dos Deputados é a fonte prioritária. Dados que podem ser incorporados:

- legislaturas
- condição do mandato
- histórico de filiações
- mandatos externos
- ocupações/profissões
- proposições
- votações nominais
- discursos
- participação em órgãos
- despesas da cota parlamentar

Não transformar quantidade de proposições, presença, gasto ou discurso em nota.

## Histórico parlamentar estadual

A ALES e o Diário do Poder Legislativo são as fontes prioritárias. O projeto deve registrar alterações de composição da legislatura, licenças, substituições e retorno de titulares para evitar confundir “eleito em 2022” com “em exercício em 2026”.

## Comparação

A comparação é puramente tabular. Permitido:

- partido
- número
- situação eleitoral
- eleições anteriores
- mandatos anteriores
- dados financeiros/patrimoniais declarados
- atividade parlamentar documentada

Não permitido no produto:

- ranking
- score
- “melhor/pior”
- “mais preparado”
- recomendação de voto
- ordenação por afinidade política

Ordenação padrão: alfabética.

## Ausência de dado

Ausência de informação nunca deve ser convertida em zero nem interpretada como inexistência do fato. Exibir:

- “não localizado na fonte consultada”
- “não disponível”
- “sincronização pendente”

conforme o caso.

## Proveniência

Cada snapshot gerado registra:

- URL da fonte
- data/hora UTC da coleta
- cargo
- UF
- identificador da eleição
- versão do normalizador

## Atualização

Os dados de candidatura são sincronizados em rotina programada. Dados de mandato podem ter cadência diferente conforme a fonte oficial.

## Correções

Correções devem alterar a fonte ou a regra de normalização; não apenas o texto visível. Isso preserva rastreabilidade.
