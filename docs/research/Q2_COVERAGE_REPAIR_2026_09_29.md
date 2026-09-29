# Q2 — diagnóstico e reparo de cobertura

Contrato: #2. Base: `855198e051033b83402b951df379cf6a5b4b1d2b`.

## Causa confirmada

A interface carrega 563 candidaturas, mas o coletor e o CLI do ledger ainda
carregavam somente Federal/Estadual (547). As 16 majoritárias eram excluídas
da descoberta, coleta e validação comum. Além disso, a descoberta de sites
reutilizava somente seeds recém-obtidas do TSE, ignorando destinos já
pesquisados ou derivados de agregadores em ciclos anteriores.

O caso Callegari já tem um rascunho em
`data/staging/issue161-majoritarian-proposal-drafts.json`; não é um problema
de renderização. Esse arquivo contém 16 rascunhos para 16 candidaturas,
todos ainda fora da publicação canônica. O snapshot tem Q2 prospectiva em
2 candidaturas; as 10 entradas prospectivas canônicas estão sincronizadas.
Não foi encontrada perda entre canônico e snapshot neste checkout.

## Correção técnica

- Coletor e ledger carregam os quatro cargos, mantendo unicidade de SQ_CANDIDATO.
- Discovery retoma seeds existentes e elimina duplicatas antes das requisições.
- Ledger separa Q2 publicada, canônica ainda não sincronizada e staging não promovido.
- Timestamp global deixa de certificar descoberta de candidaturas não listadas no run.
- Onze fontes já pesquisadas entram na fila comum: 8 matérias específicas e 3 sites como seeds.
- Sete matérias foram capturadas pelo coletor comum, com hashes, datas e menção nominal. Os sete drafts permanecem `pending`; uma fonte respondeu HTTP 429.
- Os cinco planos de governo foram obtidos diretamente do pacote oficial TSE; hashes, membros ZIP, páginas e suporte textual foram materializados em staging.
- O mapa legado de ocupações é identificado como legado; evidência usa `policy-topics.json`.

## Reprodução

```sh
python scripts/evidence_coverage_report.py --output /tmp/qv-q2-coverage.json
python scripts/coletor_evidencias.py validate
python -m unittest discover -s tests -p 'test_*.py'
npm run build
npm run verify
python scripts/audit-site.py
```

O relatório resumido versionado está em
`data/staging/q2-coverage-repair-summary.json`. Seus números descrevem
o checkout/staging versionado; não substituem os artifacts do worker.
As 563 candidaturas são contabilizadas. Staging não é aprovação e atuação
histórica não é promessa atual. Nenhuma evidência canônica foi alterada.

## Próximo gate de conteúdo

Os sete novos drafts capturados precisam de seleção de suporte textual e
revisão semântica; a fonte com HTTP 429 precisa de nova tentativa.
Os demais rascunhos de pesquisa precisam de captura verificável, suporte textual,
atribuição e revisão independente antes da aprovação humana e promoção.
Sites com propostas no corpo da página inicial continuam seeds: não relaxar
silenciosamente a regra que rejeita perfis/URLs genéricas como evidência.
A nova captura direta dos cinco planos oficiais substitui a dependência do espelho. Os cinco registros concretos em `data/staging/tse-q2-publication-proposal.json` precisam de revisão independente e aprovação humana; o resumo de Ricardo foi ajustado para preservar “apoio diagnóstico”.
Somente após esses gates, sync e publicação poderão preencher Q2 e derivar Q3.

O reparo técnico permite processamento uniforme dos quatro cargos; ele não
declara encerrada a cobertura editorial da #2 nem promove os 16 rascunhos.
