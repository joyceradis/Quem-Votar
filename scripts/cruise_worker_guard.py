#!/usr/bin/env python3
"""Cruise-mode health gate and batching report for #35.

This script is intentionally non-editorial. It never approves, promotes, or
classifies political evidence. It only checks operational provenance invariants
and reports the accumulated non-canonical backlog.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean(value: Any) -> str:
    return str(value or "").strip()


def is_chamber_source(row: dict[str, Any]) -> bool:
    origin = row.get("source_origin") or {}
    publisher = clean(row.get("source_publisher")).casefold()
    institution = clean(origin.get("institution")).casefold()
    url = clean(row.get("source_url")).casefold()
    return (
        publisher == "câmara dos deputados".casefold()
        or institution == "câmara dos deputados".casefold()
        or "camara.leg.br/" in url
    )


def proposition_id_from_url(url: str) -> str:
    match = re.search(r"[?&]idProposicao=(\d+)", url)
    return match.group(1) if match else ""


def load_candidate_chamber_ids(
    federal_path: Path,
    estadual_path: Path,
) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in (federal_path, estadual_path):
        rows = read_json(path)
        if not isinstance(rows, list):
            raise RuntimeError(f"{path} deve conter lista")
        for row in rows:
            cid = clean(row.get("tse_id"))
            mandate = row.get("current_mandate") or {}
            chamber_id = clean(mandate.get("chamber_id"))
            if cid and chamber_id:
                result[cid] = chamber_id
    return result


def build_report(
    *,
    sources_payload: dict[str, Any],
    failures_payload: dict[str, Any],
    drafts_payload: dict[str, Any],
    canonical_payload: dict[str, Any],
    candidate_chamber_ids: dict[str, str],
) -> dict[str, Any]:
    sources = sources_payload.get("sources") or []
    failures = failures_payload.get("failures") or []
    drafts = drafts_payload.get("drafts") or []
    canonical_entries = canonical_payload.get("entries") or []

    current_chamber_urls = {
        clean(row.get("source_url"))
        for row in sources
        if is_chamber_source(row)
        and clean(row.get("discovery_status")) == "exact_content"
        and clean(row.get("source_url"))
    }

    incidents: list[dict[str, Any]] = []

    for failure in failures:
        url = clean(failure.get("source_url"))
        if url and url in current_chamber_urls:
            incidents.append(
                {
                    "type": "institutional_reacquisition_failure",
                    "candidate_id": clean(failure.get("candidate_id")),
                    "source_url": url,
                    "source_id": clean(failure.get("source_id")),
                    "detail": clean(failure.get("error")),
                }
            )

    for draft in drafts:
        if not is_chamber_source(draft):
            continue
        if clean(draft.get("attribution_trust")) != "official_author_api":
            continue

        origin = draft.get("source_origin") or {}
        cid = clean(draft.get("candidate_id"))
        chamber_id = clean(origin.get("chamber_id"))
        proposition_id = clean(origin.get("proposition_id"))
        source_url = clean(draft.get("source_url"))
        url_prop_id = proposition_id_from_url(source_url)
        expected_chamber_id = candidate_chamber_ids.get(cid, "")

        problems: list[str] = []
        if not cid:
            problems.append("missing_candidate_id")
        if not chamber_id:
            problems.append("missing_chamber_id")
        if not proposition_id:
            problems.append("missing_proposition_id")
        if source_url and url_prop_id and proposition_id and url_prop_id != proposition_id:
            problems.append("proposition_id_url_mismatch")
        if expected_chamber_id and chamber_id and expected_chamber_id != chamber_id:
            problems.append("candidate_chamber_id_mismatch")

        if problems:
            incidents.append(
                {
                    "type": "institutional_anchor_integrity_failure",
                    "candidate_id": cid,
                    "source_url": source_url,
                    "draft_id": clean(draft.get("draft_id")),
                    "problems": problems,
                }
            )

    canonical_urls = {
        clean(row.get("source_url"))
        for row in canonical_entries
        if clean(row.get("source_url"))
    }
    draft_urls = {
        clean(row.get("source_url"))
        for row in drafts
        if clean(row.get("source_url"))
    }

    backlog_urls = sorted(url for url in draft_urls if url not in canonical_urls)

    return {
        "version": "1.0.0",
        "mode": "cruise",
        "semantics": (
            "Operational health and batching report only. No political evidence "
            "is approved, promoted, ranked, or reclassified by this report."
        ),
        "alert_policy": {
            "silent_on_success": True,
            "actionable_incidents": [
                "institutional_reacquisition_failure",
                "institutional_anchor_integrity_failure",
            ],
        },
        "batching": {
            "auto_pr": False,
            "promotion_policy": "logical_checkpoint_or_explicit_maintainer_trigger",
            "accumulated_noncanonical_draft_urls": len(backlog_urls),
            "sample_backlog_urls": backlog_urls[:25],
        },
        "metrics": {
            "current_exact_sources": sum(
                1 for row in sources
                if clean(row.get("discovery_status")) == "exact_content"
            ),
            "current_chamber_exact_sources": len(current_chamber_urls),
            "drafts_total": len(drafts),
            "canonical_entries": len(canonical_entries),
            "actionable_incidents": len(incidents),
        },
        "incidents": incidents,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--failures", type=Path, required=True)
    parser.add_argument("--drafts", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--federal", type=Path, required=True)
    parser.add_argument("--estadual", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        sources_payload=read_json(args.sources),
        failures_payload=read_json(args.failures),
        drafts_payload=read_json(args.drafts),
        canonical_payload=read_json(args.canonical),
        candidate_chamber_ids=load_candidate_chamber_ids(
            args.federal,
            args.estadual,
        ),
    )
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
