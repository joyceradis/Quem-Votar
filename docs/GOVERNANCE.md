# Governança de dados e produto

## Princípio central

Toda afirmação política exibida deve ser rastreável a uma fonte identificável. O produto diferencia fatos, declarações, documentos e ausência de dados.

## Proveniência obrigatória

Um registro enriquecido precisa guardar:
- instituição ou autor;
- título da fonte;
- URL;
- data da publicação/documento;
- data da coleta;
- método de vínculo com o candidato;
- nível de cobertura.

## Hierarquia de fontes

### Primária
TSE, TRE-ES, Câmara, ALES, Diário Oficial, Diário Legislativo, portais oficiais, documentos protocolados e programas oficiais.

### Institucional declaratória
Site/canal oficial do candidato ou partido. Deve ser rotulado como declaração da própria parte.

### Secundária
Imprensa e bases de terceiros. Serve como apoio e nunca substitui uma fonte primária disponível.

## Temas controversos

A plataforma não reduz temas complexos a rótulos sem documento.

Exemplo correto:
- "Em entrevista X, em data Y, o candidato declarou Z."
- "Na votação nominal da proposição Y, registrou voto X."

Exemplo incorreto:
- "É pró/contra X" sem critério publicado e sem fonte;
- inferir posição atual a partir de partido;
- inferir ideologia por associação.

## Histórico partidário

Mostrar:
- partido;
- período;
- fonte.

Não concluir "coerente", "incoerente", "mudou por oportunismo" ou equivalentes.

## Atualidade

Dados mutáveis carregam timestamp. Um registro datado não é promovido silenciosamente a estado atual.

## Correção

Toda correção deve:
1. alterar a fonte ou normalizador;
2. gerar commit rastreável;
3. atualizar cobertura;
4. evitar edição manual isolada do texto visível.

## Auditoria

Snapshots automáticos precisam passar:
- schema;
- chaves únicas;
- cargo/UF;
- privacidade;
- sentinelas;
- proveniência;
- regressão de enriquecimento.

## Independência da camada visual

UI nunca deve reinterpretar um código bruto. A normalização acontece antes, na camada de dados.


## Governança operacional de agentes

A governança editorial acima protege o significado dos dados. A governança operacional protege o repositório.

### Separação de camadas
Toda alteração deve identificar a camada afetada:
- **fonte**: material oficial ou secundário coletado;
- **normalização**: transformação do material bruto;
- **snapshot**: dado publicável;
- **interface**: apresentação;
- **documentação**: regra, método ou auditoria.

A interface não corrige fonte. O snapshot não inventa ausência. Uma decisão visual não altera a semântica dos dados.

### Cadeia mínima de rastreabilidade
Para enriquecimentos: `fonte -> coleta -> normalização -> vínculo por SQ_CANDIDATO/identificador -> snapshot -> UI`.

Quando algum elo não existir, registrar a cobertura como pendente em vez de preencher por inferência.

### Mudanças rápidas
O projeto tem prazo curto, portanto a governança deve ser proporcional ao risco:
- CSS, copy e interação local: commit direto em `main` + validação + deploy;
- normalizador/pipeline: validação do snapshot e regressão antes de concluir;
- identidade, vínculo entre bases ou regra editorial: evidência + revisão explícita;
- mudança estrutural destrutiva: branch isolada/checkpoint recuperável.

### Checkpoint auditável
Antes de declarar um marco estável, registrar:
- commit/HEAD;
- deploy correspondente;
- contagens do snapshot;
- cobertura das integrações;
- testes/validações executados;
- pendências conhecidas;
- próximo passo seguro.

Isso é o equivalente leve, para este projeto, ao checkpoint recuperável usado em projetos de maior criticidade.


## Filtros factuais e camada temática

A navegação pode ser simplificada por filtros factuais sem transformar a plataforma em recomendador eleitoral.

### Área profissional
Pode ser derivada da ocupação declarada ao TSE por taxonomia pública e versionada. O rótulo significa apenas “ocupação relacionada à área”.

### Tema político
Uma candidatura só pode receber posição temática quando existir evidência individualizada com:
- tema;
- tipo de evidência;
- resumo factual;
- fonte;
- data;
- estado de verificação.

A ausência de evidência não é convertida em “não possui proposta” enquanto a cobertura não for comprovadamente completa.

### Comparação
A comparação lado a lado pode exibir os mesmos campos documentais disponíveis nas fichas. Não produz vencedor, score, ranking ou recomendação.

## Interface e acessibilidade

A fonte pode ficar a um clique da afirmação sem ocupar a tela inicial. A interface prioriza:
- leitura rápida;
- paginação;
- linguagem clara;
- tamanho de texto ampliável;
- controles grandes;
- navegação por teclado;
- estrutura semântica de formulários.

Cores estruturais não carregam inferência ideológica.


## Governança multiagente

O projeto aceita colaboração de agentes diferentes sem exigir processo corporativo para toda alteração.

A regra operacional é proporcional ao risco:
- mudanças locais de apresentação podem ser executadas e validadas pelos gates existentes;
- mudanças de comportamento preservam contratos documentados;
- mudanças que alterem significado de dados, identidade eleitoral, proveniência, privacidade, normalização ou vínculo entre bases exigem revisão explícita.

Nenhum agente arbitra conflitos por preferência própria. O estado atual do repositório, os documentos normativos e o checkpoint recuperável prevalecem. Quando eles não resolvem a divergência, a decisão é humana.

Ausência de contexto não é autorização para reconstruir. Antes de mudança substancial, o agente precisa compreender o estado que pretende modificar.


## Entrega técnica

Mudanças de interface e deploy devem seguir `docs/DELIVERY_GOVERNANCE.md`, incluindo pré-auditoria, commit atômico e pós-auditoria de produção.


## Independência editorial e apoio institucional

Qualquer apoio institucional deve ser identificado de forma transparente e permanecer sujeito ao firewall editorial do projeto.

Apoio institucional pode financiar infraestrutura, operação ou desenvolvimento, mas não concede participação editorial nem influência sobre dados, metodologia, seleção de fontes, tratamento de candidaturas, classificação de evidências ou resultados exibidos pela plataforma.

Regras obrigatórias:

- apoio financeiro não modifica critérios de inclusão, taxonomia, padrões de evidência ou tratamento de informação ausente;
- apoiadores não recebem tratamento preferencial em decisões editoriais ou metodológicas;
- qualquer exibição pública de apoiadores deve seguir padrão visual uniforme e não promocional;
- proeminência visual não varia de acordo com o valor financeiro do apoio;
- apoio não concede direito de veto, aprovação prévia, acesso privilegiado a conteúdo ou interferência em ordem, filtros, comparação ou apresentação de candidaturas;
- apoio de candidatura, campanha, partido, federação, coligação, comitê eleitoral ou intermediário atuando em nome desses atores não deve ser tratado como apoio institucional neutro do projeto.

O financiamento da infraestrutura e a camada editorial permanecem operacionalmente separados.
