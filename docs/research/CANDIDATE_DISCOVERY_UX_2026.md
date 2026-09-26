# UX de descoberta de candidaturas — proposta para redesign

Status: research/design brief  
Relaciona-se a #153, #160, #161 e #163.

## Problema atual

A listagem atual foi desenhada para dois cargos e para um universo grande de deputados.

Com quatro cargos e centenas de candidaturas, uma listagem completa paginada como porta de entrada gera:
- muita densidade;
- baixa orientação;
- esforço excessivo para “achar alguém”;
- paginação longa;
- pouca exploração por contexto.

A lista completa deve existir, mas não precisa ser a primeira experiência.

## Princípio

A primeira pergunta não deve ser “qual página da lista?”.

A primeira pergunta deve ser:

**Como você quer encontrar uma candidatura?**

## Arquitetura sugerida

### Entrada 1 — por cargo

Quatro opções:
- Governador
- Senador
- Deputado Federal
- Deputado Estadual

Não usar quatro pills apertadas em mobile.

Sugestões para Claude testar:
- grid 2×2;
- seletor editorial com descrição curta;
- dropdown acessível no mobile;
- cards sem excesso de bordas.

Cada cargo mostra:
- quantidade de candidaturas;
- explicação curta do que faz;
- link “Entenda esse cargo”.

## Entrada 2 — busca direta

Campo de busca com:
- nome
- nome de urna
- número
- partido

Número eleitoral é uma necessidade real e deve ser pesquisável diretamente.

## Entrada 3 — por partido

Mostrar partidos presentes no cargo selecionado.

Pode ser:
- lista alfabética compacta;
- chips somente se houver poucos;
- busca de partido.

Não ordenar de modo a sugerir preferência.

## Entrada 4 — por vínculo territorial documentado

Não usar “onde mora”.

Usar:
**Municípios onde há atuação/vínculo público documentado**

Exemplos:
- já foi vereador/prefeito em Serra;
- exerceu cargo em Vitória;
- trajetória institucional em Colatina;
- naturalidade, claramente rotulada como naturalidade.

Isso responde ao interesse territorial sem publicar endereço pessoal ou inferir residência.

Adicionar explicação curta:
“Vínculo territorial não significa que a candidatura beneficiará mais esse município.”

## Entrada 5 — por assunto

Saúde, Segurança, Educação etc. continuam como macrotemas.

A UI deve dizer:
**candidaturas com registro documentado nesse assunto**

Nunca:
“candidatos que mais priorizam Saúde”
quando só existe uma evidência temática.

## Entrada 6 — posições documentadas

Para a necessidade popular de “é de esquerda ou direita?”, não criar um selo ideológico próprio sem fonte.

Sugestão mais segura e útil:
- mostrar partido com clareza;
- permitir explorar posições documentadas em temas;
- quando houver autodeclaração ou descrição atribuível, mostrar com a fonte;
- evitar transformar “esquerda/centro/direita” em ranking ou recomendação.

Se o produto decidir oferecer um filtro ideológico, ele deve:
- ter fonte metodológica explícita;
- mostrar que a classificação é atribuída, não inferida pelo site;
- permitir abrir a fonte;
- não usar cor como juízo de valor;
- não alterar ordenação por “afinidade”.

## Entrada 7 — experiência pública

Filtro factual:
- exerce mandato atualmente
- já exerceu mandato eletivo
- já exerceu função executiva pública
- primeira candidatura / sem mandato eletivo anterior documentado

Isso responde melhor “com o que a pessoa mexe hoje?” do que um badge abstrato.

## Entrada 8 — situação jurídica/documental

Não criar filtro “tem ficha criminal?” simplista.

Sugestão:
**Registros judiciais/documentais**

Mostrar apenas quando houver fonte oficial e contexto suficiente:
- situação do registro eleitoral;
- certidões criminais disponíveis no TSE/Justiça Eleitoral;
- condenações/decisões públicas relevantes;
- processos eleitorais/criminais/improbidade materialmente ligados à vida pública.

Para cada item:
- órgão
- número
- assunto
- papel da pessoa
- fase/status
- decisão
- data
- fonte

Nunca:
- homônimo;
- ação civil irrelevante;
- mera acusação transformada em culpa;
- processo arquivado sem contextualização;
- pesquisa nominal solta como dado canônico.

## Lista completa

Deve existir em botão explícito:

**Ver todas as candidaturas**

Ao abrir:
- paginação ou carregamento progressivo;
- manter filtros;
- manter URL compartilhável;
- voltar preservando contexto;
- quantidade de itens por página maior do que hoje se performance permitir;
- considerar infinite/“carregar mais” apenas se acessibilidade e retorno de navegação forem resolvidos.

Evitar obrigar o usuário a percorrer dezenas de páginas para descobrir alguém.

## Card sugerido

Card precisa ser escaneável:

- foto TSE
- cargo
- nome de urna
- partido + número
- ocupação/cargo atual confirmado
- até 2–3 assuntos documentados
- vínculo territorial público, se útil
- Entender
- Comparar

Evitar:
- patrimônio em destaque
- número bruto de PLs
- score
- “mais ativo”
- % de promessa cumprida
- selo ideológico não documentado
- excesso de badges

## Ficha

Ordem proposta:

1. Hero
2. Quem é
3. O que defende
4. Prioridades documentadas
5. O que já fez
6. Prometeu antes × o que aconteceu
7. Dados eleitorais
8. Registros judiciais/documentais, quando houver
9. Fontes e limitações

## Comparação

Mesmo cargo por padrão.

Comparar:
- identidade
- trajetória
- atuação atual
- propostas concretas
- prioridades documentadas
- atuação anterior documentada

Dados secundários em disclosure:
- patrimônio
- redes
- situação eleitoral
- vice/suplentes
- registros judiciais/documentais com mesma cautela factual

Não comparar por pontuação.

## Mobile

Prioridades:
- seletor de cargo com alvos de toque adequados;
- busca por nome/número no topo;
- filtros em drawer/bottom sheet acessível;
- filtros ativos visíveis;
- “limpar filtros”;
- lista volta ao mesmo ponto ao retornar da ficha;
- evitar 4 controles horizontais comprimidos.

## Desktop

Pode usar:
- painel de descoberta no topo;
- duas colunas: “Encontrar por…” + resultados;
- filtros laterais somente se não transformarem a página em dashboard genérico.

## Objetivo de design

O usuário deve conseguir chegar a uma candidatura por pelo menos cinco caminhos:

1. sei o nome;
2. sei o número;
3. sei o partido;
4. quero alguém com vínculo público com meu município;
5. quero ver quem tem registro documentado sobre um assunto.

A lista completa passa a ser uma opção — não a experiência principal.
