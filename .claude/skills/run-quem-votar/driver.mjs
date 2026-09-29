#!/usr/bin/env node
// Driver de agente para o site "Quem Votar? ES 2026" (Eleventy estático, servido sob /Quem-Votar/).
//
// Lê comandos de stdin, um por linha, e os executa num Chromium headless via Playwright.
// Sobe o servidor de desenvolvimento (Eleventy) sozinho se ele ainda não estiver no ar e o
// derruba no fim. Serve para conferir a interface de verdade (screenshot, texto, erros),
// não só os testes.
//
//   node .claude/skills/run-quem-votar/driver.mjs <<'EOF'
//   nav candidatos.html?cargo=governador --wait .qv-card
//   ss governadores
//   EOF
//
// Variáveis: QV_BASE (usa um servidor já no ar, ex. http://localhost:8080/Quem-Votar/),
// SCREENSHOT_DIR (padrão /tmp/shots), QV_CHROMIUM (caminho do executável do Chromium),
// QV_SCALE (deviceScaleFactor, padrão 2), QV_MAX (limite de caracteres do `text`, padrão 4000).
import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import * as readline from "node:readline";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("@playwright/test");

const REPO = path.resolve(import.meta.dirname, "../../..");
const SHOT_DIR = process.env.SCREENSHOT_DIR || "/tmp/shots";
const SERVE_LOG = "/tmp/qv-serve.log";
const PORT = 4173;
const BASE = (process.env.QV_BASE || `http://127.0.0.1:${PORT}/Quem-Votar/`).replace(/\/?$/, "/");
const SCALE = Number(process.env.QV_SCALE || 2);
const MAX_TEXT = Number(process.env.QV_MAX || 4000);
const VIEWPORTS = { mobile: { width: 390, height: 844 }, desktop: { width: 1200, height: 900 } };
fs.mkdirSync(SHOT_DIR, { recursive: true });

let server = null; // processo do Eleventy, se fomos nós que subimos
let browser = null;
let context = null;
let page = null;
let viewport = VIEWPORTS.mobile;
let errors = [];
let shotCount = 0;
let failed = false;
const mocks = []; // [{ glob, transform }]

const say = (...args) => console.log(...args);
const fail = (...args) => {
  failed = true;
  console.log("ERROR:", ...args);
};

async function up(url) {
  try {
    return (await fetch(url)).ok;
  } catch {
    return false;
  }
}

async function ensureServer() {
  const probe = new URL("candidatos.html", BASE).href;
  if (await up(probe)) return say(`servidor já no ar: ${BASE}`);
  if (process.env.QV_BASE) throw new Error(`QV_BASE=${BASE} não responde`);
  const log = fs.openSync(SERVE_LOG, "w");
  // Direto pelo binário: `npx`/`npm` não repassam SIGTERM ao Eleventy, e a porta ficaria presa.
  server = spawn(path.join(REPO, "node_modules/.bin/eleventy"), ["--serve", `--port=${PORT}`, "--quiet"], {
    cwd: REPO,
    env: { ...process.env, QV_DEV: "1" },
    stdio: ["ignore", log, log],
  });
  for (let i = 0; i < 120; i++) {
    if (await up(probe)) return say(`servidor subiu: ${BASE} (log em ${SERVE_LOG})`);
    if (server.exitCode !== null) break; // o Eleventy morreu (config quebrada, porta ocupada…): não espera os 60 s
    await new Promise((r) => setTimeout(r, 500));
  }
  const tail = fs.readFileSync(SERVE_LOG, "utf8").trim().split("\n").slice(-12).join("\n");
  throw new Error(`Eleventy não subiu (${server.exitCode === null ? "sem resposta em 60 s" : `saiu com código ${server.exitCode}`}); ${SERVE_LOG}:\n${tail}`);
}

async function launchBrowser() {
  // O Playwright fixado no package.json pode pedir um build do Chromium que este ambiente não
  // tem (só há o de /opt/pw-browsers). Tenta o padrão e cai para o executável pré-instalado.
  const tries = [process.env.QV_CHROMIUM, undefined, "/opt/pw-browsers/chromium"];
  let last;
  for (const executablePath of tries) {
    if (executablePath !== undefined && !fs.existsSync(executablePath)) continue;
    try {
      return await chromium.launch(executablePath ? { executablePath } : {});
    } catch (e) {
      last = e;
    }
  }
  throw last;
}

// Terceiros (foto, Google Analytics) falham por rede neste ambiente: só a nossa origem conta.
function watch(p) {
  const ours = (url) => {
    try {
      return new URL(url).origin === new URL(BASE).origin;
    } catch {
      return false;
    }
  };
  p.on("pageerror", (e) => errors.push(`pageerror: ${e}`));
  p.on("console", (m) => {
    if (m.type() === "error" && !/^Failed to load resource\b/.test(m.text())) errors.push(`console: ${m.text()}`);
  });
  p.on("response", (r) => {
    if (!r.ok() && ours(r.url())) errors.push(`${r.status()} ${r.url()}`);
  });
  p.on("requestfailed", (r) => {
    if (ours(r.url())) errors.push(`falhou ${r.url()}`);
  });
}

async function applyMock({ glob, transform }) {
  await context.route(glob, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    const out = transform(body);
    await route.fulfill({ response, json: out === undefined ? body : out });
  });
}

async function newContext() {
  context = await browser.newContext({ viewport, deviceScaleFactor: SCALE, locale: "pt-BR" });
  page = await context.newPage();
  watch(page);
}

// Aceita o seletor entre aspas (`count "#dados-eleitorais a"`): as aspas não fazem parte dele.
const unquote = (s) => String(s).replace(/^(["'])(.*)\1$/, "$2");
const need = () => {
  if (!page) throw new Error("sem página: rode `nav <rota>` primeiro");
};
const shotPath = (name) => path.join(SHOT_DIR, `${name || `ss-${String(++shotCount).padStart(2, "0")}`}.png`);
const short = (s, n = 200) => (String(s).length > n ? `${String(s).slice(0, n)}…` : String(s));

const COMMANDS = {
  // nav <rota relativa a /Quem-Votar/ ou URL> [--wait <seletor>]
  async nav(arg) {
    const [target, flag, ...sel] = arg.split(/\s+/);
    if (!target) return fail("uso: nav <rota> [--wait <seletor>]");
    errors = [];
    const url = new URL(target, BASE).href;
    const res = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
    if (flag === "--wait") await page.waitForSelector(unquote(sel.join(" ")), { timeout: 15_000 });
    const h1 = await page.locator("h1").first().innerText({ timeout: 1000 }).catch(() => "(sem h1 ainda)");
    say(`nav ${res?.status()} ${page.url()} | ${await page.title()} | h1: ${short(h1.replace(/\s+/g, " "), 80)}`);
  },

  // viewport mobile | desktop | <L>x<A>   (mobile = 390x844, desktop = 1200x900)
  async viewport(arg) {
    const m = /^(\d+)x(\d+)$/.exec(arg);
    const size = VIEWPORTS[arg] || (m && { width: Number(m[1]), height: Number(m[2]) });
    if (!size) return fail("uso: viewport mobile | desktop | 390x844");
    viewport = size;
    await page.setViewportSize(viewport); // só redimensiona: o DOM e os mocks continuam
    say(`viewport ${viewport.width}x${viewport.height}`);
  },

  async ss(name) {
    need();
    const file = shotPath(name);
    await page.screenshot({ path: file });
    say("screenshot:", file);
  },

  async "ss-full"(name) {
    need();
    const file = shotPath(name);
    await page.screenshot({ path: file, fullPage: true });
    say("screenshot:", file);
  },

  // ss-el <nome> <seletor>
  async "ss-el"(arg) {
    need();
    const [name, ...sel] = arg.split(/\s+/);
    if (!name || !sel.length) return fail("uso: ss-el <nome> <seletor>");
    const file = shotPath(name);
    await page.locator(unquote(sel.join(" "))).first().screenshot({ path: file, timeout: 10_000 });
    say("screenshot:", file);
  },

  async text(sel) {
    need();
    const t = await page.evaluate((s) => (s ? document.querySelector(s) : document.body)?.innerText ?? "(seletor sem resultado)", sel ? unquote(sel) : null);
    say(t.length > MAX_TEXT ? `${t.slice(0, MAX_TEXT)}\n…(truncado em ${MAX_TEXT} de ${t.length} caracteres; QV_MAX aumenta)` : t);
  },

  async count(sel) {
    need();
    say(`count ${sel}: ${await page.locator(unquote(sel)).count()}`);
  },

  async eval(expr) {
    need();
    say(JSON.stringify(await page.evaluate(expr)));
  },

  async wait(sel) {
    need();
    await page.waitForSelector(unquote(sel), { timeout: 15_000 }).then(
      () => say("found:", sel),
      () => fail("TIMEOUT esperando", sel)
    );
  },

  async click(sel) {
    need();
    await page.locator(unquote(sel)).first().click({ timeout: 5000 });
    say("click", sel, "-> OK");
  },

  async "click-text"(text) {
    need();
    await page.locator("button, a, [role=button]", { hasText: text }).first().click({ timeout: 5000 });
    say("click-text", JSON.stringify(text), "-> OK");
  },

  // fill <seletor> <texto>   (seletor sem espaços; o resto da linha é o texto)
  async fill(arg) {
    need();
    const [sel, ...rest] = arg.split(/\s+/);
    await page.fill(sel, rest.join(" "), { timeout: 5000 });
    say("fill", sel, "-> OK");
  },

  async press(key) {
    need();
    await page.keyboard.press(key);
    say("press", key, "-> OK");
  },

  // mock-json <glob> <js>: reescreve um JSON de dados. `body` é o JSON já lido; o js altera `body`.
  //   mock-json **/candidates-governador.json body[0].registration_status = "RENÚNCIA"
  // Vale para as próximas navegações. É o jeito de ver estados que o snapshot real não tem (lacuna
  // de fonte, renúncia) sem editar dado gerado. O JSON é pedido com query string (?v=…): o glob
  // ganha `**` no fim quando não termina em `*`, senão não casa.
  async "mock-json"(arg) {
    const [pattern, ...rest] = arg.split(/\s+/);
    const code = rest.join(" ");
    if (!pattern || !code) return fail("uso: mock-json <glob> <js que altera body>");
    const glob = pattern.endsWith("*") ? pattern : `${pattern}**`;
    const transform = new Function("body", `${code};\nreturn body;`);
    mocks.push({ glob, transform });
    await applyMock(mocks[mocks.length - 1]);
    say("mock-json", glob, "-> ativo");
  },

  // Erros da nossa origem desde o último `nav` (terceiros bloqueados na rede são ignorados).
  async errors() {
    if (!errors.length) return say("errors: nenhum");
    say(`errors: ${errors.length}`);
    for (const e of errors) say("  ", short(e, 300));
    failed = true;
  },

  async quit() {},

  help() {
    say("comandos:", Object.keys(COMMANDS).join(", "));
  },
};

async function shutdown() {
  await browser?.close().catch(() => {});
  if (server) server.kill("SIGTERM");
}

try {
  await ensureServer();
  browser = await launchBrowser();
  await newContext();
  say(`driver pronto | base ${BASE} | viewport ${viewport.width}x${viewport.height} | screenshots em ${SHOT_DIR}`);
} catch (e) {
  console.log("ERROR ao iniciar:", e.message);
  await shutdown();
  process.exit(1);
}

process.on("SIGINT", async () => {
  await shutdown();
  process.exit(130);
});

const rl = readline.createInterface({ input: process.stdin });
for await (const raw of rl) {
  const line = raw.trim();
  if (!line || line.startsWith("#")) continue;
  const [cmd, ...rest] = line.split(/\s+/);
  const arg = line.slice(cmd.length).trim();
  say(`> ${line}`);
  const fn = COMMANDS[cmd];
  if (!fn) {
    fail("comando desconhecido:", cmd, "(help lista os comandos)");
    continue;
  }
  if (cmd === "quit") break;
  try {
    await fn(arg);
  } catch (e) {
    fail(short(String(e.message).split("\n")[0], 300));
  }
}
await shutdown();
process.exit(failed ? 1 : 0);
