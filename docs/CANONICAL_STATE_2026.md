# CANONICAL STATE — Quem Votar? ES 2026

Status: **VIGENTE / FONTE DE VERDADE OPERACIONAL**
Atualizado após handoff factual da PR #153 em 26/09/2026.

> Em caso de conflito entre este documento e comentários, wireframes, handoffs ou documentos anteriores, **este documento prevalece**, salvo decisão humana posterior explicitamente marcada como vigente.

---

# 1. HOME — #153

## Estado

A Home ainda **não está visualmente aprovada como conjunto**.

PR ativa:
- #153
- branch: `claude/epic-lovelace-lq18l2`
- handoff final da sessão anterior: `e1a8acb0917a2dedef28751f133c990c2f350589`

O HEAD da #153 deve ser tratado como:
- evidência histórica;
- fonte de ativos e soluções técnicas reaproveitáveis;
- **não como composição visual canônica**.

Uma nova sessão pode reconstruir a Home visualmente a partir de uma base limpa, preservando apenas contratos e ativos válidos.

## Intenção visual canônica da Home

A Home deve ser:
- forte, não espalhafatosa;
- moderna, não genérica;
- editorial e humana, não dashboard;
- capixaba, sem turismo/folclore;
- sofisticada, sem frieza;
- clean, sem virar vazia;
- reconhecível como Quem Votar? mesmo sem o logo;
- azul/branco/rosa usados estruturalmente;
- com identidade do Espírito Santo por linguagem visual, não decoração gratuita.

### Identidade capixaba

Direção aprovada:
- Convento da Penha + Terceira Ponte;
- linguagem de gravura/line-art editorial;
- traço azul-marinho fino/irregular;
- fundo transparente;
- rosa como acento raro;
- composição assimétrica;
- recortes permitidos;
- sem aparência turística;
- sem grande vetor corporativo genérico;
- sem obrigatoriedade de usar a ilustração inteira em toda página.

A ilustração deve funcionar como **sistema visual**, não banner turístico.

## Preservar obrigatoriamente

- voz do produto/microcopy forte;
- H1 com presença editorial;
- busca como ação primária;
- azul + rosa;
- identidade ES;
- acessibilidade e comportamento funcional;
- fotos TSE nas fichas/listas, sem filtros que alterem a imagem oficial;
- contratos de dados existentes;
- funcionamento de busca/filtros enquanto a Home é redesenhada.

## Ativos/soluções técnicas potencialmente reaproveitáveis da #153

Validar antes de portar:
- Inter variável self-hosted;
- `assets/capixaba-line.svg`;
- `assets/capixaba-line-dark.svg`;
- autocomplete do hero;
- estados de foco/hover;
- skip-link;
- combobox ARIA;
- drawer mobile com atributos de acessibilidade;
- responsividade de navegação;
- link do landmark para conteúdo institucional.

Reaproveitar por mérito técnico/visual, não por inércia.

## Não preservar por obrigação

- composição atual do hero;
- posição atual da ilustração;
- hierarquia atual de header/hero;
- cards/containers existentes;
- radius/sombras atuais;
- qualquer microajuste acumulado apenas porque já foi commitado.

## Anti-padrões

Evitar:
- hero-card SaaS;
- excesso de rounded cards;
- pills em toda superfície;
- gradientes gratuitos;
- blobs decorativos;
- ícones em excesso;
- simetria perfeita;
- espaçamento excessivamente regular;
- slogans em toda seção;
- animação distribuída pela página inteira;
- todo bloco tentando parecer especial;
- aparência de “site gerado por IA”.

Preferir:
- tipografia;
- hierarquia;
- hairlines/divisores;
- espaço negativo com densidade útil;
- elementos sem container quando possível;
- assimetria útil;
- ritmo editorial;
- poucos componentes muito bem resolvidos.

## Estado técnico importante

O bloqueio antigo de copy em `scripts/audit-site.py` foi corrigido em #165, já integrado em `main`.

Finding ainda relevante do handoff da #153:
- existe uma asserção adicional em `scripts/audit-site.py` acoplada à substring literal de uma media query da navegação desktop;
- tratar como possível dívida de control-plane;
- **não alterar para fazer design passar sem autorização/decisão própria de contrato**.

---

# 2. FICHA INDIVIDUAL — #160

## Direção canônica

Todos os cargos usam a **mesma arquitetura de disposição**:
- Governador;
- Senador;
- Deputado Federal;
- Deputado Estadual.

A diferença entre cargos entra nos dados aplicáveis, não em quatro layouts diferentes.

Referência canônica de arquitetura/UI:
`docs/research/reference/CANDIDATE_PROFILE_UI_REFERENCE_2026.html`

Este HTML é:
- referência de arquitetura e interação;
- desktop + mobile;
- **não** especificação visual rígida.

## Ordem semântica

1. Identidade;
2. Quem é;
3. O que defende em 2026;
4. Prioridades documentadas — somente quando sustentadas;
5. O que já fez;
6. Prometeu antes × o que aconteceu — quando aplicável;
7. Registros judiciais/eleitorais — quando houver base oficial/contexto;
8. Dados eleitorais/TSE;
9. Fontes e o que ainda não sabemos.

## Progressive disclosure

Regra:
- muito dado não vira poluição;
- pouco dado não vira grandes vazios.

Leitura em três níveis:
1. leitura rápida;
2. detalhes relevantes;
3. arquivo completo/fonte original.

Exibir inicialmente poucos registros selecionados por critérios transparentes e permitir “ver atuação completa”.

## Cargo específico

Governador:
- vice;
- plano de governo;
- experiência/entregas executivas.

Senador:
- suplentes;
- Senado;
- proposições;
- relatorias;
- votações;
- comissões/pronunciamentos quando materialmente úteis.

Deputado Federal:
- Câmara;
- proposições;
- relatorias;
- votações;
- comissões.

Deputado Estadual:
- ALES;
- proposições;
- relatorias;
- votações;
- comissões.

Fotos TSE permanecem em todos os cargos.

---

# 3. DESCOBERTA DE CANDIDATURAS

A lista completa não deve ser a porta de entrada obrigatória para centenas de candidaturas.

Direção:
- busca por nome;
- busca por número;
- cargo;
- partido;
- assunto com evidência documentada;
- experiência pública;
- vínculo territorial documentado;
- orientação política/partidária apenas com metodologia/fonte atribuída;
- ação explícita “Ver todas as candidaturas”.

“Vínculo territorial” não significa residência pessoal e não autoriza inferir benefício futuro ao município.

---

# 4. PIPELINE DE EVIDÊNCIAS — #166

## Contrato canônico

```
FONTES OFICIAIS
→ RAW SOURCE STORE + proveniência
→ normalização determinística
→ extração estruturada por IA / schema estrito
→ validadores automáticos
→ revisão humana proporcional ao tier
→ dataset canônico APPROVED
→ publicação no site
```

A IA:
- encontra;
- estrutura;
- sugere.

Regras determinísticas:
- validam IDs;
- datas;
- compatibilidade de cargo;
- fonte;
- duplicatas;
- tipos de evidência.

Humano entra apenas onde existe julgamento real.

`machine_extracted != publicável`.

O front-end deve consumir somente dados aprovados/publicáveis.

## Modelo de domínio recomendado

Entidades separadas:
- Candidate;
- SourceDocument;
- Evidence;
- EvidenceRelation;
- EditorialSelection;
- ResearchCoverage.

Evitar:
- `top_5` automático;
- prioridade inferida por volume;
- promessa × resultado inferido automaticamente;
- texto biográfico não rastreável;
- banco vetorial/RAG como dependência do caminho crítico.

## Relações sensíveis

### Prioridade

Proposta/declaração não é automaticamente prioridade.

Prioridade exige:
- fonte explícita;
- eixo/bandeira/prioridade declarada;
- ou revisão editorial sustentada por evidência.

### Prometeu × aconteceu

A associação entre promessa e resultado deve existir como relação revisada entre evidências.

Busca semântica pode sugerir candidatos a relação, mas não concluir cumprimento.

---

# 5. TIERS INTERNOS DE PESQUISA

Tier é **priorização operacional interna**, nunca rótulo público de importância.

## Tier 1 — Majoritários

5 Governador + 11 Senado.

Pesquisa profunda:
- campanha 2026;
- prioridades;
- histórico institucional;
- atividade legislativa/executiva;
- promessa × resultado;
- fontes/gaps.

## Tier 2A — Proporcionais com histórico parlamentar verificável

Automação de:
- autoria;
- relatorias;
- votações;
- comissões;
- tramitação.

Revisão humana da superfície pública.

## Tier 2B — Proporcionais com histórico executivo/institucional

Pesquisar:
- atos;
- programas;
- entregas;
- portais oficiais;
- auditorias pertinentes;
- promessas anteriores quando rastreáveis.

## Tier 3 — Demais proporcionais

- TSE;
- foto;
- identidade;
- bens;
- redes;
- histórico eleitoral;
- propostas/declarações 2026;
- trajetória verificável;
- prioridades apenas quando sustentadas;
- fontes/gaps.

---

# 6. CASOS-PILOTO / FIXTURES

Usar os sete casos já escolhidos como conjunto de validação editorial/técnica:

- Alexandre Xambinho — pipeline de evidência/ALES;
- Lorenzo Pazolini — executivo municipal + promessa × resultado;
- Renato Casagrande — executivo estadual + prioridade documentada;
- Helder Salomão — Câmara;
- Evair de Melo — Câmara;
- Fabiano Contarato — Senado;
- Marcos do Val — Senado.

Eles não recebem prioridade pública por serem pilotos.

Servem para provar o método antes da escala:

```
7 fixtures
→ 16 majoritários
→ Tier 2A/2B
→ Tier 3
→ universo completo
```

---

# 7. PESQUISA CONSOLIDADA

Documentos vigentes no PR #166:

- `docs/research/CANDIDATE_RESEARCH_ARCHITECTURE_2026.md`
- `docs/research/CANDIDATE_DISCOVERY_UX_2026.md`
- `docs/research/GOVERNADOR_SENADO_RESEARCH_2026.md`
- `docs/research/CANDIDATE_SOURCE_MAP_2026.md`
- `docs/research/reference/CANDIDATE_PROFILE_UI_REFERENCE_2026.html`

A pesquisa aprofundada consolidada está mais avançada para Governador + Senado.

Federal/Estadual possuem snapshot factual amplo, mas ainda precisam receber a nova profundidade conforme tiers.

---

# 8. AUTONOMIA / DEPENDÊNCIA DA MANTENEDORA

A mantenedora não deve ser gargalo operacional.

Agentes podem resolver sem nova decisão humana:
- ingestão;
- normalização;
- IDs;
- datas;
- autoria;
- votação;
- relatoria;
- URLs;
- deduplicação;
- classificação de fonte/evidência;
- extração estruturada;
- validação;
- gaps;
- testes;
- auditoria;
- reconciliação;
- execução de lotes aderentes ao contrato vigente.

Escalar apenas:
- mudança metodológica;
- interpretação editorial contestável;
- conflito relevante de fontes;
- nova classe de evidência;
- associação sensível não resolvida;
- mudança estrutural de UX;
- publicação que possa criar conclusão política não sustentada.

---

# 9. DOCUMENTOS / INSTRUÇÕES SUPERADOS

São históricos, não autoridade vigente:

- wireframes anteriores da ficha incompatíveis com a referência atual;
- instruções antigas da #153 que exigiam preservar commits visuais específicos;
- “Hoje / Propõe / Impacto” como arquitetura canônica da ficha;
- handoff #5840894173 da #156 dentro da #153;
- afirmação de que a #159 continuava lane ativa;
- qualquer instrução de reintroduzir copy antiga para satisfazer audit;
- qualquer regra de “Top 5 projetos” sem critério transparente;
- qualquer tier baseado em “alta visibilidade” subjetiva;
- qualquer proposta de RAG/vector DB/Airflow/Prefect/CMS pesado como requisito para o release atual.

O histórico não deve ser apagado; apenas perde autoridade quando contradiz este documento.

---

# 10. ORDEM DE AUTORIDADE

Em conflito:

1. decisão humana posterior explicitamente marcada como vigente;
2. este `CANONICAL_STATE_2026.md`;
3. contratos metodológicos vigentes do PR #166;
4. Issues específicas (#153/#160/#161);
5. comentários/handoffs anteriores;
6. documentação histórica.

---

# 11. PRÓXIMO HANDOFF — NOVA SESSÃO DE DESIGN

A nova sessão de design deve:
- atuar exclusivamente na Home;
- ler este documento primeiro;
- ler o handoff factual final da #153;
- inspecionar `main` e o HEAD histórico da #153;
- poder reconstruir a Home visualmente sem preservar a composição atual;
- preservar contratos funcionais e ativos tecnicamente válidos;
- não alterar ficha/pipeline/datasets;
- produzir uma direção coesa, não uma sequência de microcorreções;
- validar desktop e mobile antes da avaliação humana.
