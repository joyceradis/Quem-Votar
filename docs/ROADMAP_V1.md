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

**P0 de governança**
- #36 — concluir proteção de `main` + caminho autorizado do sync;
- #45 — topologia multiagente e disciplina de Issues/documentação;
- #44 — Governance Sentinel para detectar drift automaticamente.

**Preflight de escala**
1. #38 — coverage ledger e relatório read-only;
2. #39 — descoberta de fontes em lote;
3. #40 — idempotência, retomada e reprocessamento seguro;
4. #41 — fila de exceções para casos ambíguos.

**Avaliação em paralelo**
5. #42 — benchmark de revisão semântica em shadow mode.

**Execução operacional**
6. #35 — full candidate evidence coverage pass, somente após o preflight mínimo #38–#41.

**Decisão pós-freeze**
7. #43 — ADR de orquestração da pipeline após resultados medidos e fim do freeze.

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

### ⏳ P1 — Histórico

- histórico eleitoral TSE;
- histórico partidário;
- mandatos anteriores;
- funções públicas anteriores;
- composição contemporânea da ALES;
- histórico federal preservado mesmo com falha transitória de API.

### ⏳ P2 — Transparência eleitoral

- bens declarados;
- receitas de campanha;
- despesas de campanha;
- fornecedores/doadores conforme regras públicas;
- redes sociais declaradas ao TSE.

### ⏳ P3 — Atuação parlamentar

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
