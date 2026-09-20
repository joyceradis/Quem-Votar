#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEDERAL = ROOT / "data/generated/candidates-federal.json"
DEFAULT_ESTADUAL = ROOT / "data/generated/candidates-estadual.json"
DEFAULT_SOURCES = ROOT / "data/staging/topic-evidence-sources.json"
DEFAULT_DRAFTS = ROOT / "data/staging/topic-evidence-drafts.json"
DEFAULT_REVIEWS = ROOT / "data/staging/topic-evidence-reviews.json"
DEFAULT_CANONICAL = ROOT / "data/reference/topic-evidence.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def candidate_rows(*paths: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        payload = read_json(path)
        if not isinstance(payload, list):
            raise RuntimeError(f"{path} must contain a JSON list")
        rows.extend(payload)
    ids = [clean(row.get("tse_id")) for row in rows]
    if not all(ids) or len(ids) != len(set(ids)):
        raise RuntimeError("candidate universe has missing or duplicate SQ_CANDIDATO")
    return rows


def list_field(path: Path, key: str) -> list[dict[str, Any]]:
    payload = read_json(path)
    items = payload.get(key, [])
    if not isinstance(items, list):
        raise RuntimeError(f"{path}: {key} must be a list")
    return items


SOCIAL_SUFFIXES = {
    "instagram.com", "facebook.com", "threads.net", "threads.com", "x.com",
    "twitter.com", "youtube.com", "youtu.be", "tiktok.com", "linkedin.com",
    "whatsapp.com",
}


def host_of(url: str) -> str:
    from urllib.parse import urlsplit
    try:
        return (urlsplit(clean(url)).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def is_social_seed(url: str) -> bool:
    host = host_of(url)
    return any(host == suffix or host.endswith("." + suffix) for suffix in SOCIAL_SUFFIXES)


def state_for(counts: Counter[str]) -> str:
    if counts["canonical"]:
        return "canonical_published"
    if counts["review_approved"]:
        return "approved_not_canonical"
    if counts["review_quarantine"]:
        return "quarantine"
    if counts["review_pending"]:
        return "review_pending"
    if counts["review_rejected"]:
        return "rejected"
    if counts["drafts"]:
        return "draft_collected"
    if counts["exact_sources"]:
        return "exact_source_found"
    if counts["seeds"]:
        return "discovery_only"
    return "not_started"


def build_report(
    candidates: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    drafts: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    canonical: list[dict[str, Any]],
    *,
    discovery_checked_at: str = "",
    processing_state: dict[str, Any] | None = None,
    exception_queue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    by_candidate: dict[str, Counter[str]] = defaultdict(Counter)
    draft_to_candidate: dict[str, str] = {}
    processing_by_candidate: dict[str, Counter[str]] = defaultdict(Counter)
    exceptions_by_candidate: dict[str, Counter[str]] = defaultdict(Counter)
    seed_urls_by_candidate: dict[str, list[str]] = defaultdict(list)

    for source in sources:
        cid = clean(source.get("candidate_id"))
        if source.get("discovery_status") == "seed":
            by_candidate[cid]["seeds"] += 1
            seed_urls_by_candidate[cid].append(clean(source.get("seed_url")))
        elif source.get("discovery_status") == "exact_content":
            by_candidate[cid]["exact_sources"] += 1

    for draft in drafts:
        cid = clean(draft.get("candidate_id"))
        by_candidate[cid]["drafts"] += 1
        did = clean(draft.get("draft_id"))
        if did:
            draft_to_candidate[did] = cid

    for review in reviews:
        cid = clean(review.get("candidate_id")) or draft_to_candidate.get(clean(review.get("draft_id")), "")
        status = clean(review.get("status"))
        if cid and status in {"pending", "approved", "quarantine", "rejected"}:
            by_candidate[cid][f"review_{status}"] += 1

    for entry in canonical:
        cid = clean(entry.get("candidate_id"))
        by_candidate[cid]["canonical"] += 1

    if processing_state:
        states = processing_state.get("sources", {})
        if not isinstance(states, dict):
            raise RuntimeError("processing_state.sources must be an object")
        for row in states.values():
            cid = clean(row.get("candidate_id"))
            status = clean(row.get("status"))
            if cid and status:
                processing_by_candidate[cid][status] += 1

    if exception_queue:
        exceptions = exception_queue.get("exceptions", [])
        if not isinstance(exceptions, list):
            raise RuntimeError("exception_queue.exceptions must be a list")
        for row in exceptions:
            if clean(row.get("status")) != "open":
                continue
            cid = clean(row.get("candidate_id"))
            qclass = clean(row.get("queue_class"))
            if cid and qclass:
                exceptions_by_candidate[cid][qclass] += 1

    ledger = []
    state_counts: Counter[str] = Counter()
    known_ids = {clean(x.get("tse_id")) for x in candidates}

    orphan_ids = sorted(cid for cid in by_candidate if cid and cid not in known_ids)
    if orphan_ids:
        raise RuntimeError(f"pipeline contains unknown candidate ids: {orphan_ids[:10]}")

    for candidate in sorted(candidates, key=lambda x: (clean(x.get("office")), clean(x.get("ballot_name")))):
        cid = clean(candidate.get("tse_id"))
        counts = by_candidate[cid]
        state = state_for(counts)
        state_counts[state] += 1
        checked_routes: list[str] = []
        if discovery_checked_at:
            checked_routes.append("tse_declared_channels")
            if any(url and not is_social_seed(url) for url in seed_urls_by_candidate[cid]):
                checked_routes.append("declared_official_site_links")
            if (candidate.get("current_mandate") or {}).get("chamber_id"):
                checked_routes.append("camara_propositions_by_official_id")

        if counts["exact_sources"]:
            discovery_outcome = "exact_content_found"
        elif counts["seeds"]:
            discovery_outcome = "no_exact_content_found_in_checked_sources"
        elif discovery_checked_at:
            discovery_outcome = "no_seed_or_exact_content_found_in_checked_sources"
        else:
            discovery_outcome = "not_checked"

        ledger.append(
            {
                "candidate_id": cid,
                "candidate_name": clean(candidate.get("ballot_name") or candidate.get("full_name")),
                "office": clean(candidate.get("office")),
                "party": clean(candidate.get("party")),
                "state": state,
                "discovery": {
                    "checked_at": discovery_checked_at,
                    "sources_checked": checked_routes,
                    "outcome": discovery_outcome,
                    "scope_note": (
                        "Resultado restrito às rotas listadas; não implica ausência exaustiva "
                        "de propostas, declarações ou atuação."
                    ),
                },
                "seeds": counts["seeds"],
                "exact_sources": counts["exact_sources"],
                "drafts": counts["drafts"],
                "processing_collected": processing_by_candidate[cid]["collected"],
                "processing_failed": processing_by_candidate[cid]["failed"],
                "exceptions_human_review": exceptions_by_candidate[cid]["human_review"],
                "exceptions_retryable": exceptions_by_candidate[cid]["retryable"],
                "exceptions_data_quality": exceptions_by_candidate[cid]["data_quality"],
                "review_pending": counts["review_pending"],
                "review_approved": counts["review_approved"],
                "review_quarantine": counts["review_quarantine"],
                "review_rejected": counts["review_rejected"],
                "canonical": counts["canonical"],
            }
        )

    total = len(candidates)
    candidates_with_seed = sum(1 for x in ledger if x["seeds"] > 0)
    candidates_with_exact = sum(1 for x in ledger if x["exact_sources"] > 0)
    candidates_with_drafts = sum(1 for x in ledger if x["drafts"] > 0)
    candidates_with_any_review = sum(
        1
        for x in ledger
        if x["review_pending"] + x["review_approved"] + x["review_quarantine"] + x["review_rejected"] > 0
    )
    candidates_with_canonical = sum(1 for x in ledger if x["canonical"] > 0)

    return {
        "version": "1.1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "semantics": (
            "Operational coverage only. It does not rank candidates, infer political positions, "
            "or imply exhaustive absence of evidence."
        ),
        "metrics": {
            "candidate_universe": total,
            "candidates_accounted_for": len(ledger),
            "candidates_with_seed": candidates_with_seed,
            "candidates_with_exact_content": candidates_with_exact,
            "candidates_with_draft": candidates_with_drafts,
            "candidates_with_review": candidates_with_any_review,
            "candidates_with_canonical_evidence": candidates_with_canonical,
            "source_records": len(sources),
            "draft_records": len(drafts),
            "review_records": len(reviews),
            "canonical_records": len(canonical),
            "candidates_discovery_checked": sum(1 for x in ledger if x["discovery"]["checked_at"]),
            "candidates_no_exact_content_in_checked_sources": sum(
                1 for x in ledger
                if x["discovery"]["outcome"] == "no_exact_content_found_in_checked_sources"
            ),
            "candidates_no_seed_or_exact_in_checked_sources": sum(
                1 for x in ledger
                if x["discovery"]["outcome"] == "no_seed_or_exact_content_found_in_checked_sources"
            ),
            "state_counts": dict(sorted(state_counts.items())),
        },
        "ledger": ledger,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a read-only evidence coverage ledger.")
    parser.add_argument("--federal", type=Path, default=DEFAULT_FEDERAL)
    parser.add_argument("--estadual", type=Path, default=DEFAULT_ESTADUAL)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--drafts", type=Path, default=DEFAULT_DRAFTS)
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL)
    parser.add_argument("--processing-state", type=Path)
    parser.add_argument("--exception-queue", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sources_payload = read_json(args.sources)
    source_rows = sources_payload.get("sources", [])
    if not isinstance(source_rows, list):
        raise RuntimeError(f"{args.sources}: sources must be a list")
    processing_state = (
        read_json(args.processing_state)
        if args.processing_state and args.processing_state.exists()
        else None
    )
    exception_queue = (
        read_json(args.exception_queue)
        if args.exception_queue and args.exception_queue.exists()
        else None
    )
    report = build_report(
        candidate_rows(args.federal, args.estadual),
        source_rows,
        list_field(args.drafts, "drafts"),
        list_field(args.reviews, "reviews"),
        list_field(args.canonical, "entries"),
        discovery_checked_at=clean(sources_payload.get("updated_at")),
        processing_state=processing_state,
        exception_queue=exception_queue,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
