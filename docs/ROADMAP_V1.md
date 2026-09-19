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

Esta é a frente prioritária porque a utilidade temática da interface depende de evidência real por candidatura.

Objetivo:

- manter a taxonomia temática;
- coletar propostas, declarações e atuação com fonte;
- preservar vínculo por `SQ_CANDIDATO`;
- não inferir posição por profissão, partido ou associação;
- medir cobertura sem tratar ausência de dado como ausência de posição.

Trabalho ativo:

- [#5 — coletor de evidências](https://github.com/joyceradis/Quem-Votar/issues/5): coleta automatizada produz **staging auditável** antes de qualquer promoção canônica;
- [#2 — integração de evidências](https://github.com/joyceradis/Quem-Votar/issues/2): validar, integrar e ampliar a cobertura em `data/reference/topic-evidence.json`.

Fluxo vigente:

`fonte permitida → coleta bruta → staging → validação → revisão semântica → promoção explícita → topic-evidence.json → sync → interface`

A infraestrutura atual já suporta HTML, texto e PDF textual sem OCR automático. A cobertura canônica permanece separada da coleta até aprovação explícita.

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
