#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import sys
import unittest
import zipfile
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "coletor_evidencias.py"
SPEC = importlib.util.spec_from_file_location("coletor_evidencias", MODULE_PATH)
collector = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = collector
assert SPEC.loader is not None
SPEC.loader.exec_module(collector)


PYPDF_AVAILABLE = importlib.util.find_spec("pypdf") is not None

MINIMAL_TEXT_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 86 >>
stream
BT
/F1 12 Tf
72 720 Td
(Maria Silva apresentou proposta para ampliar unidades de saude.) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000311 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
446
%%EOF
"""


class CollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = {
            "123": {
                "tse_id": "123",
                "ballot_name": "MARIA",
                "full_name": "MARIA SILVA",
                "office": "DEPUTADO ESTADUAL",
                "party": "ABC",
            }
        }

    def test_exact_content_url_rejects_roots_and_social_profiles(self) -> None:
        self.assertTrue(
            collector.is_exact_content_url(
                "https://example.org/noticias/proposta-1",
                "official_candidate",
            )
        )
        self.assertFalse(
            collector.is_exact_content_url(
                "https://example.org/",
                "official_candidate",
            )
        )
        self.assertTrue(
            collector.is_exact_content_url(
                "https://www.instagram.com/p/ABC123/",
                "tse_declared_social",
            )
        )
        self.assertFalse(
            collector.is_exact_content_url(
                "https://www.instagram.com/candidato/",
                "tse_declared_social",
            )
        )

    def test_tse_socials_are_discovery_seeds_not_evidence(self) -> None:
        csv_text = (
            "SG_UF;SQ_CANDIDATO;NR_ORDEM;DS_URL\n"
            "ES;123;1;https://instagram.com/teste\n"
            "RJ;999;1;https://instagram.com/outro\n"
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "rede_social_candidato_2026.csv",
                csv_text.encode("latin-1"),
            )

        def fake_fetch(url: str, **kwargs):
            return buffer.getvalue(), url, "application/zip"

        sources = collector.discover_tse_social_sources(
            candidates=self.candidates,
            fetcher=fake_fetch,
        )
        self.assertEqual(1, len(sources))
        self.assertEqual("123", sources[0]["candidate_id"])
        self.assertEqual("seed", sources[0]["discovery_status"])
        self.assertEqual("", sources[0]["source_url"])

    def test_collect_creates_pending_draft_with_hash(self) -> None:
        page = b"""
        <html>
          <head>
            <title>Proposta</title>
            <meta property="og:site_name" content="Portal oficial">
            <meta property="article:published_time" content="2026-08-15T12:00:00-03:00">
          </head>
          <body>
            <p>Maria Silva apresentou uma proposta para ampliar unidades de saude.</p>
          </body>
        </html>
        """
        source = {
            "candidate_id": "123",
            "source_kind": "official_candidate",
            "discovery_status": "exact_content",
            "source_url": "https://example.org/noticias/proposta-1",
            "source_publisher": "Portal oficial",
        }

        def fake_fetch(url: str, **kwargs):
            return page, url, "text/html; charset=utf-8"

        draft = collector.collect_source(
            source,
            candidates=self.candidates,
            fetcher=fake_fetch,
        )
        self.assertEqual("pending", draft["review_status"])
        self.assertEqual("2026-08-15", draft["published_at"])
        self.assertTrue(draft["candidate_mentioned"])
        self.assertEqual(64, len(draft["content_sha256"]))
        self.assertIn("Maria Silva", draft["raw_excerpt"])

    @unittest.skipUnless(PYPDF_AVAILABLE, "pypdf não instalado")
    def test_collect_pdf_creates_pending_draft(self) -> None:
        source = {
            "candidate_id": "123",
            "source_kind": "institutional",
            "discovery_status": "exact_content",
            "source_url": "https://example.org/documentos/projeto-85-2025.pdf",
            "source_title": "Projeto de Lei",
            "source_publisher": "Assembleia Legislativa",
            "published_at": "2025-02-20",
        }

        def fake_fetch(url: str, **kwargs):
            return MINIMAL_TEXT_PDF, url, "application/pdf"

        draft = collector.collect_source(
            source,
            candidates=self.candidates,
            fetcher=fake_fetch,
        )

        self.assertEqual("pending", draft["review_status"])
        self.assertEqual("pdf", draft["document_type"])
        self.assertEqual(1, draft["page_count"])
        self.assertTrue(draft["candidate_mentioned"])
        self.assertEqual(64, len(draft["source_sha256"]))
        self.assertEqual(64, len(draft["content_sha256"]))
        self.assertIn("Maria Silva", draft["raw_excerpt"])

    @unittest.skipUnless(PYPDF_AVAILABLE, "pypdf não instalado")
    def test_pdf_without_text_is_rejected_without_ocr(self) -> None:
        from pypdf import PdfWriter

        buffer = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.write(buffer)

        source = {
            "candidate_id": "123",
            "source_kind": "institutional",
            "discovery_status": "exact_content",
            "source_url": "https://example.org/documentos/scan.pdf",
            "source_title": "Documento",
            "source_publisher": "Assembleia Legislativa",
        }

        def fake_fetch(url: str, **kwargs):
            return buffer.getvalue(), url, "application/pdf"

        with self.assertRaisesRegex(RuntimeError, "OCR não é executado"):
            collector.collect_source(
                source,
                candidates=self.candidates,
                fetcher=fake_fetch,
            )

    def test_approved_review_can_be_promoted(self) -> None:
        draft = {
            "draft_id": "abc",
            "candidate_id": "123",
            "source_kind": "official_candidate",
            "source_url": "https://example.org/noticias/proposta-1",
            "source_title": "Proposta",
            "source_publisher": "Portal oficial",
            "published_at": "2026-08-15",
            "captured_at": "2026-09-19T20:00:00+00:00",
            "content_sha256": "a" * 64,
            "raw_excerpt": "Maria Silva apresentou uma proposta para ampliar unidades de saude.",
            "review_status": "pending",
        }
        review = {
            "draft_id": "abc",
            "status": "approved",
            "attempts": 1,
            "topic_id": "saude",
            "evidence_type": "proposta",
            "statement": "Proposta de ampliar unidades de saúde.",
            "quote_or_summary": "Apresentou proposta para ampliar unidades de saúde.",
            "scope": "estadual",
            "verification_status": "verified",
            "support_text": "Maria Silva apresentou uma proposta para ampliar unidades de saude.",
            "attribution_basis": "A página identifica nominalmente a candidata.",
            "reviewed_at": "2026-09-19T20:00:00+00:00",
            "reviewer": "teste",
        }
        canonical = {
            "version": "1.0.0",
            "updated_at": "2026-09-19",
            "semantics": "teste",
            "entries": [],
        }

        result, stats = collector.promote_reviews(
            drafts_payload={"drafts": [draft]},
            reviews_payload={"reviews": [review]},
            canonical_payload=canonical,
            candidates=self.candidates,
            topic_ids={"saude"},
        )

        self.assertEqual(1, stats["promoted"])
        self.assertEqual("123", result["entries"][0]["candidate_id"])
        self.assertEqual("saude", result["entries"][0]["topic_id"])
        self.assertNotIn("support_text", result["entries"][0])

    def test_review_fails_when_support_is_not_in_raw_excerpt(self) -> None:
        draft = {
            "draft_id": "abc",
            "candidate_id": "123",
            "source_kind": "official_candidate",
            "source_url": "https://example.org/noticias/proposta-1",
            "source_title": "Proposta",
            "source_publisher": "Portal oficial",
            "captured_at": "2026-09-19T20:00:00+00:00",
            "content_sha256": "a" * 64,
            "raw_excerpt": "Trecho diferente.",
        }
        review = collector.parse_review(
            {
                "draft_id": "abc",
                "status": "approved",
                "attempts": 1,
                "topic_id": "saude",
                "evidence_type": "proposta",
                "statement": "Resumo.",
                "scope": "estadual",
                "verification_status": "verified",
                "support_text": "Texto inexistente.",
                "attribution_basis": "Fonte identifica a candidatura.",
                "reviewed_at": "2026-09-19T20:00:00+00:00",
                "reviewer": "teste",
            }
        )
        with self.assertRaisesRegex(RuntimeError, "support_text"):
            collector.validate_review_for_promotion(
                review,
                draft,
                candidate_ids={"123"},
                topic_ids={"saude"},
            )


if __name__ == "__main__":
    unittest.main()
