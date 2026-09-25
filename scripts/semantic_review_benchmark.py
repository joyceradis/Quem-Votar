#!/usr/bin/env python3
"""Shadow-mode benchmark for automated semantic review (issue #42).

Measures whether a deterministic, transparent baseline classifier agrees
with already-reviewed evidence, without touching canonical publication.

Freeze rule (docs/GOVERNANCE.md:261 and issue #42 "Freeze rule"): shadow
output cannot independently write canonical evidence or change public
semantics. This module enforces that structurally, not by convention:
it only reads data/staging/semantic-review-benchmark-fixtures.json and
data/reference/policy-topics.json, and writes only to
data/staging/semantic-review-benchmark-report.json (staging, non-canonical).
It never imports scripts/sync-data.py, scripts/process_evidence_batch.py,
or any path that can write data/reference/topic-evidence.json.

Baseline classifier design notes:
- Topic vocabulary is derived mechanically and exclusively from
  data/reference/policy-topics.json (label + description + life_areas).
  It is intentionally not hand-expanded with curated keywords, so that no
  knowledge of the specific benchmark fixtures leaks into the baseline.
  A low topic-agreement rate is an expected, honest finding, not a bug.
- Evidence-type classification first checks the official Câmara dos
  Deputados document-type code in the source title (PL/PEC/PLP are
  proposals; REQ/RPD/RIC/PRL are procedural acts already taken). That is
  general legislative-taxonomy knowledge, not fixture-specific tuning.
  When no such code is present (e.g. a secondary/journalistic source),
  it falls back to lexical cue counting, which is deliberately left
  unable to resolve the atuação/proposta/declaração boundary case
  documented in fixture staging-001 — the benchmark is designed to
  surface that failure mode, not hide it.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "data" / "staging" / "semantic-review-benchmark-fixtures.json"
DEFAULT_POLICY_TOPICS = ROOT / "data" / "reference" / "policy-topics.json"
DEFAULT_REPORT = ROOT / "data" / "staging" / "semantic-review-benchmark-report.json"

WORD_RE = re.compile(r"[a-z]+")
STOPWORDS = {
    "a", "o", "os", "as", "de", "da", "do", "das", "dos", "em", "um", "uma",
    "uns", "umas", "para", "por", "com", "que", "na", "no", "nas", "nos",
    "e", "ou", "ao", "aos", "sobre", "the", "of", "se", "sua", "seu",
    "suas", "seus", "ou", "ja", "ate", "sem", "mais", "menos",
}

CODE_RE = re.compile(r"^([A-Z]{2,4})\s?\d")
DOCUMENT_CODE_EVIDENCE_TYPE = {
    "PL": "proposta",
    "PLP": "proposta",
    "PEC": "proposta",
    "PDL": "proposta",
    "REQ": "atuação",
    "RPD": "atuação",
    "RIC": "atuação",
    "PRL": "atuação",
}

EVIDENCE_TYPE_PRIORITY = ["atuação", "proposta", "declaração"]
EVIDENCE_TYPE_CUES = {
    "atuação": [
        "requerimento", "requer ", "parecer do relator", "parecer ",
        "relator", "votacao nominal", "votacao", "aprovou", "apresentou",
        "audiencia publica", "visita tecnica", "retirada de pauta",
        "retirada da pauta", "comissao de",
    ],
    "proposta": [
        "propoe", "institui a", "institui o", "institui ", "dispoe sobre",
        "altera a lei", "cria o fundo", "regulamentar", "obrigatoriedade de",
    ],
    "declaração": [
        "afirmou", "declarou", "disse que", "segundo o deputado",
        "segundo a deputada", "“", "”",
    ],
}


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def tokenize(text: str) -> list[str]:
    folded = strip_accents(text).casefold()
    words = WORD_RE.findall(folded)
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_topic_vocab(policy_topics_doc: dict) -> dict[str, set[str]]:
    vocab: dict[str, set[str]] = {}
    for topic in policy_topics_doc["topics"]:
        words = set(tokenize(topic["label"]))
        words |= set(tokenize(topic["description"]))
        for area in topic.get("life_areas", []):
            words |= set(tokenize(area))
        vocab[topic["id"]] = words
    return vocab


def classify_topic(text: str, topic_vocab: dict[str, set[str]]) -> tuple[str | None, float, int]:
    tokens = set(tokenize(text))
    if not tokens:
        return None, 0.0, 0
    best_topic = None
    best_score = 0
    for topic_id in sorted(topic_vocab):
        overlap = len(tokens & topic_vocab[topic_id])
        if overlap > best_score:
            best_score = overlap
            best_topic = topic_id
    confidence = best_score / len(tokens)
    return best_topic, confidence, best_score


def evidence_type_from_document_code(source_title: str) -> str | None:
    match = CODE_RE.match((source_title or "").strip())
    if not match:
        return None
    return DOCUMENT_CODE_EVIDENCE_TYPE.get(match.group(1))


def classify_evidence_type(source_title: str, text: str) -> tuple[str | None, float, str]:
    code_result = evidence_type_from_document_code(source_title)
    if code_result:
        return code_result, 1.0, "document_code"

    folded = strip_accents(f"{source_title} {text}").casefold()
    scores = {
        etype: sum(folded.count(strip_accents(cue).casefold()) for cue in cues)
        for etype, cues in EVIDENCE_TYPE_CUES.items()
    }
    best_type = None
    best_score = 0
    for etype in EVIDENCE_TYPE_PRIORITY:
        if scores[etype] > best_score:
            best_type = etype
            best_score = scores[etype]
    if best_type is None:
        return None, 0.0, "unsupported"
    confidence = min(1.0, best_score / 3)
    return best_type, confidence, "lexical_cue"


def classify_decision(
    source_kind: str,
    topic_id: str | None,
    topic_score: int,
    evidence_type: str | None,
    evidence_basis: str,
) -> tuple[str, str | None]:
    if source_kind != "institutional":
        return "exception_review", "ambiguous_attribution"
    if topic_id is None or topic_score < 1:
        return "exception_review", "unsupported_topic"
    if evidence_type is None or evidence_basis == "unsupported":
        return "exception_review", "evidence_type_ambiguity"
    return "approve", None


def classify_fixture(fixture: dict, topic_vocab: dict[str, set[str]]) -> dict:
    input_data = fixture["input"]
    text = input_data.get("text", "")
    source_title = input_data.get("source_title", "")
    source_kind = input_data.get("source_kind", "")

    topic_id, topic_confidence, topic_score = classify_topic(
        f"{source_title} {text}", topic_vocab
    )
    evidence_type, evidence_confidence, evidence_basis = classify_evidence_type(
        source_title, text
    )
    decision, decision_reason = classify_decision(
        source_kind, topic_id, topic_score, evidence_type, evidence_basis
    )

    return {
        "topic_id": topic_id,
        "topic_confidence": round(topic_confidence, 4),
        "topic_score": topic_score,
        "evidence_type": evidence_type,
        "evidence_confidence": round(evidence_confidence, 4),
        "evidence_basis": evidence_basis,
        "decision": decision,
        "decision_reason": decision_reason,
    }


def evaluate_fixture(fixture: dict, prediction: dict) -> dict:
    ground_truth = fixture["ground_truth"]
    excluded = bool(fixture.get("excluded_from_decision_scoring"))
    categories: list[str] = []

    topic_match = prediction["topic_id"] == ground_truth.get("topic_id")
    evidence_match = prediction["evidence_type"] == ground_truth.get("evidence_type")

    if not topic_match:
        categories.append("topic_mismatch")
    if prediction["topic_id"] is None:
        categories.append("unsupported_topic")
    if not evidence_match:
        categories.append("evidence_type_mismatch")
        categories.append("attribution_error")
    if prediction["evidence_type"] is None:
        categories.append("unsupported_evidence_type")

    decision_match = None
    decision_scored = not excluded and ground_truth.get("decision") is not None
    if decision_scored:
        decision_match = prediction["decision"] == ground_truth["decision"]
        if not decision_match:
            categories.append("decision_mismatch")
            if prediction["decision"] == "approve" and ground_truth["decision"] != "approve":
                categories.append("false_approval")
    elif prediction["decision"] == "exception_review":
        categories.append("correctly_routed_to_exception_review")

    if not categories:
        categories.append("full_agreement")

    return {
        "topic_match": topic_match,
        "evidence_match": evidence_match,
        "decision_match": decision_match,
        "decision_scored": decision_scored,
        "categories": categories,
    }


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def run_benchmark(fixtures_doc: dict, policy_topics_doc: dict) -> dict:
    topic_vocab = load_topic_vocab(policy_topics_doc)
    fixtures = fixtures_doc["fixtures"]

    results = []
    for fixture in fixtures:
        prediction = classify_fixture(fixture, topic_vocab)
        evaluation = evaluate_fixture(fixture, prediction)
        results.append(
            {
                "fixture_id": fixture["fixture_id"],
                "candidate_id": fixture.get("candidate_id"),
                "heterogeneity_tags": fixture.get("heterogeneity_tags", []),
                "prediction": prediction,
                "ground_truth": fixture["ground_truth"],
                "excluded_from_decision_scoring": bool(
                    fixture.get("excluded_from_decision_scoring")
                ),
                **evaluation,
            }
        )

    total = len(results)
    decision_scored = [r for r in results if r["decision_scored"]]

    full_agreement = sum(1 for r in results if "full_agreement" in r["categories"])
    unsupported_topic = sum(1 for r in results if "unsupported_topic" in r["categories"])
    unsupported_evidence_type = sum(
        1 for r in results if "unsupported_evidence_type" in r["categories"]
    )
    attribution_errors = sum(1 for r in results if "attribution_error" in r["categories"])
    false_approvals = sum(1 for r in results if "false_approval" in r["categories"])
    correctly_routed = sum(
        1 for r in results if "correctly_routed_to_exception_review" in r["categories"]
    )
    decision_agreements = sum(1 for r in decision_scored if r["decision_match"])

    metrics = {
        "fixture_count": total,
        "decision_scored_count": len(decision_scored),
        "agreement_with_reviewed_examples": rate(full_agreement, total),
        "disagreement_rate": rate(total - full_agreement, total),
        "unsupported_topic_assignment": {
            "count": unsupported_topic,
            "rate": rate(unsupported_topic, total),
        },
        "unsupported_evidence_type_assignment": {
            "count": unsupported_evidence_type,
            "rate": rate(unsupported_evidence_type, total),
        },
        "attribution_errors": {
            "count": attribution_errors,
            "rate": rate(attribution_errors, total),
        },
        "false_approvals": {
            "count": false_approvals,
            "rate": rate(false_approvals, len(decision_scored)),
        },
        "cases_correctly_routed_to_exception_review": {"count": correctly_routed},
        "decision_agreement_rate": rate(decision_agreements, len(decision_scored)),
    }

    return {"metrics": metrics, "results": results}


def build_report(fixtures_doc: dict, policy_topics_doc: dict) -> dict:
    benchmark = run_benchmark(fixtures_doc, policy_topics_doc)
    return {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "authorization_issue": 42,
        "freeze_rule": (
            "Shadow output only. This report does not write canonical "
            "evidence and does not change public semantics. See "
            "docs/GOVERNANCE.md:261 and issue #42."
        ),
        "fixture_file": str(DEFAULT_FIXTURES.relative_to(ROOT)),
        "policy_topics_file": str(DEFAULT_POLICY_TOPICS.relative_to(ROOT)),
        "coverage_gaps": fixtures_doc.get("coverage_gaps", []),
        "metrics": benchmark["metrics"],
        "results": benchmark["results"],
    }


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    parser.add_argument("--policy-topics", default=str(DEFAULT_POLICY_TOPICS))
    parser.add_argument("--output", default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute metrics without writing the staging report file.",
    )
    args = parser.parse_args(argv)

    fixtures_doc = load_json(Path(args.fixtures))
    policy_topics_doc = load_json(Path(args.policy_topics))
    report = build_report(fixtures_doc, policy_topics_doc)

    if not args.dry_run:
        write_report(report, Path(args.output))

    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
