# Auditoria — Quem-Votar ES

Data: 2026-09-19.

## Resumo executivo

A interface já existia, mas a camada de dados não estava operacional: os snapshots de Deputado Federal e Deputado Estadual permaneciam vazios porque a sincronização falhava.

A auditoria rastreou a falha de origem e reorganizou a arquitetura para separar fonte, transporte, candidatura, mandato e evidência histórica.

## 1. Universo eleitoral do ES

No cadastro básico 2026 processado a partir do arquivo oficial do TSE por espelho rastreável:

- **Deputado Federal: 137 registros**
- **Deputado Estadual: 410 registros**
- **Total: 547 registros**

Cada candidatura usa `SQ_CANDIDATO` como identificador eleitoral.

## 2. Falha do coletor anterior

O sincronizador consultava um endpoint interno do DivulgaCand.

Resultado observado no GitHub Actions:

- HTTP 403;
- snapshots vazios;
- interface sem registros eleitorais.

Uma segunda tentativa, baixando diretamente `consulta_cand_2026.zip` do CDN oficial do TSE, também recebeu HTTP 403 no runner.

Conclusão técnica: a ausência de dados era causada por bloqueio de acesso automatizado naquele ambiente, não por inexistência de candidaturas.

## 3. Contingência implantada

Foi configurado fallback para um espelho público que processa o arquivo oficial `consulta_cand_2026.zip` e publica JSON por UF/cargo.

O snapshot registra:

- TSE como fonte primária;
- URL do dataset oficial;
- repositório/caminho do espelho;
- blob SHA do arquivo espelhado;
- data/hora da coleta.

## 4. Separação Federal / Estadual

Os conjuntos são independentes:

- `data/generated/candidates-federal.json`
- `data/generated/candidates-estadual.json`

A validação rejeita cargo incorreto, UF diferente de ES e `SQ_CANDIDATO` duplicado.

## 5. Situação eleitoral

Achado: o espelho básico devolve `DS_SITUACAO_CANDIDATURA = #NE` nos 547 registros atuais do ES.

Correção:

- `#NE` é tratado como ausência;
- a interface mostra “Não disponível”;
- o workflow impede que `#NE` ou `#NULO` sejam publicados como status.

## 6. Histórico eleitoral

Achado: a interface mostrava “0 eleições anteriores” quando a camada histórica não estava carregada.

Correção:

- zero deixou de representar ausência de integração;
- a interface mostra “Ainda não integrado”;
- a ficha informa que isso não significa ausência de candidaturas anteriores.

## 7. Mandato federal

A camada federal consulta a API oficial da Câmara dos Deputados.

Um mandato só é associado automaticamente quando há correspondência nominal exata normalizada entre a candidatura e o cadastro da Câmara.

A ficha separa candidatura 2026, mandato em exercício, histórico institucional e mandatos externos registrados pela Câmara.

## 8. Histórico estadual / ALES

Foi removida a dependência de lista hardcoded de parlamentares sem garantia temporal.

Foi adicionado:

`data/reference/ales-20a-legislatura-2025.json`

A fonte é a 21ª Sessão Ordinária da 20ª Legislatura, realizada em 01/04/2025, com 30 deputados registrados no painel eletrônico.

No cruzamento nominal com o universo de candidaturas 2026, **26 desses 30 nomes aparecem como candidatos a deputado federal ou estadual**.

A interface apresenta isso como **atividade institucional documentada em 2025**, não como confirmação automática de mandato atual em 2026.

## 9. Patrimônio

A interface tinha espaço para patrimônio, mas a ingestão de `bem_candidato_2026` não está operacional no runner por causa do bloqueio de acesso ao CDN.

Correção:

- nenhum valor é estimado;
- ausência não aparece como R$ 0;
- o campo permanece não integrado.

## 10. Privacidade

O snapshot foi reduzido ao necessário para a consulta eleitoral.

A validação impede publicação de CPF, título eleitoral, e-mail, data exata de nascimento e outros campos pessoais não necessários.

## 11. Automação

O workflow valida:

1. sintaxe Python;
2. sintaxe JavaScript;
3. existência dos dois conjuntos;
4. cargo correto;
5. UF ES;
6. unicidade de `SQ_CANDIDATO`;
7. ausência de campos pessoais proibidos;
8. ausência de sentinelas `#NE`/`#NULO`;
9. proveniência TSE;
10. proveniência do fallback.

## 12. Pendências documentadas

Ainda precisam de integração auditável:

- histórico eleitoral completo do TSE para todas as candidaturas;
- bens de `bem_candidato_2026`;
- redes sociais declaradas;
- prestação de contas 2026;
- composição da ALES com referência contemporânea a setembro de 2026;
- proposições, votações, despesas, presença e emendas estaduais em formato estruturado.

Esses campos permanecem explícitos como pendência; não são preenchidos por inferência.


## 13. Revisão de arquitetura da interface — 19/09/2026

A experiência anterior concentrava apresentação, filtros, cards, explicações e ficha no mesmo documento. Isso produzia excesso de texto e não correspondia ao fluxo principal de consulta.

Correção implantada:
- Home independente;
- listagem independente por cargo;
- ficha individual em URL própria;
- metodologia/fontes em página separada;
- abas internas na ficha para não despejar todo o conteúdo simultaneamente;
- parâmetros de URL compartilháveis para cargo, busca e candidato.

O site continua tecnicamente compatível com GitHub Pages, mas a arquitetura de informação deixou de ser uma one-page application improvisada.

## 14. Fotografias — 19/09/2026

A auditoria confirmou que o snapshot anterior possuía **0 URLs de fotografia** para 137 federais e 410 estaduais.

Foi integrada uma camada explícita de fotografia:
- origem primária: TSE, recurso “ES - Fotos de candidatos”;
- vínculo: `SQ_CANDIDATO`;
- arquivo oficial registrado no metadata;
- transporte/cache público temporário registrado separadamente;
- fallback visual em caso de indisponibilidade.

Após a sincronização, **137/137 registros federais e 410/410 estaduais possuem URL de transporte de foto no snapshot**.

Isso mede presença da URL no snapshot, não disponibilidade HTTP de cada arquivo individual. A UI mantém fallback para falhas de imagem.

## 15. Estado de entrega

O repositório possui `docs/CHECKPOINT_CURRENT.md` como checkpoint pré-release.

Não há release formal apenas porque houve commits ou deploys do Pages. Para um marco versionado, devem ser satisfeitos os gates descritos no checkpoint.


## 16. Revisão de UX — filtros, paginação e comparação — 19/09/2026

A listagem contínua de 137/410 candidaturas foi substituída por uma navegação orientada a tarefas:

- 12 candidaturas por página;
- filtros persistidos na URL;
- área profissional;
- registro institucional;
- seleção de até 3 fichas para comparação;
- página própria de áreas e temas;
- aumento de texto;
- marca visual própria em `assets/logo.svg`.

O shell estrutural usa azul/navy/branco. Cores da navegação não são utilizadas para inferir esquerda/direita/centro.

### Área profissional

A taxonomia é pública em `data/reference/topics.json` e usa somente a ocupação declarada no cadastro eleitoral.

Cobertura do snapshot atual:
- Saúde: 44 candidaturas;
- Segurança pública: 33;
- Educação: 40;
- Direito e justiça: 33;
- Gestão e negócios: 88.

Uma mesma ocupação pode pertencer a mais de uma área, portanto as contagens não são mutuamente exclusivas.

Esses rótulos não significam proposta, qualidade profissional, experiência comprovada ou posição política.

### Camada temática

A interface está preparada para `topic_evidence`, mas a cobertura de propostas/posições ainda não é considerada completa.

Consequência:
- pode-se filtrar por área profissional agora;
- não se publica filtro negativo “não tem proposta” até a cobertura da fonte ser auditada;
- futuras posições favoráveis/contrárias devem ser registradas individualmente com fonte, data e regra explícita.

### Acessibilidade

Foram adicionados:
- controle A+;
- controles com alvo de toque ampliado;
- formulários agrupados;
- paginação;
- redução de texto na Home;
- comparação em tela própria.



## 17. Interface V4 — 19/09/2026

A V4 consolida a interface pública com três correções principais.

### Recorte e snapshot

Todas as páginas públicas exibem:
- recorte atual: Deputado Federal e Deputado Estadual no Espírito Santo;
- data/hora do snapshot;
- link para a fonte primária do TSE.

As contagens são lidas dos arquivos gerados. A interface não trata 137/410/547 como números eleitorais permanentes.

### Ficha vertical

As abas da ficha foram substituídas por seções expansíveis nativas (`details/summary`):
- Visão geral;
- Histórico;
- Temas e propostas;
- Fontes.

A primeira seção abre por padrão. As demais continuam presentes na mesma página e podem ser acessadas por âncora.

### Linguagem visual

A interface evita:
- checkmarks de aprovação;
- bolinhas/status decorativos;
- scores;
- chips para dados básicos;
- cores de cargo;
- codificação ideológica automática.

O rosa do Espírito Santo aparece apenas como acento discreto de marca e não possui significado político ou avaliativo.

### Acessibilidade

A V4 mantém:
- controle de aumento de texto;
- alvos de toque amplos;
- skip link;
- foco visível;
- `prefers-reduced-motion`;
- texto de proveniência com tamanho legível;
- informação textual independente de cor.

## 18. Interface V5 — 19/09/2026

### Reconstrução
- frontend público refeito sobre os mesmos snapshots e identificadores;
- busca e cargo dominam o primeiro fluxo;
- filtros secundários são progressivos;
- listagem usa linhas editoriais compactas em vez de coleção de cards;
- favicon SVG e manifesto web adicionados;
- SVGs de interface permanecem funcionais e mínimos.

### Correção semântica de temas
- `Saúde`, `Educação`, `Segurança`, `Economia` e demais temas passam a significar política pública;
- ocupação declarada ao TSE deixa de alimentar tema ou filtro temático;
- associação candidato-tema depende exclusivamente de `topic_evidence` individualizada;
- taxonomia pública: `data/reference/policy-topics.json`;
- cobertura ausente permanece explicitamente ausente.

### Base de decisão de UX
- redução de choice overload com paginação, busca dominante e filtros sob demanda;
- informação individual do candidato separada de atalhos partidários;
- hierarquia em camadas: Visão geral -> Trajetória -> Temas e propostas -> Registros públicos -> Fontes;
- sem score, ranking, recomendação ou classificação ideológica produzida pela plataforma.

### Preservação de dados
- `SQ_CANDIDATO` não alterado;
- pipeline TSE/Câmara/ALES não reescrito;
- origem e transporte de fotos preservados;
- V5 é mudança de interface e semântica de apresentação, não reinterpretação do snapshot.

## 19. Hardening de governança — 20/09/2026

A auditoria da Issue #36 identificou regressão real: um sync automático publicou queda de **7 para 0** vínculos federais após indisponibilidade da Câmara.

Correções implantadas no commit `28eb787`:

- restauração dos 7 vínculos previamente validados após rechecagem institucional;
- fail-closed quando a Câmara estiver indisponível e não houver estado anterior seguro;
- preservação do último estado validado quando a falha for transitória;
- remoção de `[skip ci]` dos snapshots;
- proibição de `git pull --rebase` após geração/auditoria;
- execução da suíte `tests/` no Quality e no sync;
- redução do trecho bruto persistido pelo coletor de 9.000 para 3.000 caracteres;
- pinagem do espelho por commit + blob + SHA-256;
- expansão de CODEOWNERS para pipeline e evidência canônica;
- Agent Fence passa a exigir vínculo com Issue de autorização para mudanças de governança/control plane/evidência canônica;
- o sync eleitoral deixa de escrever diretamente em `main` e passa a produzir artifact de snapshot candidato com runtime `contents: read`;
- Quality passa a executar em todo push para `main`, removendo lacunas por filtro de paths.

A proteção de branch/ruleset permanece uma configuração externa do GitHub e não é substituída por documentação ou CI.
