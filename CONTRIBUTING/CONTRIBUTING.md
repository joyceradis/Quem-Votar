Como contribuir com o Quem Votar?

Obrigado pelo interesse em contribuir com o Quem Votar?.

O Quem Votar? é um projeto cívico de informação eleitoral orientado por evidências. O objetivo do repositório é tornar informações públicas sobre candidaturas mais acessíveis, compreensíveis, verificáveis e rastreáveis, preservando neutralidade editorial, proveniência dos dados e segurança metodológica.

Contribuições são bem-vindas, mas mudanças neste projeto não são avaliadas apenas por funcionarem tecnicamente. Elas também precisam respeitar os contratos de produto, dados, privacidade, acessibilidade, governança e integridade editorial do repositório.

⸻

1. Antes de contribuir

Leia os documentos de governança aplicáveis antes de alterar código, dados, interface ou documentação.

A documentação existente no repositório é parte do contrato do projeto, não material meramente informativo.

Quando houver conflito entre uma implementação e um contrato documentado, o conflito deve ser explicitado e resolvido antes da integração da mudança.

Não presuma que o comportamento atual do código representa necessariamente a regra correta.

⸻

2. Princípios do projeto

Toda contribuição deve preservar os seguintes princípios:

2.1 Neutralidade

O Quem Votar? não deve:

* recomendar candidatos;
* produzir ranking eleitoral;
* atribuir nota, score ou grau de afinidade;
* declarar um candidato “melhor” ou “pior”;
* transformar ausência de evidência em conclusão;
* utilizar linguagem editorial que favoreça ou prejudique candidatura específica.

A plataforma deve apresentar informações e evidências para que o próprio usuário forme sua decisão.

2.2 Proveniência

Informações políticas, eleitorais ou sobre atuação pública devem preservar, sempre que aplicável:

* fonte;
* URL ou identificador da fonte;
* data;
* tipo de evidência;
* vínculo com a candidatura correta;
* contexto necessário para interpretação.

Uma informação sem proveniência adequada não deve ser promovida para uma superfície que sugira confirmação factual.

2.3 Identidade de candidatura

A chave canônica de identificação de candidatura é:

SQ_CANDIDATO

Não substitua essa chave por nome, número eleitoral, slug, índice, posição em array ou outro identificador sem que exista decisão arquitetural explícita autorizando a mudança.

2.4 Lacuna não é conclusão

Ausência de dado, ausência de proposta localizada ou ausência de evidência não significa ausência de atuação, posicionamento ou compromisso.

Estados vazios devem comunicar a limitação da base sem criar inferências indevidas.

2.5 Complexidade interna, simplicidade externa

A interface pode ser simples.

A metodologia por trás dela não precisa ser simplificada artificialmente.

Validação, proveniência, classificação, transformação de dados e regras editoriais devem permanecer auditáveis mesmo quando o resultado apresentado ao usuário for conciso.

⸻

3. Antes de começar uma mudança

Antes de implementar uma alteração relevante:

1. verifique se já existe issue relacionada;
2. leia o contrato e os critérios de aceitação da issue;
3. identifique dependências com outras issues ou pull requests;
4. confirme se existe alguma restrição de escopo ou freeze em vigor;
5. determine quais arquivos precisam realmente ser modificados;
6. prefira o menor diff capaz de satisfazer o contrato.

Não amplie silenciosamente o escopo de uma issue durante a implementação.

Se surgir uma necessidade nova e independente, registre-a separadamente.

⸻

4. Issues

Issues são unidades formais de trabalho e decisão.

Uma issue deve, quando aplicável, registrar:

* problema;
* contexto;
* escopo;
* fora de escopo;
* critérios de aceitação;
* riscos;
* dependências;
* evidências necessárias;
* decisão final.

Não feche uma issue apenas porque existe código correspondente.

O encerramento deve refletir o cumprimento verificável do contrato estabelecido.

Histórico

Comentários constituem parte do histórico de governança do projeto.

Não apague comentários de issues ou pull requests sem autorização explícita da mantenedora.

Quando uma informação anterior estiver incorreta, prefira:

* comentário de retificação;
* atualização documentada;
* referência à decisão posterior.

O histórico deve permanecer auditável.

⸻

5. Branches e commits

Mantenha alterações pequenas e semanticamente coerentes.

Um commit deve representar uma unidade compreensível de mudança.

Evite combinar, no mesmo commit:

* refatoração não relacionada;
* mudança visual independente;
* atualização de dados;
* correção de bug;
* alteração de governança.

Mensagens de commit devem explicar claramente o que foi alterado.

Exemplo:

fix(candidate): preserve evidence provenance in topic cards
Keeps source metadata attached to thematic evidence during
candidate-page rendering and prevents unverified records from
being promoted to the primary evidence surface.

Não altere histórico publicado apenas para tornar a sequência de commits mais estética quando isso prejudicar rastreabilidade ou auditoria.

⸻

6. Pull requests

Todo pull request deve possuir escopo identificável.

A descrição deve informar, quando aplicável:

* issue relacionada;
* problema resolvido;
* arquivos ou componentes afetados;
* comportamento anterior;
* comportamento resultante;
* testes executados;
* evidências produzidas;
* riscos ou limitações conhecidas;
* itens explicitamente fora do escopo.

Um PR não deve declarar algo como comprovado quando a evidência disponível demonstra apenas parte do contrato.

Diferencie claramente:

* implementação;
* teste automatizado;
* análise estática;
* validação em navegador;
* validação de runtime;
* validação em produção.

Essas evidências não são intercambiáveis.

⸻

7. Revisão

Pull requests podem passar por diferentes tipos de revisão, incluindo:

* revisão de código;
* revisão arquitetural;
* revisão de dados;
* revisão de privacidade;
* revisão de acessibilidade;
* revisão de interface;
* validação em navegador;
* auditoria de runtime;
* reconciliação entre código, CI, artifact e produção.

Um CI verde é evidência importante, mas não substitui automaticamente outros critérios de aceite exigidos pela issue.

⸻

8. Testes

Código novo ou comportamento alterado deve possuir cobertura proporcional ao risco introduzido.

Quando aplicável, teste:

* comportamento esperado;
* estados vazios;
* entradas inválidas;
* regressões;
* mobile;
* desktop;
* navegação por teclado;
* acessibilidade;
* privacidade;
* isolamento de estado;
* teardown;
* cenários assíncronos;
* comportamento após navegação interna.

Não enfraqueça, remova, ignore ou marque testes como skip apenas para obter CI verde.

Quando um teste falhar, determine primeiro se:

1. a implementação está incorreta;
2. o teste está incorreto;
3. o contrato mudou;
4. existe comportamento não determinístico;
5. existe dependência ou estado residual.

A causa deve ser identificada antes da correção.

⸻

9. Dados e evidências eleitorais

Mudanças que adicionem, transformem ou exibam dados eleitorais exigem atenção especial.

Não:

* invente dados ausentes;
* converta inferência em fato;
* vincule registros apenas pela semelhança de nomes quando existir possibilidade de ambiguidade;
* elimine proveniência durante transformações;
* trate ocupação declarada, candidatura, mandato ou vínculo histórico como sinônimo automático de atividade profissional atual;
* apresente classificação política como fato quando a metodologia não sustentar essa interpretação.

Quando um vínculo for incerto, preserve a incerteza.

Preferimos uma lacuna explícita a uma associação falsa.

⸻

10. Interface

Alterações de interface devem preservar a arquitetura informacional do produto.

Antes de promover um dado para uma superfície de maior destaque, considere:

* qual pergunta do usuário aquele dado responde;
* qual é a fonte;
* qual é a força da evidência;
* se o rótulo é semanticamente correto;
* se existe risco de transformar dado administrativo em interpretação editorial;
* qual comportamento ocorrerá quando o dado estiver ausente.

Não use design para aumentar artificialmente a autoridade de uma evidência fraca.

⸻

11. Acessibilidade

Acessibilidade faz parte do contrato funcional.

Mudanças de UI devem considerar, quando aplicável:

* teclado;
* foco;
* semântica HTML;
* contraste;
* leitura por tecnologia assistiva;
* tamanho e comportamento responsivo;
* estados de interação;
* redução de movimento;
* conteúdo compreensível sem depender exclusivamente de cor.

Uma interface visualmente correta pode continuar inadequada se não for operável ou compreensível por outros meios.

⸻

12. Privacidade e telemetria

Alterações que envolvam:

* analytics;
* parâmetros de URL;
* identificadores;
* armazenamento local;
* cookies;
* telemetria;
* serviços externos;
* scripts de terceiros;

devem ser tratadas como mudanças sensíveis.

Não introduza coleta adicional de dados como efeito colateral de outra feature.

Quando o contrato exigir privacidade determinística, ela deve ser demonstrada por evidência compatível com o risco, e não apenas presumida a partir da configuração pretendida.

⸻

13. Dependências externas

Não adicione bibliotecas, serviços, scripts ou integrações externas apenas por conveniência.

Antes de introduzir uma dependência, considere:

* necessidade;
* tamanho;
* manutenção;
* segurança;
* privacidade;
* licença;
* impacto de performance;
* possibilidade de implementar a funcionalidade com a arquitetura existente.

Dependências estruturais devem ser justificadas no PR.

⸻

14. Automação e agentes de IA

Ferramentas de IA, agentes de código e automações podem participar do desenvolvimento do projeto.

O uso dessas ferramentas não reduz os requisitos de revisão.

Agentes devem obedecer aos mesmos contratos aplicáveis a contribuições humanas.

Eles não devem:

* inventar resultados de testes;
* alegar execução que não ocorreu;
* criar evidências inexistentes;
* ocultar falhas;
* ampliar escopo silenciosamente;
* alterar governança para permitir a própria implementação;
* apagar histórico para eliminar divergências;
* realizar merge sem a autorização exigida;
* tratar sua própria implementação como prova independente de correção.

Implementação e auditoria devem permanecer distinguíveis.

Consulte também as diretrizes específicas para agentes e automações do repositório.

⸻

15. Mudanças de governança

Arquivos de governança possuem peso superior ao de documentação comum.

Mudanças nesses arquivos devem ser explícitas e revisáveis.

Não altere silenciosamente regras de:

* aprovação;
* merge;
* proveniência;
* metodologia;
* privacidade;
* segurança;
* política editorial;
* responsabilidades;
* autoridade dos agentes.

Uma mudança de regra não deve ser introduzida dentro de um PR cuja finalidade declarada seja outra.

⸻

16. Freeze

Quando houver período de freeze formalmente declarado, somente alterações compatíveis com as exceções definidas para aquele período devem avançar.

Não classifique uma feature como correção apenas para contornar o freeze.

Caso exista dúvida sobre enquadramento, registre-a antes da implementação.

⸻

17. Merge

A existência de aprovação automatizada, CI verde ou ausência de conflitos não constitui, isoladamente, autorização para merge.

O merge deve respeitar:

* contrato da issue;
* critérios de aceitação;
* revisões exigidas;
* gates aplicáveis;
* regras de governança;
* autorização da mantenedora quando prevista.

Não faça merge enquanto existir bloqueio material conhecido.

⸻

18. Segurança de mudanças

Quando uma contribuição apresentar risco relevante, prefira:

1. mudança pequena;
2. prova isolada;
3. validação;
4. integração;
5. verificação pós-integração.

Evite grandes alterações simultâneas que tornem difícil determinar a origem de regressões.

Rollback simples é uma propriedade desejável.

⸻

19. Comunicação

Discussões técnicas devem ser objetivas e rastreáveis.

Ao identificar um problema:

* descreva o comportamento observado;
* indique a evidência;
* diferencie fato de hipótese;
* informe impacto;
* proponha correção quando apropriado.

Evite atribuir intenção a outras pessoas ou contribuidores quando a evidência disponível demonstra apenas comportamento técnico.

Discordâncias são aceitáveis.

Perda de rastreabilidade não é.

⸻

20. Código de Conduta

Todas as pessoas que participam do projeto devem seguir o CODE_OF_CONDUCT.md.

Questões de comportamento comunitário pertencem ao Código de Conduta.

Questões de engenharia, evidência, governança e entrega pertencem a este documento e aos contratos técnicos relacionados.

⸻

21. Regra final

O princípio geral para contribuir com o Quem Votar? é:

Não basta a mudança parecer correta. Ela precisa ser compreensível, verificável, rastreável e compatível com os contratos do projeto.

Quando houver conflito entre velocidade e perda de evidência, preserve a evidência.

Quando houver conflito entre preencher uma lacuna e inventar certeza, preserve a lacuna.

Quando houver conflito entre um diff amplo e uma mudança verificável, prefira a mudança verificável.

Obrigado por contribuir com o Quem Votar?.
