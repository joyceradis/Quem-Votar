#!/usr/bin/env python3
"""Build a bounded, candidate-fair curation delta from non-canonical drafts.

This is a handoff generator only. It never approves, promotes, scores, ranks,
or rewrites political evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import discover_evidence_sources as discovery


PRIMARY_CHAMBER_SIGLAS = {
    "PL",
    "PLP",
    "PEC",
    "PDL",
    "PRC",
    "REQ",
    "RPD",
    "PRL",
    "PRLP",
    "PRLE",
}


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def decided_ids(payload: dict[str, Any]) -> set[str]:
    groups = payload.get("decisions") or {}
    result: set[str] = set()
    if not isinstance(groups, dict):
        raise RuntimeError("decisions deve ser objeto")
    for values in groups.values():
        if isinstance(values, list):
            result.update(clean(x) for x in values if clean(x))
    return result


def is_trusted_chamber(draft: dict[str, Any]) -> bool:
    origin = draft.get("source_origin") or {}
    return (
        clean(draft.get("source_kind")) == "institutional"
        and clean(draft.get("source_publisher")).casefold()
        == "câmara dos deputados"
        and clean(draft.get("attribution_trust"))
        in {"official_author_api", "official_author_bulk"}
        and clean(origin.get("institution")) == "Câmara dos Deputados"
        and bool(clean(origin.get("chamber_id")))
        and bool(clean(origin.get("proposition_id")))
    )


def lane(draft: dict[str, Any]) -> str:
    if is_trusted_chamber(draft):
        return "institutional_trusted"
    kind = clean(draft.get("source_kind"))
    if kind in {"official_candidate", "official_party"}:
        return "declared_official"
    if kind == "secondary":
        return "secondary"
    return "other"


LANE_PRIORITY = {
    "institutional_trusted": 0,
    "declared_official": 1,
    "secondary": 2,
    "other": 3,
}


def official_document_type(row: dict[str, Any]) -> str:
    value = clean(row.get("official_document_type"))
    if value:
        return value
    snapshot = row.get("institutional_snapshot") or {}
    if isinstance(snapshot, dict):
        return clean(snapshot.get("siglaTipo"))
    return ""


def chamber_document_priority(row: dict[str, Any]) -> int:
    """Technical routing only; never an approval or content score."""
    if not is_trusted_chamber(row):
        return 0
    sigla = official_document_type(row).upper()
    if not sigla:
        return 1
    return 0 if sigla in PRIMARY_CHAMBER_SIGLAS else 1


def publication_recency_key(row: dict[str, Any]) -> int:
    """Newest valid ISO date first inside the same technical priority.

    A digit count alone does not prove a real calendar date (e.g. an
    "20261340" garbage value is 8 digits but not a month/day that exists),
    so this rejects anything datetime cannot parse and treats it exactly
    like a non-date instead of silently sorting it as an arbitrary date.
    """
    value = clean(row.get("published_at"))[:10].replace("-", "")
    if len(value) != 8 or not value.isdigit():
        return 0
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError:
        return 0
    return -int(value)


def is_candidate_site_listing(draft: dict[str, Any]) -> bool:
    if clean(draft.get("source_kind")) not in {"official_candidate", "official_party"}:
        return False
    return not discovery.looks_like_exact_content(
        clean(draft.get("source_url")),
        clean(draft.get("source_title")),
    )


def latest_source_index(
    payload: dict[str, Any] | None,
) -> dict[tuple[str, str], dict[str, Any]]:
    if not payload:
        return {}
    rows = payload.get("sources") or []
    if not isinstance(rows, list):
        raise RuntimeError("sources deve ser lista")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        cid = clean(row.get("candidate_id"))
        url = discovery.canonicalize_url(clean(row.get("source_url")))
        if not cid or not url:
            continue
        result[(cid, url)] = row
    return result


def enrich_from_source(
    draft: dict[str, Any],
    source: dict[str, Any] | None,
) -> dict[str, Any]:
    if not source:
        return dict(draft)

    result = dict(draft)
    snapshot = source.get("institutional_snapshot") or {}
    if not isinstance(snapshot, dict):
        snapshot = {}

    source_origin = source.get("source_origin") or {}
    if not isinstance(source_origin, dict):
        source_origin = {}

    if not result.get("source_origin") and source_origin:
        result["source_origin"] = source_origin
    if not clean(result.get("attribution_trust")):
        result["attribution_trust"] = clean(source.get("attribution_trust"))

    doc_type = clean(snapshot.get("siglaTipo"))
    if doc_type:
        result["official_document_type"] = doc_type

    themes = snapshot.get("official_themes")
    if isinstance(themes, list):
        result["official_themes"] = themes

    proposition_id = clean(
        snapshot.get("proposition_id") or source_origin.get("proposition_id")
    )
    if proposition_id:
        result["official_proposition_id"] = proposition_id

    transport = clean(snapshot.get("transport"))
    if transport:
        result["discovery_transport"] = transport

    bulk_sha = clean(
        snapshot.get("bulk_snapshot_sha256")
        or source_origin.get("bulk_snapshot_sha256")
    )
    if bulk_sha:
        result["bulk_snapshot_sha256"] = bulk_sha

    result["latest_source_attribution_trust"] = clean(
        source.get("attribution_trust")
    )
    return result


def build_batch(
    *,
    drafts_payload: dict[str, Any],
    canonical_payload: dict[str, Any],
    decisions_payload: dict[str, Any],
    sources_payload: dict[str, Any] | None = None,
    limit: int = 100,
    per_candidate_limit: int = 12,
) -> tuple[dict[str, Any], dict[str, int]]:
    drafts = drafts_payload.get("drafts") or []
    canonical = canonical_payload.get("entries") or []
    if not isinstance(drafts, list) or not isinstance(canonical, list):
        raise RuntimeError("drafts/entries inválidos")

    source_index = latest_source_index(sources_payload)
    known_decisions = decided_ids(decisions_payload)
    canonical_urls = {
        discovery.canonicalize_url(clean(row.get("source_url")))
        for row in canonical
        if clean(row.get("source_url"))
    }
    canonical_candidate_urls = {
        (
            clean(row.get("candidate_id")),
            discovery.canonicalize_url(clean(row.get("source_url"))),
        )
        for row in canonical
        if clean(row.get("candidate_id")) and clean(row.get("source_url"))
    }

    skipped_decided = 0
    skipped_canonical = 0
    skipped_nonpending = 0
    skipped_listing = 0
    by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for raw_draft in drafts:
        did = clean(raw_draft.get("draft_id"))
        cid = clean(raw_draft.get("candidate_id"))
        url = discovery.canonicalize_url(clean(raw_draft.get("source_url")))
        if not did or not cid or not url:
            continue

        draft = enrich_from_source(raw_draft, source_index.get((cid, url)))

        # Dedup first: keep only the newest draft for each (candidate, source) pair.
        # Then check decisions on the newest draft_id to avoid selecting an older
        # version when the newer one was already decided.
        key = (cid, url)
        existing = by_key.get(key)
        if existing is not None and not (
            clean(draft.get("captured_at")),
            did,
        ) > (
            clean(existing.get("captured_at")),
            clean(existing.get("draft_id")),
        ):
            continue
        by_key[key] = draft

    # Now apply decision/canonical/status/listing filters to the deduplicated drafts.
    eligible = []
    for draft in by_key.values():
        did = clean(draft.get("draft_id"))
        cid = clean(draft.get("candidate_id"))
        url = discovery.canonicalize_url(clean(draft.get("source_url")))

        if did in known_decisions:
            skipped_decided += 1
            continue
        if (cid, url) in canonical_candidate_urls:
            skipped_canonical += 1
            continue
        if clean(draft.get("review_status") or "pending") != "pending":
            skipped_nonpending += 1
            continue
        if is_candidate_site_listing(draft):
            skipped_listing += 1
            continue

        eligible.append(draft)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        grouped[clean(row.get("candidate_id"))].append(row)

    for cid in grouped:
        grouped[cid].sort(
            key=lambda row: (
                LANE_PRIORITY.get(lane(row), 9),
                chamber_document_priority(row),
                # Derived from the same parse as publication_recency_key, not a
                # separate empty-string check: an invalid-but-non-empty date
                # (e.g. "2026-13-40") must land in the same fallback bucket as
                # a genuinely absent one, never sort ahead of it.
                publication_recency_key(row) == 0,
                publication_recency_key(row),
                clean(row.get("source_url")),
                clean(row.get("draft_id")),
            )
        )

    selected: list[dict[str, Any]] = []
    taken: dict[str, int] = defaultdict(int)
    active = sorted(grouped)
    while active and len(selected) < max(0, limit):
        next_round: list[str] = []
        for cid in active:
            if taken[cid] >= max(0, per_candidate_limit):
                continue
            rows = grouped[cid]
            if not rows:
                continue
            selected.append(rows.pop(0))
            taken[cid] += 1
            if rows and taken[cid] < max(0, per_candidate_limit):
                next_round.append(cid)
            if len(selected) >= max(0, limit):
                next_round = []
                break
        active = next_round

    handoff = []
    for row in selected:
        official_themes = row.get("official_themes")
        if not isinstance(official_themes, list):
            official_themes = []
        handoff.append(
            {
                "draft_id": clean(row.get("draft_id")),
                "candidate_id": clean(row.get("candidate_id")),
                "candidate_name": clean(row.get("candidate_name")),
                "office": clean(row.get("office")),
                "party": clean(row.get("party")),
                "lane": lane(row),
                "document_priority": chamber_document_priority(row),
                "official_document_type": official_document_type(row),
                "official_proposition_id": clean(row.get("official_proposition_id")),
                "official_themes": official_themes,
                "discovery_transport": clean(row.get("discovery_transport")),
                "bulk_snapshot_sha256": clean(row.get("bulk_snapshot_sha256")),
                "source_kind": clean(row.get("source_kind")),
                "source_url": clean(row.get("source_url")),
                "source_title": clean(row.get("source_title")),
                "source_publisher": clean(row.get("source_publisher")),
                "published_at": clean(row.get("published_at")),
                "candidate_mentioned": bool(row.get("candidate_mentioned")),
                "attribution_trust": clean(row.get("attribution_trust")),
                "latest_source_attribution_trust": clean(
                    row.get("latest_source_attribution_trust")
                ),
                "attribution_basis_hint": clean(row.get("attribution_basis_hint")),
                "raw_excerpt": clean(row.get("raw_excerpt")),
                "review_status": "pending",
            }
        )

    batch_basis = "\n".join(x["draft_id"] for x in handoff)
    batch_id = (
        hashlib.sha256(batch_basis.encode("utf-8")).hexdigest()[:16]
        if handoff
        else ""
    )
    metrics = {
        "drafts_total": len(drafts),
        "known_decision_ids": len(known_decisions),
        "canonical_urls": len(canonical_urls),
        "canonical_candidate_urls": len(canonical_candidate_urls),
        "skipped_decided": skipped_decided,
        "skipped_canonical": skipped_canonical,
        "skipped_nonpending": skipped_nonpending,
        "skipped_listing": skipped_listing,
        "eligible_unique": len(eligible),
        "eligible_primary_chamber": sum(
            is_trusted_chamber(row) and chamber_document_priority(row) == 0
            for row in eligible
        ),
        "candidates_eligible": len(grouped),
        "selected": len(handoff),
        "selected_primary_chamber": sum(
            row["lane"] == "institutional_trusted"
            and row["document_priority"] == 0
            for row in handoff
        ),
        "candidates_selected": len({x["candidate_id"] for x in handoff}),
    }
    payload = {
        "version": "1.1.0",
        "batch_id": batch_id,
        "semantics": (
            "New curation work only. Candidate-fair technical batching; no political "
            "ranking, semantic approval, V5.5 topic mapping, or canonical publication "
            "is performed."
        ),
        "policy": {
            "max_records": limit,
            "max_per_candidate": per_candidate_limit,
            "lane_order": list(LANE_PRIORITY),
            "chamber_primary_document_types": sorted(PRIMARY_CHAMBER_SIGLAS),
            "document_type_policy": (
                "Technical review priority only. Other official document types remain "
                "in staging and are not rejected or approved automatically."
            ),
            "official_theme_policy": (
                "Câmara codTema/tema are transported as official metadata only; "
                "no automatic mapping to the public V5.5 taxonomy."
            ),
            "autoapproval": False,
        },
        "metrics": metrics,
        "items": handoff,
    }
    return payload, metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", type=Path, required=True)
    ap.add_argument("--canonical", type=Path, required=True)
    ap.add_argument("--decisions", type=Path, required=True)
    ap.add_argument("--sources", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--metrics", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--per-candidate-limit", type=int, default=12)
    args = ap.parse_args()

    payload, metrics = build_batch(
        drafts_payload=read_json(args.drafts),
        canonical_payload=read_json(args.canonical),
        decisions_payload=read_json(args.decisions),
        sources_payload=read_json(args.sources) if args.sources else None,
        limit=max(0, args.limit),
        per_candidate_limit=max(1, args.per_candidate_limit),
    )
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.metrics.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
