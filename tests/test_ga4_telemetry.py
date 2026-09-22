#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
MEASUREMENT_ID = "G-2KY1FDKV88"
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


def run_telemetry(href, script_src="https://joyceradis.github.io/Quem-Votar/telemetry.js?v=1"):
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
            currentScript: {{ src: {json.dumps(script_src)} }},
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

    def test_measurement_id_and_loader_are_centralized(self):
        text = (ROOT / "telemetry.js").read_text(encoding="utf-8")
        self.assertEqual(1, text.count(MEASUREMENT_ID))
        self.assertIn("googletagmanager.com/gtag/js?id=", text)
        self.assertIn("send_page_view: false", text)
        self.assertIn("allow_google_signals: false", text)
        self.assertIn("allow_ad_personalization_signals: false", text)
        self.assertIn('page_referrer: ""', text)

    def test_candidate_page_drops_identity_query_hash_referrer_and_dynamic_title(self):
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
        self.assertEqual("Entenda esta candidatura · Quem Votar?", config[2]["page_title"])
        self.assertFalse(config[2]["allow_google_signals"])
        self.assertFalse(config[2]["allow_ad_personalization_signals"])
        self.assertTrue(config[2]["ignore_referrer"])
        self.assertEqual(config[2]["page_location"], page_view[2]["page_location"])
        self.assertEqual(config[2]["page_title"], page_view[2]["page_title"])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("123456789", serialized)
        self.assertNotIn("saude", serialized)
        self.assertNotIn("NOME DE CANDIDATO", serialized)

    def test_compare_page_drops_ids_query(self):
        result = run_telemetry(
            "https://joyceradis.github.io/Quem-Votar/comparar.html"
            "?ids=101,202,303"
        )
        config = result["config"]
        self.assertEqual(
            "https://joyceradis.github.io/Quem-Votar/comparar.html",
            config[2]["page_location"],
        )
        serialized = json.dumps(result)
        self.assertNotIn("101", serialized)
        self.assertNotIn("202", serialized)
        self.assertNotIn("303", serialized)

    def test_unknown_or_identifier_path_fails_closed_to_project_root(self):
        result = run_telemetry(
            "https://joyceradis.github.io/Quem-Votar/social/123456789/index.html"
        )
        config = result["config"]
        self.assertEqual(
            "https://joyceradis.github.io/Quem-Votar/",
            config[2]["page_location"],
        )
        self.assertEqual("Quem Votar? · Espírito Santo 2026", config[2]["page_title"])
        self.assertNotIn("123456789", json.dumps(result))

    def test_loader_is_added_once_with_only_the_canonical_measurement_id(self):
        result = run_telemetry("https://joyceradis.github.io/Quem-Votar/")
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
