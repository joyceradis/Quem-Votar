# Roadmap V1 — Eleições 2026 / Espírito Santo

Este arquivo mostra **a sequência macro de evolução do produto**.  
As tarefas executáveis, decisões e critérios de pronto ficam nas [Issues](https://github.com/joyceradis/Quem-Votar/issues).

## Estado atual

### ✅ P0 — Fundação e baseline público

Entregue como base da V5/V5.5:

- identidade capixaba;
- navegação mobile;
- Home orientada à tarefa;
- busca;
- separação Federal/Estadual;
- deep link de candidato;
- comparação;
- indicadores de cobertura;
- governança para agentes;
- auditoria e CI contra regressão;
- sistema visual editorial V5.5;
- tags temáticas somente quando existe evidência documentada.

As frentes de fundação visual e estrutural já estão consolidadas. A V5.5 é o baseline atual; evolução futura deve preservar seus contratos de neutralidade, legibilidade e desempenho.

### 🚧 P4 — Temas e posições documentadas

Esta é a frente prioritária de conteúdo. O resultado de produto é acompanhado pela **#2**; a engenharia de escala é coordenada pela **#34**.

### Ordem canônica de execução

**Governança consolidada**
- #36 — proteção efetiva de `main`: concluída;
- #45 — topologia multiagente e disciplina documental: concluída;
- #44 — Governance Sentinel: `status:blocked`, implementação pendente (control-plane/alto risco);
- #117 — plano de execução/harness: três slices integrados (#118/#119/#120);
- #133 — cadência do worker de evidências: **concluída** (`evidence-industrial` passou de 5 min para horário). O incidente #171 (reaquisição da Câmara) é lane de dados separada, não é a cadência.

**Reconstrução V6 — gate de release**
- Fases 0–4 concluídas e em `main` (Issue #167; PRs #168/#170); Fase 5 (corte atômico da superfície pública) date-gated a partir de 04/10/2026 via `scripts/cutover-v6.sh`. É pré-condição do release da baseline V6; não antecipa o corte nem reabre o núcleo eleitoral congelado.

**Preflight de escala — concluído**
1. #38 — coverage ledger e relatório read-only;
2. #39 — descoberta de fontes em lote;
3. #40 — idempotência, retomada e reprocessamento seguro;
4. #41 — fila de exceções para casos ambíguos.

**Avaliação em paralelo**
5. #42 — benchmark de revisão semântica em shadow mode; disponível para triagem, sem escrita canônica.

**Execução operacional ativa**
6. #35 — worker contínuo wartime, read-only/artifact-only; promoção continua explícita e humana.

**Decisão pós-freeze**
7. #43 — ADR de orquestração permanece bloqueada até o pós-freeze e os resultados medidos.

### Arquitetura vigente

Infraestrutura entregue pela #5:

`source → staging → deterministic validation → semantic review → explicit promotion → sync → public interface`

Princípios:

- `SQ_CANDIDATO` é a identidade eleitoral canônica;
- descoberta/coleta em lote substitui projetos manuais por candidatura;
- perfis/homepages são seeds, não evidências;
- ausência de achado permanece ausência de dado;
- processamento, cobertura de evidência e publicação canônica são métricas distintas;
- revisão humana continua obrigatória para promoção canônica;
- nenhuma Issue desta frente autoriza score, ranking, recomendação ou inferência política automática.

A #34 é tracking; critérios executáveis vivem nas Issues-filhas.

## Próximas frentes

### 🟡 P1 — Histórico — base integrada, expansão pendente

Já integrado:
- histórico eleitoral TSE quando disponível;
- vínculos institucionais federais atuais/históricos;
- evidências documentais estaduais vinculadas de forma conservadora.

Ainda evolutivo:
- histórico partidário mais completo;
- funções públicas anteriores;
- composição contemporânea/longitudinal da ALES;
- ampliação de fontes sem inferência por ausência.

### 🟡 P2 — Transparência eleitoral — parcialmente integrada

Já integrado:
- bens declarados;
- redes sociais declaradas ao TSE, tratadas como dado/seed e não como posição política.

Ainda pendente:
- receitas de campanha;
- despesas de campanha;
- fornecedores/doadores conforme regras públicas e disponibilidade da fonte.

### 🟡 P3 — Atuação parlamentar — cobertura parcial

Federal:

- proposições;
- votações;
- órgãos/comissões;
- discursos;
- despesas.

Estadual:

- proposições;
- votações;
- presença quando houver fonte apropriada;
- comissões;
- despesas/emendas quando houver fonte estruturada.

### ⏳ P5 — Expansão

- Senado ES;
- Governo ES;
- Presidência;
- arquitetura por eleição/UF/cargo;
- busca nacional sem perder proveniência local.

## Regra de uso

- **README** = o que o projeto é e qual é o estado estável.
- **Roadmap** = para onde o projeto vai e em que ordem.
- **Checkpoint** = estado técnico datado da `main`.
- **Issue** = tarefa concreta que pode ser discutida, implementada e fechada.
- **Comment** = atualização, decisão ou descoberta dentro de uma Issue.
- **Commit** = alteração efetivamente gravada no código.
- **PR** = pacote de alterações proposto para entrar na branch principal.

O Roadmap não deve ser atualizado a cada micro-PR. Atualize quando uma fase fecha, uma prioridade muda ou uma descoberta altera a sequência macro.
