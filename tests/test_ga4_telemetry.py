#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
MEASUREMENT_ID = "G-2KY1FDKV88"
CANONICAL_ROOT = "https://joyceradis.github.io/Quem-Votar/"
PUBLIC_PAGES = [
    "index.html",
    "candidatos.html",
    "candidato.html",
    "comparar.html",
    "temas.html",
    "sobre.html",
    "apoio.html",
]
BOOTSTRAP = '<script src="telemetry.js?v=1"></script>'


def run_telemetry(href, referrer=""):
    node_script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const vm = require("vm");
        const appended = [];
        const sandbox = {{
          console,
          Date,
          URL,
          encodeURIComponent,
          location: {{ href: {json.dumps(href)} }},
          document: {{
            title: "NOME DE CANDIDATO · Quem Votar?",
            referrer: {json.dumps(referrer)},
            createElement(tag) {{
              if (tag !== "script") throw new Error("unexpected element");
              return {{ dataset: {{}}, async: false, src: "" }};
            }},
            head: {{
              appendChild(node) {{
                appended.push({{
                  src: node.src,
                  async: node.async,
                  dataset: node.dataset,
                }});
              }},
            }},
          }},
        }};
        sandbox.window = sandbox;
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync("telemetry.js", "utf8"), sandbox);
        const commands = sandbox.dataLayer.map(entry => Array.from(entry));
        const config = commands.find(entry => entry[0] === "config");
        const pageViews = commands.filter(
          entry => entry[0] === "event" && entry[1] === "page_view"
        );
        const otherEvents = commands.filter(
          entry => entry[0] === "event" && entry[1] !== "page_view"
        );
        process.stdout.write(JSON.stringify({{
          config,
          pageViews,
          otherEvents,
          appended,
        }}));
        """
    )
    completed = subprocess.run(
        ["node", "-e", node_script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


class GA4TelemetryTests(unittest.TestCase):
    def test_privacy_bootstrap_present_once_on_every_public_page(self):
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                text = (ROOT / page).read_text(encoding="utf-8")
                self.assertEqual(1, text.count(BOOTSTRAP))
                self.assertNotIn("googletagmanager.com/gtag/js?id=", text)
                self.assertNotIn("gtag('config',", text)
                self.assertNotIn(MEASUREMENT_ID, text)

    def test_measurement_id_and_privacy_controls_are_centralized(self):
        text = (ROOT / "telemetry.js").read_text(encoding="utf-8")
        self.assertEqual(1, text.count(MEASUREMENT_ID))
        self.assertIn('const CANONICAL_ORIGIN = "https://joyceradis.github.io"', text)
        self.assertIn('const PROJECT_BASE_PATH = "/Quem-Votar/"', text)
        self.assertIn("googletagmanager.com/gtag/js?id=", text)
        self.assertIn("send_page_view: false", text)
        self.assertIn("allow_google_signals: false", text)
        self.assertIn("allow_ad_personalization_signals: false", text)
        self.assertIn("current.origin !== CANONICAL_ORIGIN", text)

    def test_candidate_page_drops_identity_query_hash_and_dynamic_title(self):
        result = run_telemetry(
            "https://joyceradis.github.io/Quem-Votar/candidato.html"
            "?id=123456789&tema=saude#perfil"
        )
        config = result["config"]
        page_view = result["pageViews"][0]
        self.assertEqual(1, len(result["pageViews"]))
        self.assertEqual([], result["otherEvents"])
        self.assertEqual(MEASUREMENT_ID, config[1])
        self.assertFalse(config[2]["send_page_view"])
        self.assertEqual(
            "https://joyceradis.github.io/Quem-Votar/candidato.html",
            config[2]["page_location"],
        )
        self.assertEqual("", config[2]["page_referrer"])
        self.assertEqual(
            "Entenda esta candidatura · Quem Votar?",
            config[2]["page_title"],
        )
        self.assertFalse(config[2]["allow_google_signals"])
        self.assertFalse(config[2]["allow_ad_personalization_signals"])
        self.assertEqual(config[2]["page_location"], page_view[2]["page_location"])
        self.assertEqual(config[2]["page_title"], page_view[2]["page_title"])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("123456789", serialized)
        self.assertNotIn("saude", serialized)
        self.assertNotIn("NOME DE CANDIDATO", serialized)

    def test_all_electoral_query_state_is_excluded(self):
        cases = {
            "id": "80002549468",
            "ids": "101,202,303",
            "q": "nome-secreto",
            "tema": "saude",
            "partido": "XYZ",
            "cargo": "federal",
            "page": "7",
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                result = run_telemetry(
                    f"https://joyceradis.github.io/Quem-Votar/candidatos.html?{key}={value}#estado"
                )
                serialized = json.dumps(result, ensure_ascii=False)
                self.assertNotIn(value, serialized)
                self.assertNotIn("#estado", serialized)
                self.assertEqual(
                    "https://joyceradis.github.io/Quem-Votar/candidatos.html",
                    result["config"][2]["page_location"],
                )

    def test_unknown_social_and_noncanonical_origins_fail_closed(self):
        urls = [
            "https://joyceradis.github.io/Quem-Votar/social/80002549468/index.html",
            "https://joyceradis.github.io/Quem-Votar/desconhecida/80002549468",
            "https://evil.example/Quem-Votar/candidato.html?id=80002549468",
        ]
        for url in urls:
            with self.subTest(url=url):
                result = run_telemetry(url)
                self.assertEqual(CANONICAL_ROOT, result["config"][2]["page_location"])
                self.assertEqual(
                    "Quem Votar? · Espírito Santo 2026",
                    result["config"][2]["page_title"],
                )
                self.assertNotIn("80002549468", json.dumps(result))

    def test_referrer_is_allowlisted_and_sanitized_independently(self):
        internal = run_telemetry(
            "https://joyceradis.github.io/Quem-Votar/candidato.html?id=111",
            "https://joyceradis.github.io/Quem-Votar/candidatos.html?q=SEGREDO#x",
        )
        self.assertEqual(
            "https://joyceradis.github.io/Quem-Votar/candidatos.html",
            internal["config"][2]["page_referrer"],
        )
        self.assertNotIn("SEGREDO", json.dumps(internal))

        external = run_telemetry(
            "https://joyceradis.github.io/Quem-Votar/candidato.html?id=111",
            "https://search.example/?q=SEGREDO",
        )
        self.assertEqual("", external["config"][2]["page_referrer"])
        self.assertNotIn("SEGREDO", json.dumps(external))

        unknown_internal = run_telemetry(
            "https://joyceradis.github.io/Quem-Votar/",
            "https://joyceradis.github.io/Quem-Votar/social/111/index.html",
        )
        self.assertEqual("", unknown_internal["config"][2]["page_referrer"])
        self.assertNotIn("111", json.dumps(unknown_internal))

    def test_loader_is_added_once_with_only_canonical_measurement_id(self):
        result = run_telemetry(CANONICAL_ROOT)
        self.assertEqual(1, len(result["appended"]))
        loader = result["appended"][0]
        self.assertTrue(loader["async"])
        self.assertEqual(
            "https://www.googletagmanager.com/gtag/js?id=" + MEASUREMENT_ID,
            loader["src"],
        )
        self.assertEqual("privacy", loader["dataset"]["qvGa4"])


if __name__ == "__main__":
    unittest.main()
