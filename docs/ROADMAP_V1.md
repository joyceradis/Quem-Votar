# Roadmap V1 — Eleições 2026 / Espírito Santo

Este arquivo mostra **a sequência de evolução do produto**.  
As tarefas executáveis, decisões e critérios de pronto ficam nas [Issues](https://github.com/joyceradis/Quem-Votar/issues).

## Estado atual

### ✅ P0 — Fundação
Entregue como base da V5/V5.4:
- identidade capixaba;
- navegação mobile;
- Home orientada à tarefa;
- busca;
- separação Federal/Estadual;
- deep link de candidato;
- indicadores de cobertura;
- governança para agentes;
- auditoria e CI contra regressão.

A Issue [#1](https://github.com/joyceradis/Quem-Votar/issues/1) está concluída.

### 🚧 Prioridade imediata — fechar V5.4
Issue [#3](https://github.com/joyceradis/Quem-Votar/issues/3).

Próximos pontos:
- revisar os critérios de aceitação ainda não comprovados;
- concluir compartilhamento/preview onde o GitHub Pages limitar metadados dinâmicos;
- validar mobile, teclado e comportamento visual;
- fechar a issue apenas quando os gates e critérios restantes estiverem comprovados.

### 🚧 P4 — Temas e posições documentadas
Esta frente foi antecipada porque a utilidade temática da V5 depende de evidência real por candidatura.

Objetivo:
- manter a taxonomia temática;
- coletar propostas, declarações e atuação com fonte;
- preservar vínculo por `SQ_CANDIDATO`;
- não inferir posição por profissão, partido ou associação;
- medir cobertura sem tratar ausência de dado como ausência de posição.

Trabalho ativo:
- [#5 — coletor de evidências](https://github.com/joyceradis/Quem-Votar/issues/5): coleta automatizada deve produzir **staging auditável**, não publicar interpretação diretamente na fonte canônica;
- [#2 — integração de evidências](https://github.com/joyceradis/Quem-Votar/issues/2): validar, integrar e ampliar a cobertura em `data/reference/topic-evidence.json`.

Fluxo desejado:

`fonte oficial → coleta bruta → staging → validação → topic-evidence.json → sync → interface`

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
- **Issue** = uma tarefa concreta que pode ser discutida, implementada e fechada.
- **Comment** = atualização, decisão ou descoberta dentro de uma Issue.
- **Commit** = alteração efetivamente gravada no código.
- **PR** = pacote de alterações proposto para entrar na branch principal.
