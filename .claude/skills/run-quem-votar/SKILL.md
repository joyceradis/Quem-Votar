---
name: run-quem-votar
description: Build, run, test and drive the "Quem Votar? ES 2026" static site (Eleventy + vanilla JS). Use when asked to start or build the site, run its tests or audit, take a screenshot of a page (ficha, lista, comparação), check the UI at mobile width, or interact with the running app.
---

Quem Votar? is a static site: Eleventy compiles `src/` into `_site/`, vanilla JS in the browser reads `data/generated/*.json`, and GitHub Pages serves it under **`/Quem-Votar/`** (never the domain root). To *see* it, drive it with `.claude/skills/run-quem-votar/driver.mjs`: headless Chromium through Playwright, which starts the dev server itself (`chromium-cli` is not installed here).

All paths are relative to the repo root.

## Prerequisites

No apt packages. Node 22 and Python 3.11 are already there, and Chromium is preinstalled at `/opt/pw-browsers/chromium`: do not run `playwright install`; the driver and the test config below point at that binary.

```bash
npm ci
# Only for the full Python suite (pypdf); the system python crashes on it, see Gotchas
python3 -m venv /tmp/qv-venv && /tmp/qv-venv/bin/pip install -q -r requirements-evidence.txt
```

## Build

```bash
npm run build && npm run verify
```

`verify` prints `verify-build: OK — 654 arquivos, 10 rotas públicas conferidas.` (the count moves when files are added). `_site/`, `node_modules/` and `test-results/` are gitignored.

## Run (agent path)

Pipe commands to the driver, one per line (`#` starts a comment). It brings up Eleventy on `:4173`, launches Chromium at 390×844 (mobile first; `QV_SCALE` sets the pixel ratio, default 2), runs the lines in order, and shuts everything down at the end. Exit code is 1 if any command failed.

```bash
node .claude/skills/run-quem-votar/driver.mjs <<'EOF'
nav candidato.html?id=80002552172&cargo=governador --wait .hero-facts
wait .profile-fallback
ss ficha-governador
text #dados-eleitorais
viewport desktop
ss-full ficha-desktop
nav candidatos.html?cargo=governador --wait .qv-card
count .qv-card
click .qv-btn--compare
eval document.querySelector('#compareCount')?.textContent
errors
EOF
```

Screenshots land in `/tmp/shots/<name>.png` (`SCREENSHOT_DIR` overrides). Open them with the Read tool: looking at the image is the check.

| command | what it does |
|---|---|
| `nav <rota> [--wait <css>]` | go to a route relative to `/Quem-Votar/` and wait for the selector; clears `errors` |
| `viewport mobile\|desktop\|390x844` | resize (mobile 390×844, desktop 1200×900); keeps the DOM |
| `ss [name]` / `ss-full [name]` | viewport / full-page screenshot |
| `ss-el <name> <css>` | screenshot of one element |
| `text [css]` | `innerText` of the page or element (cut at `QV_MAX`, default 4000) |
| `count <css>` / `wait <css>` | number of matches / wait up to 15 s (failure = exit 1) |
| `eval <js>` | evaluate an expression in the page, print JSON |
| `click <css>` / `click-text <text>` / `fill <css> <text>` / `press <key>` | interact |
| `mock-json <glob> <js>` | rewrite a data JSON on the next loads; `body` is the parsed JSON |
| `errors` | same-origin console errors, HTTP failures and page errors since the last `nav` |

Routes: `index.html`, `candidatos.html?cargo=federal|estadual|governador|senador&q=<texto>&partido=<SIGLA>&page=<n>`, `candidato.html?id=<SQ_CANDIDATO>&cargo=<cargo>`, `comparar.html?ids=<id>,<id>`, `temas.html`, `sobre.html`, `apoio.html`. Example IDs (`SQ_CANDIDATO`): `80002552172` Ricardo Ferraço (governador), `80002551370` Renato Casagrande (senador), `80002542403` Amaro Neto (federal, with thematic evidence), `80002531645` Ailana Pelissari (federal).

`mock-json` is how you see a state the real snapshot does not have (a candidate who renounced, a data gap) without touching generated data — the e2e tests do the same with `page.route`. The glob gets `**` appended, because the data is requested with a `?v=` query:

```bash
node .claude/skills/run-quem-votar/driver.mjs <<'EOF'
mock-json **/data/generated/candidates-governador.json body[0].registration_status = "RENÚNCIA"
nav candidatos.html?cargo=governador --wait .qv-card
eval [...document.querySelectorAll('.qv-card-status')].map(e => e.textContent)
ss-el card-renuncia .qv-card
EOF
```

To reuse a server that is already running (for example `npm start`), set `QV_BASE`; the driver then leaves it alone:

```bash
QV_BASE=http://localhost:8080/Quem-Votar/ node .claude/skills/run-quem-votar/driver.mjs <<'EOF'
nav sobre.html
text h1
EOF
```

## Run (human path)

```bash
npm start   # Eleventy dev server with live reload at http://localhost:8080/Quem-Votar/
```

Useless headless. Stop it by its port (never `pkill -f`, see Gotchas):

```bash
lsof -ti:8080 -sTCP:LISTEN | xargs -r kill
```

## Test

```bash
npx playwright test -c .claude/skills/run-quem-votar/playwright.local.config.js
```

About 105–108 pass in ~50 s: desktop and mobile projects, with its own server on `:4173`. Add a spec path or `-g <title>` to narrow it. The `-c` file is `playwright.config.js` plus the Chromium path; plain `npx playwright test` fails here, see Troubleshooting. Two things vary between runs and are not your change: `home.spec.js › carrega sem erro de console nem requisição quebrada` fails now and then locally (2 of 12 isolated runs: it reloads with `networkidle` and aborts its own in-flight requests as `falhou …/data/generated/….json?v=…`; CI retries once), and 2–4 tests skip themselves on data conditions (`foto indisponível…`, `toda evidência em PROPÕE…`).

```bash
/tmp/qv-venv/bin/python -m unittest discover -s tests -p 'test_*.py'
python3 scripts/audit-site.py
```

294 tests pass in the venv (the number grows with the suite). `audit-site.py` ends with `AUDITORIA OK | ...`. CI runs the same checks (`audit`, `frontend-v6`) plus the "Cerca" fence: a PR that touches protected paths (`scripts/sync-data.py`, `scripts/audit-site.py`, `docs/CHECKPOINT_CURRENT.md`, `.github/workflows/`…) needs `Authorization-Issue: #N` in its body, and one that changes `data/generated/*` must also change the checkpoint.

## After editing `src/`

GitHub Pages publishes the repo root (there is no deploy workflow), not `_site/`. So `js/`, `styles/` and the root `*.html` are committed copies of the build output and must match `src/js`, `src/styles` and `_site/*.html`. The dev server and the e2e tests serve `src/`, so a stale root copy still passes them and only shows up in production; `audit-site.py` reads the root copies.

```bash
cp -r src/js/. js/ && cp -r src/styles/. styles/
diff -rq src/js js && diff -rq src/styles styles && echo espelhos-ok
# After editing a .njk template: rebuild and copy that page
npm run build && cp _site/sobre.html sobre.html
```

## Direct invocation (pipeline code)

`scripts/sync-data.py` has a hyphen in its name, so tests load it with `importlib`. Do the same to call its helpers without the full sync:

```bash
python3 - <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("sync_data", "scripts/sync-data.py")
sync = importlib.util.module_from_spec(spec); sys.modules[spec.name] = sync; spec.loader.exec_module(sync)
print(sync._normalize_social_links(["https://chat.whatsapp.com/abc", "https://www.instagram.com/fulano/"]))
print(sync._scrub_asset_description("BANCO: 104 AGÊNCIA: 1234 CONTA: 12345-6, CPF NO 123.456.789-09"))
PY
```

Prints `['https://www.instagram.com/fulano/']` and `BANCO: 104 AGÊNCIA: 1234 CONTA: [omitida], CPF NO [omitido]`.

## Gotchas

- **The site only exists under `/Quem-Votar/`.** `http://localhost:8080/candidatos.html` is a 404. Production also lives under a subpath, so an absolute asset path (`/styles/…`) works locally and breaks there; `npm run verify` checks for them.
- **Third-party hosts are blocked here** (candidate photos from `realidadebrasil.com.br`, Google Analytics). Photos stay a blank box for a moment and then become the monogram fallback; that is intended, not a bug (`wait .profile-fallback` on a ficha, `wait .photo-fallback` on the list, if you want the fallback in the shot). `errors` ignores other origins on purpose. The pages render after their JSON fetches, so wait for the element you need (`--wait <selector>`), not for the load event.
- **`data/generated/*` is generated and never hand-edited.** The full `python3 scripts/sync-data.py` cannot run here (`HTTP Error 403: Forbidden`, exit 1, files untouched). Regenerate through the `sync-data.yml` workflow (`workflow_dispatch`): it publishes a `data/sync-<run>` branch for the PR.
- **`audit-site.py` polices the public markup.** The word "selo" is rejected anywhere in the JS or HTML, comments included (the asserts in `scripts/audit-site.py` list the rest).
- **The system `python3` crashes importing `pypdf`** (`pyo3_runtime.PanicException`, 20 errors in the suite). It is the OS `cryptography` package; the venv above installs a working one.
- **`pkill -f "eleventy --serve"` kills your own shell** (exit 144), because the pattern matches the command line running it. Kill by port, or `pgrep -f "[e]leventy.*--serve" | xargs -r kill`.

## Troubleshooting

- **`Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1243/…` from `npx playwright test`:** the Playwright pinned in `package.json` (1.63) wants a Chromium build that is not installed; only `chromium-1194` is. Use the `-c .claude/skills/run-quem-votar/playwright.local.config.js` command above. The driver already falls back to `/opt/pw-browsers/chromium` (or `QV_CHROMIUM`).
- **`AssertionError: UI pública não deve expor jargão "selo"`:** see Gotchas; reword the text in `src/`, then re-sync the mirror.
- **`ERROR ao iniciar: Eleventy não subiu (saiu com código 1); /tmp/qv-serve.log: …`:** the dev server the driver started died (broken `.eleventy.js` or template, busy port); the message ends with the log tail, the full log is `/tmp/qv-serve.log`.
