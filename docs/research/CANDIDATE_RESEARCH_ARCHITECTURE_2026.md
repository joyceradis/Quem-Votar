# Arquitetura canônica de pesquisa de candidaturas — ES 2026

Status: research-only / apoio à #160, #161, #162 e #163  
Owner de pesquisa: ChatGPT  
Executor de produto: Claude  
Regra: mesma arquitetura para Governador, Senador, Deputado Federal e Deputado Estadual.

## Princípio

A unidade do produto é a candidatura, identificada por `SQ_CANDIDATO`.

A diferença entre cargos entra nos campos aplicáveis e na linguagem da UI — não em quatro modelos incompatíveis.

```
SQ_CANDIDATO
→ identidade eleitoral
→ foto TSE
→ trajetória
→ campanha 2026
→ prioridades documentadas
→ atuação anterior
→ promessa × resultado, quando aplicável
→ fontes
→ cobertura/gaps
```

## Envelope comum

```yaml
candidate:
  tse_id:
  ballot_name:
  full_name:
  social_name:
  office:
  office_family: executive | legislative
  number:
  party:
  party_name:
  coalition:
  registration_status:
  occupation:
  education:
  naturality:
  photo:
    photo_url:
    photo_source:
  assets:
  social_links:
  previous_elections:
  current_mandate:
  institutional_history:
  campaign_evidence:
  documented_priorities:
  legislative_record:
  executive_delivery:
  past_commitments:
  sources:
  coverage:
```

## Identidade eleitoral

Fonte canônica: TSE / DivulgaCandContas / Dados Abertos.

Campos:
- SQ_CANDIDATO
- nome de urna
- nome civil
- nome social quando aplicável
- cargo
- número
- partido
- federação/coligação quando aplicável
- situação da candidatura
- ocupação
- escolaridade
- naturalidade
- bens declarados
- redes sociais declaradas

Nunca publicar endereço residencial.

## Fotos — contrato idêntico aos deputados

Origem editorial canônica: TSE.

Arquivo oficial ES 2026:
`https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/fotos/foto_cand2026_ES_div.zip`

Transporte/cache operacional atual:
`https://realidadebrasil.com.br/media/photos/<SQ_CANDIDATO>.jpg`

Preservar:

```yaml
photo_source:
  institution: TSE
  dataset: ES - Fotos de candidatos
  official_archive_url: <zip TSE>
  transport: cache público do pacote oficial TSE
  mirror: Realidade Brasil
```

Mesma foto precisa funcionar em:
- card
- ficha
- comparação
- social preview
- fallback neutro se a imagem falhar

Não substituir por foto de imprensa ou rede social no canônico.

## Quem é / trajetória

- profissão/formação
- cargos eletivos anteriores
- cargos públicos não eletivos
- mandato atual
- histórico eleitoral
- histórico partidário documentado
- município(s) de atuação pública documentada

### Nota territorial

Não usar residência pessoal/endereço como filtro.

Para responder à pergunta prática “essa pessoa tem vínculo com Serra/Vitória/etc.?”, usar:
- naturalidade, quando pública;
- município onde já exerceu mandato/cargo;
- município onde atuou institucionalmente;
- base territorial explicitamente documentada.

Rotular como **vínculo/atuação territorial documentada**, não como “mora em”.

Nenhum vínculo territorial autoriza inferir que a candidatura “vai ajudar mais” aquele município.

## Campanha 2026

`campaign_evidence[]`

Tipos:
- proposta
- declaração
- compromisso

Campos mínimos:
- candidate_id
- topic_id
- evidence_type
- statement
- quote_or_summary
- source_url
- source_title
- source_publisher
- published_at
- captured_at
- verification_status

## Prioridades documentadas

`documented_priorities[]`

Só publicar quando a fonte sustentar explicitamente prioridade, bandeira, eixo ou ênfase.

Nunca inferir prioridade por:
- quantidade de posts
- profissão
- partido
- número de evidências
- ausência de outros temas

Campos:
- label
- basis / por que foi tratada como prioridade
- source_url
- source_publisher
- source_date
- review_status

## Atuação legislativa

`legislative_record[]`

- proposition_id
- type
- title/ementa curta
- year
- role: author | coauthor | rapporteur | vote | request | speech
- status
- result, quando aplicável
- source_url
- source_institution

Regras:
- projeto apresentado ≠ lei aprovada
- lei aprovada ≠ política implementada
- número de projetos não é score
- selecionar itens materialmente úteis; não transformar volume em mérito

## Atuação executiva

`executive_delivery[]`

Para quem exerceu prefeitura, governo, secretaria ou outra função executiva:
- programa/ação/obra/política
- cargo/período
- resultado documentado
- fonte institucional
- papel da pessoa quando verificável

Não atribuir toda execução de um governo exclusivamente ao titular.

## Promessa × resultado

`past_commitments[]`

- commitment
- source_url
- source_date
- election_or_plan
- office_period
- observed_result
- result_source_url
- result_date
- external_assessment: fulfilled | partial | not_fulfilled | not_assessed
- assessment_publisher
- notes

Uma classificação de “cumprida/parcial/não cumprida” deve ser atribuída à fonte que realizou a checagem.

O Quem Votar? não cria nota, média ou ranking.

## Justiça / antecedentes / processos

Esta camada precisa de critério estrito.

### Pode entrar
- situação do registro de candidatura;
- certidões criminais disponibilizadas oficialmente pela Justiça Eleitoral;
- condenações ou decisões judiciais públicas com fonte oficial;
- processos eleitorais, criminais ou de improbidade/public-law materialmente relacionados à vida pública, quando verificáveis e contextualizados.

### Não deve entrar automaticamente
- todo processo civil encontrado por busca nominal;
- homônimos;
- boletins sem confirmação processual;
- alegações partidárias/campanha sem fonte judicial;
- processo arquivado apresentado como culpa;
- mera existência de ação como conclusão sobre caráter.

### Campos
- court
- case_number
- subject
- procedural_status
- role_in_case
- decision_summary
- decision_date
- source_url
- captured_at
- caution_note

A UI precisa distinguir: investigado, denunciado, réu, condenado, absolvido, arquivado, decisão recorrível/trânsito em julgado, quando a fonte permitir.

## Orientação política / esquerda-direita

Não inferir orientação individual por profissão, aparência, partido isoladamente ou temas contados.

O produto pode mostrar:
- partido;
- posições documentadas sobre temas;
- autodeclaração do candidato/partido, se houver;
- descrição ideológica atribuída a fonte identificada, quando realmente necessária.

Preferência de UX: deixar a pessoa navegar por **partido + posições documentadas + temas**, em vez de produzir um selo próprio “esquerda/direita” do Quem Votar?.

## Cobertura

`coverage` deve dizer o que está:
- verified
- partial
- not_integrated
- not_found_yet

Ausência visual não vira conclusão factual.

## Campos específicos por cargo

### Governador
- vice
- plano de governo TSE
- experiência executiva
- executive_delivery
- compromissos anteriores

### Senador
- 1º suplente
- 2º suplente
- proposições
- relatorias
- votações
- comissões
- pronunciamentos

### Deputado Federal
- Câmara
- proposições
- relatorias
- votações
- comissões

### Deputado Estadual
- ALES
- proposições
- relatorias
- votações
- comissões

## Fontes-base 2026

TSE candidatos:
https://dadosabertos.tse.jus.br/dataset/candidatos-2026

DivulgaCandContas:
https://divulgacandcontas.tse.jus.br/divulga/

Fotos:
https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/fotos/foto_cand2026_ES_div.zip

Cadastro:
https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip

Complementares:
https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand_complementar/consulta_cand_complementar_2026.zip

Bens:
https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2026.zip

Redes sociais:
https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2026.zip

Histórico:
https://cdn.tse.jus.br/estatistica/sead/odsele/historico_candidatura/historico_candidatura_2026.zip

Propostas de governo ES:
https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_ES.zip

## Regra final

A ficha deve responder, sem julgamento:

1. Quem é?
2. O que está defendendo?
3. Quais prioridades estão realmente documentadas?
4. O que já fez quando teve poder público?
5. O que prometeu antes e o que aconteceu?
6. De onde saiu cada informação?
7. O que ainda não sabemos?


## Contrato de disposição visual — mesmo padrão para os quatro cargos

A disposição base da ficha deve ser a mesma para:
- Governador;
- Senador;
- Deputado Federal;
- Deputado Estadual.

Sugestão de arquitetura:

### Desktop
**Coluna lateral de identidade**
- foto oficial TSE, sem filtro que altere a aparência da imagem;
- cargo;
- nome de urna;
- partido + número;
- ocupação/cargo atual confirmado;
- ações: comparar, compartilhar;
- link educativo `O que faz este cargo?`;
- dados eleitorais/TSE em hierarquia secundária.

**Coluna principal editorial**
1. Quem é;
2. O que defende em 2026;
3. Prioridades documentadas — somente se sustentadas;
4. O que já fez;
5. Prometeu antes × o que aconteceu — quando aplicável;
6. Registros judiciais e eleitorais — somente com fonte/contexto suficiente;
7. Fontes e o que ainda não sabemos.

### Mobile
A mesma ordem semântica, empilhada em uma coluna. A identidade deixa de ser sticky.

### Campos específicos não mudam a arquitetura
- Governador acrescenta vice, plano de governo e entregas executivas;
- Senador acrescenta suplentes e atuação do Senado;
- Deputado Federal acrescenta atuação da Câmara;
- Deputado Estadual acrescenta atuação da ALES.

Nenhum cargo recebe uma ficha visual estruturalmente diferente.

### Critérios de design
Isto é uma sugestão de IA/UX, não um wireframe obrigatório. O executor pode alterar largura, sticky rail, disclosures, tipografia, densidade e composição após validar:
- legibilidade;
- acessibilidade;
- responsividade;
- performance;
- coerência com a identidade visual da #153;
- comportamento real dos dados.

Evitar:
- excesso de cards;
- patrimônio no hero;
- contagens de projetos como sinal de mérito;
- cores como julgamento;
- seção vazia de prioridade;
- afirmação judicial negativa absoluta quando a pesquisa não for exaustiva.
