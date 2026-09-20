# Governança de entrega — Quem Votar?

Data-base: 2026-09-19.

## Objetivo

Evitar que uma mudança válida gere uma sequência de commits intermediários, deploys cancelados, cache divergente ou interface que herde camadas antigas de CSS.

## Norte de produto

Antes de qualquer decisão visual ou de copy, ler `docs/PRODUCT_NORTH_STAR.md`.

## Contrato visual humano

A direção aprovada para a interface pública é:

- identidade capixaba em **azul, branco e rosa**;
- home orientada às três perguntas práticas definidas no norte de produto;
- experiência de produto de consumo, simples, jovem e limpa;
- tipografia forte, bastante espaço útil, imagens limpas e motion discreto;
- menu principal lateral que abre e fecha;
- poucos containers, cards, badges e ícones;
- divisores, linhas, hierarquia e expansão progressiva antes de empilhamento de caixas;
- interatividade funcional sem gamificação;
- temas como Saúde, Educação e Economia representam propostas, declarações ou atuação documentada, nunca profissão.

A cor não pode produzir recomendação, score, qualidade, ideologia ou vencedor.

## Regra de fonte de verdade

1. branch canônica: `main`;
2. `AGENTS.md`;
3. este documento;
4. `docs/GOVERNANCE.md`;
5. `docs/CHECKPOINT_CURRENT.md`;
6. testes automatizados.

Um agente não deve reconstruir por memória quando o estado canônico puder ser lido.

## Pré-auditoria obrigatória

Antes de qualquer escrita:

1. ler `main` atual;
2. verificar workflows ativos e conclusões recentes;
3. comparar o site atual com o contrato visual acima;
4. identificar se o problema é interface, dados, pipeline ou deploy;
5. listar arquivos que realmente precisam mudar;
6. preservar dados e lógica que já estejam válidos.

## Commit atômico

Uma entrega lógica de frontend deve gerar **um commit atômico**.

Proibido:

- atualizar cada HTML em commits separados apenas para quebrar cache;
- empilhar uma nova camada de CSS sobre uma camada antiga para “corrigir” o visual;
- disparar uma sequência de commits enquanto Pages/Quality ainda estão processando a mesma entrega;
- usar `git push` de snapshot para responder a mudança puramente visual.

Quando vários arquivos fazem parte da mesma entrega, eles devem ser preparados e persistidos no mesmo tree/commit.

## CSS

`styles.css` deve ter:

- um único `:root`;
- uma única camada visual canônica;
- nenhum bloco de override de versão antiga anexado ao fim do arquivo;
- azul/branco/rosa como identidade estrutural;
- nenhuma cor usada como proxy de orientação política.

## Workflows

### Quality

Roda em todo PR para `main` e em todo push para `main`. Execuções são enfileiradas; não canceladas para “dar lugar” a commits posteriores.

### Sync eleitoral

Roda somente:

- por agenda;
- por acionamento manual.

O runtime usa `contents: read`, produz um snapshot candidato auditado como artifact e **não escreve em `main`**. A integração de atualização eleitoral passa por PR rastreável; não existe bypass permanente para o bot de sync.

## Pós-auditoria obrigatória

Uma entrega só pode ser chamada de concluída quando:

1. Quality terminar em `success`;
2. Pages build/deploy terminar em `success`;
3. não houver run `queued`, `pending` ou `in_progress` da entrega;
4. o HTML publicado usar a mesma versão de assets do `main`;
5. a home publicada contiver “Em quem eu vou votar?”;
6. a produção carregar o stylesheet canônico sem camada de override legada.

## Histórico

Falhas reais devem ser corrigidas na causa.

Commits intermediários produzidos pela mesma entrega não devem permanecer na história canônica quando puderem ser consolidados com segurança, preservando exatamente o tree final.

Logs antigos de GitHub Actions são registros do servidor e podem continuar visíveis na aba Actions mesmo após um commit deixar a história de `main`. Isso não transforma o commit em parte do estado canônico.


## Hardening de dados — 20/09/2026

Para snapshots automáticos:

- proibido usar `[skip ci]`;
- o workflow de sync executa testes e auditoria antes de exportar o artifact;
- o sync não cria commit nem faz push direto para `main`;
- o artifact registra o SHA-base, hashes dos arquivos gerados e patch do snapshot candidato;
- qualquer integração posterior em `main` ocorre por PR e dispara Quality;
- indisponibilidade da Câmara preserva estado federal previamente validado; sem estado seguro, o sync falha fechado;
- proveniência do espelho deve ser vinculada a revisão imutável e ao hash dos bytes processados.

`Pages success` isoladamente não equivale a governança concluída.
