#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate-social-previews.py"
SPEC = importlib.util.spec_from_file_location("social_previews", MODULE_PATH)
previews = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = previews
assert SPEC.loader is not None
SPEC.loader.exec_module(previews)


def candidate(cid: str, kind: str = "federal") -> dict:
    return {
        "tse_id": cid,
        "ballot_name": "MARIA & TESTE",
        "full_name": "MARIA DE TESTE",
        "number": 1234,
        "office": "DEPUTADO FEDERAL" if kind == "federal" else "DEPUTADO ESTADUAL",
        "party": "ABC",
        "photo_url": f"https://example.org/{cid}.jpg",
        "_kind": kind,
    }


class StaticSocialPreviewTests(unittest.TestCase):
    def test_render_contains_static_og_and_dynamic_profile_redirect(self) -> None:
        html = previews.render_preview(candidate("80000000001"))
        self.assertIn(
            'property="og:url" content="https://joyceradis.github.io/Quem-Votar/social/80000000001/"',
            html,
        )
        self.assertIn("candidato.html?id=80000000001&amp;cargo=federal", html)
        self.assertIn('property="og:title"', html)
        self.assertIn('property="og:description"', html)
        self.assertIn('property="og:image"', html)
        self.assertIn("MARIA &amp; TESTE", html)
        self.assertIn("<body></body>", html)
        self.assertNotIn("<main", html)
        self.assertNotIn("<p>", html)
        self.assertNotIn("googletagmanager.com", html)
        self.assertNotIn('name="twitter:', html)
        self.assertNotIn("score", html.lower())
        self.assertNotIn("recomend", html.lower())

    def test_generate_is_one_to_one_by_sq_candidato(self) -> None:
        rows = [
            candidate("80000000001", "federal"),
            candidate("80000000002", "estadual"),
        ]
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            previews, "load_candidates", return_value=rows
        ):
            out = Path(tmp) / "social"
            manifest = previews.generate(output_dir=out)

            self.assertEqual(2, manifest["candidate_count"])
            self.assertEqual(
                ["80000000001", "80000000002"],
                manifest["candidate_ids"],
            )
            self.assertTrue((out / "80000000001" / "index.html").exists())
            self.assertTrue((out / "80000000002" / "index.html").exists())
            self.assertTrue((out / "manifest.json").exists())

    def test_invalid_candidate_identity_fails_closed(self) -> None:
        bad = candidate("not-an-sq")
        with self.assertRaisesRegex(RuntimeError, "SQ_CANDIDATO inválido"):
            previews.render_preview(bad)


if __name__ == "__main__":
    unittest.main()
