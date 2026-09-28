// Verificação da saída do build (Fase 4).
//
// Existe por uma razão concreta: o site é publicado sob o subcaminho
// /Quem-Votar/, nunca na raiz do domínio. Uma prévia servida da raiz aceita
// caminho absoluto ("/styles/base.css") que em produção vira
// joyceradis.github.io/styles/base.css e dá 404. Nenhum teste de página pega
// isso. Este script pega, e ainda confere que todo arquivo referenciado pelo
// HTML gerado realmente existe na saída.
//
// Uso: node scripts/verify-build.mjs [diretorio]  (padrão: _site)
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.argv[2] || "_site");
const erros = [];

const walk = (dir) =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const full = path.join(dir, e.name);
    return e.isDirectory() ? walk(full) : [full];
  });

if (!fs.existsSync(root)) {
  console.error(`Saída não encontrada: ${root}. Rode "npm run build" antes.`);
  process.exit(2);
}

const arquivos = walk(root);
const rel = (f) => path.relative(root, f).split(path.sep).join("/");
const existentes = new Set(arquivos.map(rel));

// 1. Rotas públicas obrigatórias.
const PUBLICAS = [
  "index.html",
  "candidatos.html",
  "candidato.html",
  "comparar.html",
  "temas.html",
  "sobre.html",
  "apoio.html",
  "manifest.webmanifest",
  "data/generated/candidates-federal.json",
  "data/generated/meta.json",
];
for (const p of PUBLICAS) {
  if (!existentes.has(p)) erros.push(`rota pública ausente na saída: ${p}`);
}

// 2. Páginas internas de revisão não podem vazar para o público.
for (const interna of ["styleguide.html", "preview-shell.html"]) {
  if (existentes.has(interna)) {
    erros.push(`página interna emitida na saída pública: ${interna}`);
  }
}

// 3. Nenhuma referência absoluta a asset próprio (quebra sob /Quem-Votar/).
const REF = /(?:href|src)="(\/(?:styles|js|assets|data|social)\/[^"]*)"/g;
const CSSREF = /url\((\/(?:assets|styles)\/[^)]*)\)/g;
for (const f of arquivos.filter((f) => /\.(html|css)$/.test(f))) {
  const texto = fs.readFileSync(f, "utf8");
  for (const re of [REF, CSSREF]) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(texto))) {
      erros.push(`${rel(f)}: caminho absoluto "${m[1]}" quebra sob /Quem-Votar/`);
    }
  }
}

// 4. Todo asset local referenciado pelo HTML existe de fato na saída.
const LOCAL = /(?:href|src)="(?!https?:|mailto:|#|data:)([^"?#]+)[^"]*"/g;
for (const f of arquivos.filter((f) => f.endsWith(".html"))) {
  const texto = fs.readFileSync(f, "utf8");
  const base = path.dirname(rel(f));
  LOCAL.lastIndex = 0;
  let m;
  while ((m = LOCAL.exec(texto))) {
    const alvo = path.posix.normalize(path.posix.join(base === "." ? "" : base, m[1]));
    if (!alvo || alvo.startsWith("..")) continue;
    const ok = existentes.has(alvo) || existentes.has(`${alvo.replace(/\/$/, "")}/index.html`);
    if (!ok) erros.push(`${rel(f)}: referência quebrada "${m[1]}"`);
  }
}


// 5. Pós-cutover V6: a saída recém-gerada deve ser idêntica à superfície
// pública versionada. Isso evita drift entre `src/` e o que o Pages realmente
// publica (ex.: uma correção visual aplicada em src/styles sem regenerar
// styles/). Só roda no diretório padrão `_site`; verificações contra um
// diretório alternativo continuam podendo ser usadas isoladamente.
if (root === path.resolve("_site")) {
  const repoRoot = path.resolve(".");
  const rotasEspelhadas = [
    "index.html",
    "candidatos.html",
    "candidato.html",
    "comparar.html",
    "temas.html",
    "sobre.html",
    "apoio.html",
  ];

  const publicFiles = [];
  for (const dir of ["styles", "js"]) {
    const abs = path.join(repoRoot, dir);
    if (fs.existsSync(abs)) {
      publicFiles.push(
        ...walk(abs).map((f) => path.relative(repoRoot, f).split(path.sep).join("/")),
      );
    }
  }

  const builtFiles = arquivos
    .map(rel)
    .filter((p) => p.startsWith("styles/") || p.startsWith("js/"));

  const espelhados = new Set([...rotasEspelhadas, ...publicFiles, ...builtFiles]);

  for (const p of espelhados) {
    const gerado = path.join(root, p);
    const publicado = path.join(repoRoot, p);

    if (!fs.existsSync(gerado)) {
      erros.push(`paridade pública: arquivo existe no repositório mas não no build: ${p}`);
      continue;
    }
    if (!fs.existsSync(publicado)) {
      erros.push(`paridade pública: arquivo existe no build mas não na superfície versionada: ${p}`);
      continue;
    }

    const a = fs.readFileSync(gerado);
    const b = fs.readFileSync(publicado);
    if (!a.equals(b)) {
      erros.push(`paridade pública: build e superfície versionada divergem: ${p}`);
    }
  }
}

if (erros.length) {
  console.error(`verify-build: ${erros.length} problema(s)`);
  for (const e of [...new Set(erros)]) console.error(`  - ${e}`);
  process.exit(1);
}
console.log(`verify-build: OK — ${arquivos.length} arquivos, ${PUBLICAS.length} rotas públicas conferidas.`);
