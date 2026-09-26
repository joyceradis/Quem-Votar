#!/usr/bin/env bash
# Corte atômico da V6 (Fase 5) — executar só a partir de 2026-10-04, fim do
# feature freeze do núcleo eleitoral.
#
# Substitui a superfície pública pelos arquivos gerados, preservando as URLs
# (mesmo link, mesmos parâmetros, mesmo contrato JSON). Não roda sozinho em
# CI: é um comando único e deliberado, com auditoria antes e depois, conforme
# docs/DELIVERY_GOVERNANCE.md ("commit atômico", proibido fatiar por arquivo).
set -euo pipefail
cd "$(dirname "$0")/.."

hoje=$(date -u +%Y-%m-%d)
if [[ "$hoje" < "2026-10-04" ]]; then
  echo "Bloqueado: o freeze do núcleo eleitoral vai até 2026-10-04 (hoje: $hoje)." >&2
  exit 1
fi

echo "==> 1/6 build"
npm ci --silent
npm run build

echo "==> 2/6 verificação da saída"
npm run verify

echo "==> 3/6 comportamento (desktop e mobile)"
npm run test:e2e

echo "==> 4/6 substituindo a superfície pública"
# Some o que a V6 substitui. Os dados (data/), os assets e os stubs sociais
# não são tocados aqui: vêm do próprio build ou já estão versionados.
git rm -q app.js styles.css
rm -rf styles js
for rota in index candidatos candidato comparar temas sobre apoio; do
  cp "_site/$rota.html" "$rota.html"
done
cp -r _site/styles styles
cp -r _site/js js

echo "==> 5/6 regerando os stubs de preview social contra o markup definitivo"
python3 scripts/generate-social-previews.py

echo "==> 6/6 auditoria pós-corte"
python3 scripts/audit-site.py
python3 -m unittest discover -s tests -p 'test_*.py'

cat <<'FIM'

Corte preparado na árvore de trabalho. Falta, manualmente e em um único commit:

  - atualizar VERSION, docs/CHECKPOINT_CURRENT.md, docs/SITE_MAP.md e a linha
    de baseline visual do README.md;
  - git add -A && git commit  (um commit só — não fatiar por arquivo);
  - abrir o PR para main e conferir, depois do merge: Quality success,
    Pages success, home no ar com a copy esperada, nenhum run pendente;
  - criar a tag/release formal (AGENTS.md §7).
FIM
