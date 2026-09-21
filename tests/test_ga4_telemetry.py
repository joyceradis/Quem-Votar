#!/usr/bin/env python3
from pathlib import Path
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

EXPECTED_SRC = (
    '<script async src="https://www.googletagmanager.com/gtag/js?'
    f'id={MEASUREMENT_ID}"></script>'
)
EXPECTED_CONFIG = f"gtag('config', '{MEASUREMENT_ID}');"


class GA4TelemetryTests(unittest.TestCase):
    def test_google_tag_present_once_on_every_public_page(self):
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                text = (ROOT / page).read_text(encoding="utf-8")
                self.assertIn("<head>\n<!-- Google tag (gtag.js) -->", text)
                self.assertEqual(1, text.count(EXPECTED_SRC))
                self.assertEqual(1, text.count(EXPECTED_CONFIG))
                self.assertEqual(2, text.count(MEASUREMENT_ID))
                self.assertLess(text.index(EXPECTED_SRC), text.index("</head>"))

    def test_no_other_ga_measurement_id_is_embedded(self):
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                text = (ROOT / page).read_text(encoding="utf-8")
                ga_lines = [
                    line for line in text.splitlines()
                    if "googletagmanager.com/gtag/js?id=" in line
                    or "gtag('config'," in line
                ]
                self.assertTrue(ga_lines)
                self.assertTrue(all(MEASUREMENT_ID in line for line in ga_lines))


if __name__ == "__main__":
    unittest.main()
