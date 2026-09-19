# Referências de design e licenciamento

## Objetivo

Registrar referências de experiência sem transformar inspiração visual em cópia não rastreável.

## Referências observadas

### Ballotpedia
Referência de produto para:
- profundidade progressiva de informação;
- ficha extensa por candidato;
- apresentação de histórico e contexto;
- navegação por eleição/cargo.

https://ballotpedia.org/

### VOTE411
Referência de produto para:
- navegação guiada;
- perguntas temáticas;
- respostas atribuídas aos próprios candidatos;
- preparação do eleitor antes da votação.

https://www.vote411.org/

## Identidade do Espírito Santo

A identidade visual da V1 deriva das cores oficiais da bandeira estadual: azul, branco e rosa.

Referência normativa:
Decreto-Lei estadual nº 16.618/1947, art. 2º.

## Regra de implementação

O frontend do Quem-Votar foi escrito especificamente para este repositório.

Não copiar:
- HTML/CSS/JS proprietário de sites de referência;
- assets protegidos;
- componentes sem licença compatível;
- textos editoriais de terceiros.

Pode reutilizar código externo apenas quando:
1. houver licença explícita compatível;
2. a origem estiver registrada;
3. a licença/atribuição exigida for preservada;
4. a dependência trouxer ganho técnico claro.

## Design system próprio

Tokens V5:
- ação: `--blue`
- azul profundo: `--blue-dark`
- branco estrutural: `--white`
- rosa ES: `--pink`
- texto: `--ink`
- estrutura: `--line` e `--surface`

Os valores digitais são uma interpretação de interface inspirada na identidade capixaba; o projeto não afirma que sejam códigos cromáticos normativos oficiais. Azul, branco e rosa formam a identidade visual; o rosa é acento de marca e não carrega significado político ou de qualidade.

## Evidência aplicada à V5

A V5 usa pesquisa de comportamento eleitoral e design cívico para reduzir carga cognitiva sem recomendar candidatos.

### Choice overload
Cunow, Desposato, Janusz e Sells (Electoral Studies, 2021) encontraram que conjuntos maiores de candidatos aumentam a carga cognitiva, reduzem aprendizado sobre posições e ampliam o uso de atalhos pouco informativos.

Aplicação no produto: paginação, busca dominante, filtros progressivos e comparação limitada a 3 candidaturas.

https://doi.org/10.1016/j.electstud.2020.102230

### Informação de posições no nível do candidato
Nezi, Wall e Germann (European Journal of Political Research, 2025) mostram que informação no nível do candidato pode ajudar eleitores a distinguir candidatos de seus partidos.

Aplicação no produto: `Temas` significa proposta, declaração ou atuação documentada do candidato; profissão e partido não são usados como substitutos.

https://doi.org/10.1111/1475-6765.70024

### Sistema brasileiro de lista aberta
Nicolau descreve a combinação brasileira de voto nominal e voto de legenda e a forte dimensão personalizada da disputa proporcional.

Aplicação no produto: nome, número, cargo e partido permanecem visíveis juntos; a interface não presume que partido substitui informação individual.

https://www.scielo.br/j/dados/a/Mm8QL3xjPYBMN4bhGQWypLS/

### Plain language e informação em camadas
A EAC e o Center for Civic Design recomendam linguagem simples, hierarquia previsível e apresentação progressiva do conteúdo.

Aplicação no produto: Home curta; ficha em Visão geral -> Trajetória -> Temas e propostas -> Registros públicos -> Fontes e limitações.

https://www.eac.gov/election-officials/design
https://civicdesign.org/tools/voter-education-design-toolkit/

## Limite normativo

Essas referências são usadas para melhorar encontrabilidade, compreensão e comparação factual. Não são usadas para criar nudges partidários, score de afinidade, ranking, recomendação de voto ou ordenação valorativa.