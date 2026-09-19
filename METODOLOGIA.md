# Metodologia — Quem-Votar ES

Atualizado em: 2026-09-19.

## Objetivo

Organizar dados públicos sobre candidaturas do Espírito Santo em fichas factuais e rastreáveis.

## Unidades independentes

Todo registro é separado por cargo:

- `DEPUTADO FEDERAL`
- `DEPUTADO ESTADUAL`

Candidatura atual, mandato atual, histórico eleitoral e atividade parlamentar são dimensões distintas.

## Hierarquia de fonte e transporte

### Fontes primárias

1. TSE / Dados Abertos / DivulgaCandContas
2. Câmara dos Deputados / Dados Abertos
3. Assembleia Legislativa do Espírito Santo / documentos institucionais
4. TRE-ES e demais órgãos públicos competentes

### Transporte de contingência

Um espelho técnico pode transportar dados cuja origem primária continue identificada quando o ambiente de automação não consegue acessar diretamente a fonte.

No cadastro básico 2026:

- origem: `consulta_cand_2026.zip` do TSE;
- contingência: `herminiotorres/dossie-cidadao`;
- rastreabilidade: repositório, caminho e blob SHA salvos no metadata.

O espelho não substitui a identificação da fonte primária.

## Estados epistemológicos

Um campo pode estar:

- **verificado**: sustentado por fonte identificada;
- **datado**: sustentado para a data do documento, sem inferência de continuidade;
- **não integrado**: a fonte existe, mas a pipeline ainda não a incorpora;
- **não disponível**: não localizado na fonte operacional consultada.

“Não disponível” não é convertido em zero.

## Situação jurídica eleitoral

A aplicação preserva a terminologia oficial quando ela estiver disponível.

Códigos sentinela da base, como `#NE` e `#NULO`, não são interpretados como decisão jurídica e não são mostrados como status.

## Histórico eleitoral

A camada prevista utiliza o histórico oficial do TSE e pode incluir:

- ano;
- eleição;
- cargo;
- UF/município;
- partido;
- número;
- situação da candidatura;
- resultado;
- identificador oficial.

Até a integração ser auditável, a interface informa “histórico ainda não integrado”.

## Câmara dos Deputados

Para candidaturas federais, a API oficial da Câmara é usada para identificar parlamentares em exercício.

### Regra de vínculo

O sistema só confirma automaticamente o vínculo quando há correspondência nominal exata após normalização entre:

- nome de urna / nome completo da candidatura;
- nome parlamentar / nome civil da Câmara.

Correspondência ambígua não produz vínculo.

### Dados institucionais

Podem ser exibidos:

- legislatura;
- partido institucional;
- condição e situação;
- histórico de exercício;
- mandatos externos;
- links para despesas, eventos, discursos e órgãos.

## Assembleia Legislativa do Espírito Santo

A composição da ALES não é inferida a partir da ocupação declarada no TSE nem de uma lista sem data.

A referência histórica inicial é a 21ª Sessão Ordinária da 20ª Legislatura, realizada em 01/04/2025, cuja ata registra 30 deputados presentes no painel eletrônico.

Um candidato de 2026 só recebe essa evidência quando o nome da candidatura corresponde de forma exata, após normalização, ao nome registrado no documento.

O rótulo exibido é **“atuação institucional documentada”**. A evidência datada não é transformada automaticamente em afirmação de mandato atual.

## Privacidade

O snapshot público é minimizado para a finalidade da plataforma.

Não publicar:

- CPF;
- título eleitoral;
- e-mail pessoal;
- data exata de nascimento;
- identificadores pessoais usados apenas para junção;
- descrição livre de bens enquanto a camada patrimonial não estiver auditada.

## Validação automática

O workflow bloqueia publicação quando:

- Federal ou Estadual está vazio;
- cargo ou UF não corresponde ao recorte;
- `SQ_CANDIDATO` está ausente ou duplicado;
- códigos `#NE`/`#NULO` vazam para a interface;
- campos pessoais proibidos aparecem no JSON;
- a proveniência TSE não está registrada;
- o fallback operacional não registra sua proveniência;
- Python ou JavaScript possui erro de sintaxe.

## Apresentação

A interface oferece busca textual, filtros documentais, ficha individual, data e links de fonte. A ordenação padrão é alfabética.
