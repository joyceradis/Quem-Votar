#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[v6] install"
python -m pip install -r requirements-evidence.txt
npm ci

echo "[v6] pre-cutover gates"
npm run build
npm run verify
npx playwright install --with-deps chromium
npm run test:e2e
python scripts/audit-site.py
python -m unittest discover -s tests -p 'test_*.py' -v

echo "[v6] replace public V5 tree with V6 build"
git rm -q app.js styles.css
rm -rf styles js

for rota in index candidatos candidato comparar temas sobre apoio; do
  cp "_site/${rota}.html" "${rota}.html"
done
cp -r _site/styles styles
cp -r _site/js js

python scripts/generate-social-previews.py
python scripts/reconcile-v6-release.py

echo "[v6] post-cutover gates"
for rota in index candidatos candidato comparar temas sobre apoio; do
  cmp "_site/${rota}.html" "${rota}.html"
done
diff -qr _site/styles styles
diff -qr _site/js js

python scripts/audit-site.py
python -m unittest discover -s tests -p 'test_*.py' -v

python -m py_compile \
  scripts/sync-data.py \
  scripts/audit-site.py \
  scripts/coletor_evidencias.py \
  scripts/evidence_coverage_report.py \
  scripts/discover_evidence_sources.py \
  scripts/process_evidence_batch.py \
  scripts/build_exception_queue.py \
  scripts/generate-social-previews.py

find src/js -type f -name '*.js' -print0 | xargs -0 -n1 node --check

test ! -e app.js
test ! -e styles.css
test -d js
test -d styles

echo "[v6] remove one-shot control plane from release tree"
rm -f .v6-cutover-trigger
git rm -q .github/workflows/v6-cutover-executor.yml
git rm -q scripts/run-v6-cutover-authorized.sh scripts/reconcile-v6-release.py

git add -A

python - <<'PY'
import subprocess

changed = subprocess.check_output(
    ["git", "diff", "--cached", "--name-only"],
    text=True,
).splitlines()

exact = {
    "index.html",
    "candidatos.html",
    "candidato.html",
    "comparar.html",
    "temas.html",
    "sobre.html",
    "apoio.html",
    "app.js",
    "styles.css",
    "README.md",
    "docs/CHECKPOINT_CURRENT.md",
    "docs/SITE_MAP.md",
    "docs/REBUILD_V6.md",
    "scripts/cutover-v6.sh",
    ".github/workflows/quality.yml",
    ".github/workflows/v6-cutover-executor.yml",
    "scripts/run-v6-cutover-authorized.sh",
    "scripts/reconcile-v6-release.py",
    ".v6-cutover-trigger",
}
prefixes = ("styles/", "js/", "social/")

unexpected = [
    path for path in changed
    if path not in exact and not path.startswith(prefixes)
]
if unexpected:
    raise SystemExit("unexpected cutover paths: " + ", ".join(unexpected))

data_changes = [path for path in changed if path.startswith("data/")]
if data_changes:
    raise SystemExit("cutover must not modify data/: " + ", ".join(data_changes))

required = {"index.html", "app.js", "styles.css"}
missing = sorted(required.difference(changed))
if missing:
    raise SystemExit("expected cutover paths missing: " + ", ".join(missing))

print(f"cutover paths: {len(changed)}")
print("\n".join(changed))
PY
