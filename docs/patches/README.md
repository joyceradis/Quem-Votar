# Mudanças que aguardam autorização da mantenedora

Este diretório guarda mudanças **prontas e verificadas** que tocam caminhos
protegidos pela Cerca Elétrica (`.github/workflows/agent-fence.yml`) e por
`.github/CODEOWNERS`. Elas não entram no PR da reconstrução V6: a cerca exige
uma Issue de autorização **aberta por @joyceradis**, com os rótulos
`decision-recorded` e `risk:high` e um comentário dela começando com
`## Decisão técnica após revisão`. Um agente não pode produzir isso por si —
e não deve tentar contornar.

## `v6-fase5-caminhos-protegidos.patch`

Duas mudanças, ambas necessárias **antes do corte da Fase 5** (04/10/2026):

1. **`scripts/audit-site.py` — desacoplar o auditor do nome dos arquivos.**
   Hoje ele lê `styles.css` e `app.js` por nome e casa contra o texto
   *minificado* desses arquivos. No corte esses dois arquivos deixam de
   existir (o CSS vira `styles/`, o JS vira módulos em `js/`) e a auditoria
   quebraria mesmo com o site idêntico — ela mede implementação, não
   comportamento. O patch introduz `public_css()` / `public_js()`, que
   resolvem a superfície publicada: enquanto `styles.css` e `app.js`
   existirem, o resultado é byte-a-byte o de hoje; depois do corte, passam a
   ler as pastas publicadas. As asserções que dependiam de minificação viram
   regex tolerante a espaço — mesma regra, sem depender de formatação.

2. **`.github/workflows/quality.yml` — job `frontend-v6`.**
   Roda `npm run build`, `npm run verify` e a suíte Playwright (desktop e
   mobile) a cada PR. Não toca em nada publicado: a saída do build é
   descartada no fim do job. Sem isso, a verificação da V6 depende de um
   agente rodar os comandos à mão.

Aplicar depois da autorização:

```sh
git apply docs/patches/v6-fase5-caminhos-protegidos.patch
python3 scripts/audit-site.py   # deve continuar OK antes do corte
```

Restam, para o PR do corte, as 6 asserções de `audit-site.py` que leem o
texto-fonte do `app.js` e só podem ser substituídas pelos testes de
comportamento equivalentes — a tabela está em `docs/REBUILD_V6.md`.
