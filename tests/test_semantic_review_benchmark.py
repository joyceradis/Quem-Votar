#!/usr/bin/env python3
"""Tests for scripts/semantic_review_benchmark.py (issue #42 shadow benchmark)."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE = SCRIPTS / "semantic_review_benchmark.py"
SPEC = importlib.util.spec_from_file_location("semantic_review_benchmark", MODULE)
bench = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bench)

CANONICAL_TOPIC_EVIDENCE = ROOT / "data" / "reference" / "topic-evidence.json"


def policy_topics_doc():
    return {
        "version": "1.1.0",
        "semantics": "test",
        "topics": [
            {
                "id": "saude",
                "label": "Saúde",
                "description": "Acesso a hospitais, postos e medicamentos.",
                "life_areas": ["fila de atendimento", "posto de saude"],
                "practical_question": "Isso muda uma fila de hospital?",
            },
            {
                "id": "educacao",
                "label": "Educação",
                "description": "Escolas, creches e universidades publicas.",
                "life_areas": ["vaga em creche", "merenda escolar"],
                "practical_question": "Isso muda uma vaga em escola?",
            },
        ],
    }


def make_fixture(
    fixture_id,
    text,
    source_title="",
    source_kind="institutional",
    topic_id="saude",
    evidence_type="proposta",
    decision="approve",
    excluded=False,
    decision_none=False,
):
    return {
        "fixture_id": fixture_id,
        "candidate_id": "cand-1",
        "input": {
            "text": text,
            "source_title": source_title,
            "source_publisher": "Câmara dos Deputados",
            "source_kind": source_kind,
            "document_type": None,
            "scope": "federal",
            "published_at": "2025-01-01",
        },
        "ground_truth": {
            "decision": None if decision_none else decision,
            "topic_id": topic_id,
            "evidence_type": evidence_type,
            "verification_status": "verified",
        },
        "provenance": {"origin_file": "test", "origin_note": "synthetic"},
        "heterogeneity_tags": [],
        "excluded_from_decision_scoring": excluded,
    }


class TopicClassifierTests(unittest.TestCase):
    def test_topic_vocab_derived_only_from_policy_topics_fields(self):
        vocab = bench.load_topic_vocab(policy_topics_doc())
        self.assertIn("saude", vocab)
        self.assertIn("educacao", vocab)
        self.assertIn("hospitais", vocab["saude"])
        self.assertIn("creches", vocab["educacao"])

    def test_classify_topic_picks_best_overlap(self):
        vocab = bench.load_topic_vocab(policy_topics_doc())
        topic_id, confidence, score = bench.classify_topic(
            "Novo posto de saude vai atender fila de atendimento", vocab
        )
        self.assertEqual(topic_id, "saude")
        self.assertGreater(score, 0)

    def test_classify_topic_returns_none_on_no_overlap(self):
        vocab = bench.load_topic_vocab(policy_topics_doc())
        topic_id, confidence, score = bench.classify_topic("xyz abc qwerty", vocab)
        self.assertIsNone(topic_id)
        self.assertEqual(score, 0)


class EvidenceTypeClassifierTests(unittest.TestCase):
    def test_document_code_prefix_takes_priority(self):
        result = bench.evidence_type_from_document_code("PL 3193/2025")
        self.assertEqual(result, "proposta")

    def test_document_code_procedural_prefix(self):
        result = bench.evidence_type_from_document_code("REQ 1/2026")
        self.assertEqual(result, "atuação")

    def test_document_code_absent_returns_none(self):
        self.assertIsNone(bench.evidence_type_from_document_code("Noticia sobre o deputado"))

    def test_classify_evidence_type_uses_document_code_when_present(self):
        etype, confidence, basis = bench.classify_evidence_type("PEC 10/2025", "qualquer texto")
        self.assertEqual(etype, "proposta")
        self.assertEqual(basis, "document_code")
        self.assertEqual(confidence, 1.0)

    def test_classify_evidence_type_falls_back_to_lexical_cues(self):
        etype, confidence, basis = bench.classify_evidence_type(
            "Deputado fala a jornal", "O deputado afirmou que “apoia” a causa"
        )
        self.assertEqual(basis, "lexical_cue")
        self.assertEqual(etype, "declaração")

    def test_classify_evidence_type_unsupported_when_no_cues(self):
        etype, confidence, basis = bench.classify_evidence_type("Titulo generico", "texto neutro")
        self.assertIsNone(etype)
        self.assertEqual(basis, "unsupported")


class DecisionRoutingTests(unittest.TestCase):
    def test_non_institutional_source_routes_to_exception_review(self):
        decision, reason = bench.classify_decision("secondary", "saude", 2, "proposta", "document_code")
        self.assertEqual(decision, "exception_review")
        self.assertEqual(reason, "ambiguous_attribution")

    def test_unsupported_topic_routes_to_exception_review(self):
        decision, reason = bench.classify_decision("institutional", None, 0, "proposta", "document_code")
        self.assertEqual(decision, "exception_review")
        self.assertEqual(reason, "unsupported_topic")

    def test_unsupported_evidence_type_routes_to_exception_review(self):
        decision, reason = bench.classify_decision("institutional", "saude", 2, None, "unsupported")
        self.assertEqual(decision, "exception_review")
        self.assertEqual(reason, "evidence_type_ambiguity")

    def test_full_support_approves(self):
        decision, reason = bench.classify_decision("institutional", "saude", 2, "proposta", "document_code")
        self.assertEqual(decision, "approve")
        self.assertIsNone(reason)


class RunBenchmarkSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.topics = policy_topics_doc()

    def test_full_agreement_case(self):
        fixture = make_fixture(
            "syn-agree",
            text="Novo posto de saude para reduzir a fila de atendimento",
            source_title="PL 100/2025",
            topic_id="saude",
            evidence_type="proposta",
            decision="approve",
        )
        report = bench.run_benchmark({"fixtures": [fixture]}, self.topics)
        result = report["results"][0]
        self.assertIn("full_agreement", result["categories"])
        self.assertEqual(report["metrics"]["agreement_with_reviewed_examples"], 1.0)

    def test_unsupported_topic_case(self):
        fixture = make_fixture(
            "syn-unsupported-topic",
            text="xyz abc qwerty zzz",
            source_title="PL 100/2025",
            topic_id="saude",
            evidence_type="proposta",
            decision="approve",
        )
        report = bench.run_benchmark({"fixtures": [fixture]}, self.topics)
        result = report["results"][0]
        self.assertIn("unsupported_topic", result["categories"])
        self.assertEqual(report["metrics"]["unsupported_topic_assignment"]["count"], 1)

    def test_unsupported_evidence_type_case(self):
        fixture = make_fixture(
            "syn-unsupported-evidence",
            text="posto de saude e fila de atendimento sem pistas de tipo",
            source_title="Titulo generico sem codigo",
            topic_id="saude",
            evidence_type="proposta",
            decision="approve",
        )
        report = bench.run_benchmark({"fixtures": [fixture]}, self.topics)
        result = report["results"][0]
        self.assertIn("unsupported_evidence_type", result["categories"])
        self.assertEqual(report["metrics"]["unsupported_evidence_type_assignment"]["count"], 1)

    def test_false_approval_case(self):
        # Prediction will approve (institutional, clean topic+evidence match via
        # document code) but ground truth says exception_review -> false_approval.
        fixture = make_fixture(
            "syn-false-approval",
            text="Novo posto de saude para reduzir a fila de atendimento",
            source_title="PL 100/2025",
            topic_id="saude",
            evidence_type="proposta",
            decision="exception_review",
        )
        report = bench.run_benchmark({"fixtures": [fixture]}, self.topics)
        result = report["results"][0]
        self.assertIn("false_approval", result["categories"])
        self.assertEqual(report["metrics"]["false_approvals"]["count"], 1)

    def test_correctly_routed_to_exception_review_case(self):
        fixture = make_fixture(
            "syn-correctly-routed",
            text="xyz abc qwerty zzz",
            source_title="Titulo sem codigo",
            topic_id="saude",
            evidence_type="proposta",
            decision_none=True,
        )
        report = bench.run_benchmark({"fixtures": [fixture]}, self.topics)
        result = report["results"][0]
        self.assertIn("correctly_routed_to_exception_review", result["categories"])
        self.assertEqual(
            report["metrics"]["cases_correctly_routed_to_exception_review"]["count"], 1
        )
        self.assertFalse(result["decision_scored"])

    def test_every_result_is_categorized(self):
        fixtures = [
            make_fixture("f1", "posto de saude fila", "PL 1/2025", topic_id="saude", evidence_type="proposta"),
            make_fixture("f2", "xyz abc qwerty", "PL 2/2025", topic_id="saude", evidence_type="proposta"),
            make_fixture("f3", "texto neutro", "sem codigo", topic_id="saude", evidence_type="proposta"),
        ]
        report = bench.run_benchmark({"fixtures": fixtures}, self.topics)
        for result in report["results"]:
            self.assertTrue(result["categories"])

    def test_run_benchmark_is_repeatable(self):
        fixtures = [
            make_fixture("f1", "posto de saude fila", "PL 1/2025", topic_id="saude", evidence_type="proposta"),
            make_fixture("f2", "vaga em creche merenda escolar", "REQ 2/2025", topic_id="educacao", evidence_type="atuação"),
        ]
        doc = {"fixtures": fixtures}
        first = bench.run_benchmark(doc, self.topics)
        second = bench.run_benchmark(doc, self.topics)
        self.assertEqual(first, second)


class RealFixtureFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures_doc = bench.load_json(bench.DEFAULT_FIXTURES)
        cls.policy_topics_doc = bench.load_json(bench.DEFAULT_POLICY_TOPICS)

    def test_fixture_file_schema(self):
        self.assertEqual(self.fixtures_doc["authorization_issue"], 42)
        self.assertEqual(len(self.fixtures_doc["fixtures"]), 23)

    def test_policy_topics_schema(self):
        self.assertEqual(len(self.policy_topics_doc["topics"]), 7)

    def test_run_benchmark_against_real_fixtures_is_repeatable(self):
        first = bench.run_benchmark(self.fixtures_doc, self.policy_topics_doc)
        second = bench.run_benchmark(self.fixtures_doc, self.policy_topics_doc)
        self.assertEqual(first, second)

    def test_every_real_result_is_categorized(self):
        report = bench.run_benchmark(self.fixtures_doc, self.policy_topics_doc)
        for result in report["results"]:
            self.assertTrue(result["categories"], msg=f"{result['fixture_id']} has no category")

    def test_staging_001_excluded_from_decision_scoring_but_topic_and_evidence_scored(self):
        report = bench.run_benchmark(self.fixtures_doc, self.policy_topics_doc)
        staging = next(r for r in report["results"] if r["fixture_id"] == "staging-001")
        self.assertTrue(staging["excluded_from_decision_scoring"])
        self.assertFalse(staging["decision_scored"])
        self.assertIsNone(staging["decision_match"])
        # topic_id/evidence_type ground truth is still present and comparable
        self.assertEqual(staging["ground_truth"]["topic_id"], "infraestrutura")
        self.assertEqual(staging["ground_truth"]["evidence_type"], "atuação")
        self.assertIn(staging["topic_match"], (True, False))
        self.assertIn(staging["evidence_match"], (True, False))

    def test_metrics_are_internally_consistent(self):
        report = bench.run_benchmark(self.fixtures_doc, self.policy_topics_doc)
        metrics = report["metrics"]
        self.assertEqual(metrics["fixture_count"], 23)
        self.assertEqual(metrics["decision_scored_count"], 22)
        self.assertGreaterEqual(metrics["false_approvals"]["count"], 0)
        self.assertLessEqual(
            metrics["false_approvals"]["count"], metrics["decision_scored_count"]
        )


class FreezeRuleTests(unittest.TestCase):
    def test_module_never_imports_canonical_write_paths(self):
        source = MODULE.read_text(encoding="utf-8")
        # The module docstring is allowed to *mention* topic-evidence.json
        # while explaining the freeze rule; the executable code below the
        # docstring must never reference it, and must never import the
        # canonical-write modules.
        _, _, code_after_docstring = source.split('"""', 2)
        self.assertNotIn("topic-evidence.json", code_after_docstring)
        self.assertNotIn("sync-data", code_after_docstring)
        self.assertNotIn("process_evidence_batch", code_after_docstring)

    def test_default_report_path_is_staging_not_reference(self):
        self.assertIn("staging", str(bench.DEFAULT_REPORT))
        self.assertNotIn("reference", str(bench.DEFAULT_REPORT))

    def test_running_main_does_not_modify_canonical_topic_evidence(self):
        before = hashlib.sha256(CANONICAL_TOPIC_EVIDENCE.read_bytes()).hexdigest()
        exit_code = bench.main(["--dry-run"])
        after = hashlib.sha256(CANONICAL_TOPIC_EVIDENCE.read_bytes()).hexdigest()
        self.assertEqual(exit_code, 0)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
