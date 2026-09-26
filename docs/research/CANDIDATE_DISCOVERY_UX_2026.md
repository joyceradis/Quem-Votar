# UX de descoberta de candidaturas — proposta para redesign

Status: research/design brief  
Relaciona-se a #153, #160, #161 e #163.

> **IMPORTANTE — natureza deste documento**
>
> Este material é uma **sugestão de produto/UX**, não uma especificação visual rígida.
> O executor deve confrontá-lo com engenharia de frontend, arquitetura da informação,
> acessibilidade, responsividade, performance, testes em navegador e o estado real da #153.
> Se houver uma solução tecnicamente superior que preserve a intenção do produto,
> ela deve prevalecer.
>
> A intenção deve ser preservada; a forma final pode e deve usar julgamento de design.

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
- **número eleitoral**
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

## Entrada 6 — orientação política / esquerda-centro-direita

As pessoas querem saber se uma candidatura está mais à esquerda, ao centro ou à direita. O produto pode atender a essa necessidade, mas **não deve criar uma classificação própria e opaca**.

### Sugestão

Mostrar uma camada do tipo:

**Orientação partidária — classificação acadêmica**

com:
- rótulo atribuído à fonte;
- metodologia identificada;
- ano da classificação;
- link para o estudo;
- observação curta de que a posição do partido não substitui as posições individuais documentadas do candidato.

A literatura de Ciência Política usa diferentes métodos para posicionar partidos no eixo esquerda-direita, incluindo:
- survey com especialistas;
- análise de programas/manifestos;
- comportamento parlamentar;
- percepções de opinião pública.

Por isso, a UI não deve fingir precisão absoluta.

### Referências acadêmicas úteis

- Bolognesi, Ribeiro e Codato — *Uma Nova Classificação Ideológica dos Partidos Políticos Brasileiros* (Dados, 2023):
  https://www.scielo.br/j/dados/a/zzyM3gzHD4P45WWdytXjZWg/
- *Como medir ideologia partidária?* (Revista de Sociologia e Política, 2024):
  https://www.scielo.br/j/rsocp/a/xWg9PnvvVs69M5f8wBYMyTg/
- *Posicionamento dos partidos políticos brasileiros na escala esquerda-direita: dilemas metodológicos e revisão da literatura*:
  https://www.scielo.br/j/rbcpol/a/XNBnwhWwbSsMPFrj4zmHQsG/

### Regras

Não inferir ideologia individual por:
- profissão;
- aparência;
- município;
- quantidade de evidências;
- temas isolados.

Mostrar sempre:
- partido;
- posições documentadas;
- votos/declarações/propostas;
- a classificação partidária como referência atribuída, não como veredito sobre a pessoa.

## Entrada 7 — experiência pública

Filtro factual:
- exerce mandato atualmente;
- já exerceu mandato eletivo;
- já exerceu função executiva pública;
- primeira candidatura / sem mandato eletivo anterior documentado.

Isso responde melhor “com o que a pessoa mexe hoje?” do que um badge abstrato.

## Entrada 8 — situação jurídica/documental

Não criar filtro “tem ficha criminal?” simplista.

Sugestão:
**Registros judiciais e eleitorais**

O TSE informa que o DivulgaCandContas 2026 disponibiliza dados de candidatura, declaração de bens e certidões de antecedentes criminais.

Fontes-base:
- TSE DivulgaCandContas:
  https://www.tse.jus.br/administracao/painel/divulgacao-de-candidaturas-e-contas-eleitorais
- TSE / notícia sobre dados 2026:
  https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/tse-disponibiliza-dados-da-prestacao-de-contas-parcial-das-campanhas-eleitorais

Mostrar apenas quando houver fonte oficial e contexto suficiente:
- situação do registro eleitoral;
- certidões criminais disponíveis no TSE/Justiça Eleitoral;
- condenações/decisões públicas relevantes;
- processos eleitorais/criminais/improbidade materialmente ligados à vida pública.

Para cada item:
- órgão;
- número;
- assunto;
- papel da pessoa;
- fase/status;
- decisão;
- data;
- fonte.

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
- considerar “carregar mais” apenas se acessibilidade, histórico e retorno de navegação forem resolvidos.

Evitar obrigar o usuário a percorrer dezenas de páginas para descobrir alguém.

## Card sugerido

Card precisa ser escaneável:

- foto TSE;
- cargo;
- nome de urna;
- partido + número;
- ocupação/cargo atual confirmado;
- até 2–3 assuntos documentados;
- vínculo territorial público, se útil;
- orientação partidária atribuída, se a metodologia estiver integrada;
- Entender;
- Comparar.

Evitar:
- patrimônio em destaque;
- número bruto de PLs;
- score;
- “mais ativo”;
- % de promessa cumprida;
- selo ideológico sem fonte;
- excesso de badges.

## Ficha

Ordem proposta:

1. Hero
2. Quem é
3. O que defende
4. Prioridades documentadas
5. O que já fez
6. Prometeu antes × o que aconteceu
7. Registros judiciais e eleitorais, quando houver base oficial
8. Dados declarados ao TSE
9. Fontes e limitações

## Fontes no ponto de uso

As fontes **não devem ficar apenas no fim da ficha**.

Sugestão:
- cada afirmação material recebe um pequeno indicador de fonte;
- pode ser numérico, como `[1]`, `[2]`, ou ícone discreto;
- hover e foco mudam visualmente dentro da identidade do produto;
- a ação abre a fonte original;
- a lista consolidada de fontes continua no final da ficha.

### Tipos de fonte

**Oficial**
- TSE
- Câmara
- Senado
- ALES
- Prefeitura
- Governo
- Diário Oficial
- tribunal/órgão público

**Acadêmica**
- artigo científico
- survey de especialistas
- estudo metodológico

**Campanha**
- plano oficial
- site oficial da candidatura
- rede declarada ao TSE
- entrevista/fala direta do candidato

**Jornalística / não oficial**
- veículo jornalístico usado como fonte secundária, checagem ou contexto

O rótulo deve deixar claro o tipo de fonte sem sugerir que “não oficial” = falso.

### Interação sugerida

Exemplo conceitual:

`A candidatura propõe X. [3]`

No hover/foco de `[3]`:
- muda de cor dentro da paleta (rosa/cinza/azul conforme contraste);
- mostra identificação curta da fonte;
- não depende apenas de cor;
- teclado recebe o mesmo comportamento funcional.

No clique:
- abre a origem.

### Nova guia

Se o produto optar por abrir fonte em nova guia, **avisar visual e programaticamente** que o link abrirá nova aba/janela.

W3C recomenda avisar previamente quando um link abre novo contexto e também exige foco visível para operação por teclado.

Referências:
- W3C G201:
  https://www.w3.org/WAI/WCAG21/Techniques/general/G201
- W3C G200:
  https://www.w3.org/WAI/WCAG22/Techniques/general/G200.html
- WCAG 2.2 — Focus Visible:
  https://www.w3.org/WAI/WCAG22/Understanding/focus-visible
- WCAG 2.1 — Content on Hover or Focus:
  https://www.w3.org/WAI/WCAG21/Understanding/content-on-hover-or-focus

### Tooltip / hover

Se hover/focus abrir conteúdo adicional:
- deve funcionar também por teclado;
- ser dismissível quando necessário;
- permanecer visível tempo suficiente;
- não desaparecer quando o usuário mover o ponteiro para o próprio conteúdo.

Evitar depender apenas do atributo `title` para conteúdo essencial.

## Comparação

Mesmo cargo por padrão.

Comparar:
- identidade;
- trajetória;
- atuação atual;
- propostas concretas;
- prioridades documentadas;
- atuação anterior documentada.

Dados secundários em disclosure:
- patrimônio;
- redes;
- situação eleitoral;
- vice/suplentes;
- registros judiciais/documentais com mesma cautela factual.

Não comparar por pontuação.

## Mobile

Prioridades:
- seletor de cargo com alvos de toque adequados;
- busca por nome/número no topo;
- filtros em drawer/bottom sheet acessível;
- filtros ativos visíveis;
- “limpar filtros”;
- lista volta ao mesmo ponto ao retornar da ficha;
- evitar quatro controles horizontais comprimidos.

## Desktop

Pode usar:
- painel de descoberta no topo;
- duas colunas: “Encontrar por…” + resultados;
- filtros laterais somente se não transformarem a página em dashboard genérico.

## Indicação visual de proveniência

A informação deve ser hierarquizada pela função, não por ornamentação excessiva.

Sugestão visual:
- texto editorial principal limpo;
- pequenos índices/símbolos para fontes;
- rótulos discretos de proveniência;
- dividers em vez de cards para tudo;
- disclosures para densidade secundária;
- hover/focus com feedback claro;
- cor nunca como único indicador de estado.

## Pipeline de interação

```
usuário escolhe caminho
→ filtros ficam explícitos na URL/estado
→ resultados escaneáveis
→ abre ficha
→ vê afirmações com fontes em linha
→ pode abrir a origem
→ volta sem perder contexto
```

## Objetivo de design

O usuário deve conseguir chegar a uma candidatura por pelo menos seis caminhos:

1. sei o nome;
2. sei o número;
3. sei o partido;
4. quero alguém com vínculo público com meu município;
5. quero ver quem tem registro documentado sobre um assunto;
6. quero uma referência de orientação partidária com metodologia/fonte.

A lista completa passa a ser uma opção — não a experiência principal.

## Autoridade do executor

Este documento **não substitui o julgamento do executor**.

Claude deve:
- observar referências de design e padrões de interação;
- preservar coerência com a identidade visual já construída;
- respeitar o pipeline de dados/proveniência;
- testar posição de texto, densidade, microcopy, indicadores visuais e estados de interação;
- validar desktop/mobile/teclado;
- evitar soluções visualmente bonitas que piorem descoberta ou acessibilidade;
- propor alternativa melhor quando houver, explicando o ganho.

A recomendação aqui é a intenção de produto. A implementação final deve resultar de engenharia + UX + runtime real.
