#!/usr/bin/env python3
"""Reliable, resumable processing of exact-content evidence sources.

This layer wraps the existing collector. It adds operational state, retries,
resume, targeted reprocessing and deterministic deduplication without changing
review semantics or canonical evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import coletor_evidencias as collector
import discover_evidence_sources as discovery

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "data/staging/topic-evidence-sources.json"
DEFAULT_DRAFTS = ROOT / "data/staging/topic-evidence-drafts.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    return collector.clean(value)


def make_source_id(item: dict[str, Any]) -> str:
    candidate_id = clean(item.get("candidate_id"))
    url = discovery.canonicalize_url(clean(item.get("source_url")))
    raw = f"{candidate_id}\n{url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def empty_state() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "updated_at": utc_now(),
        "semantics": (
            "Estado operacional não-canônico para resume/retry/reprocessamento. "
            "Status collected não equivale a aprovação editorial."
        ),
        "sources": {},
    }


def normalize_state(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return empty_state()
    states = payload.get("sources")
    if not isinstance(states, dict):
        raise RuntimeError("processing state deve conter objeto 'sources'")
    result = dict(payload)
    result["sources"] = {str(k): dict(v) for k, v in states.items()}
    result.setdefault("version", "1.0.0")
    result.setdefault("semantics", empty_state()["semantics"])
    return result


def merge_drafts(
    existing: list[dict[str, Any]],
    additions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in existing:
        draft_id = clean(item.get("draft_id"))
        if draft_id:
            by_id[draft_id] = item
    for item in additions:
        draft_id = clean(item.get("draft_id"))
        if draft_id and draft_id not in by_id:
            by_id[draft_id] = item
    return sorted(
        by_id.values(),
        key=lambda x: (
            clean(x.get("candidate_name")),
            clean(x.get("source_url")),
            clean(x.get("draft_id")),
        ),
    )


def stable_failure(
    *,
    source_id: str,
    item: dict[str, Any],
    error: str,
    attempts_used: int,
) -> dict[str, Any]:
    error = clean(error)[:1000]
    failure_key = hashlib.sha256(
        f"{source_id}\n{error}".encode("utf-8")
    ).hexdigest()[:20]
    return {
        "failure_id": failure_key,
        "source_id": source_id,
        "candidate_id": clean(item.get("candidate_id")),
        "candidate_name": clean(item.get("candidate_name")),
        "source_url": clean(item.get("source_url")),
        "stage": "collection",
        "error": error,
        "attempts_used": attempts_used,
        "observed_at": utc_now(),
    }


def attempt_source(
    item: dict[str, Any],
    *,
    candidates: dict[str, dict[str, Any]],
    tries: int,
    fetcher=collector.fetch_bytes,
    backoff_seconds: float = 0.5,
) -> tuple[dict[str, Any] | None, int, str]:
    last_error = ""
    used = 0
    for attempt in range(max(1, tries)):
        used += 1
        try:
            return (
                collector.collect_source(item, candidates=candidates, fetcher=fetcher),
                used,
                "",
            )
        except Exception as exc:
            last_error = str(exc)
            if attempt + 1 < max(1, tries) and backoff_seconds > 0:
                time.sleep(backoff_seconds * (2 ** attempt))
    return None, used, last_error


def run_batch(
    *,
    source_payload: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    existing_drafts: list[dict[str, Any]],
    state_payload: dict[str, Any] | None = None,
    max_attempts: int = 3,
    retries_per_run: int = 2,
    workers: int = 6,
    limit: int | None = None,
    per_candidate_limit: int | None = None,
    reprocess_source_ids: set[str] | None = None,
    reprocess_candidate_ids: set[str] | None = None,
    fetcher=collector.fetch_bytes,
    checkpoint: Callable[[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]], None] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    raw_sources = source_payload.get("sources")
    if not isinstance(raw_sources, list):
        raise RuntimeError("source payload deve conter lista 'sources'")

    reprocess_source_ids = reprocess_source_ids or set()
    reprocess_candidate_ids = reprocess_candidate_ids or set()
    state = normalize_state(state_payload)
    states: dict[str, dict[str, Any]] = state["sources"]

    exact_by_id: dict[str, dict[str, Any]] = {}
    for item in raw_sources:
        if clean(item.get("discovery_status")) != "exact_content":
            continue
        sid = make_source_id(item)
        if not sid:
            continue
        exact_by_id.setdefault(sid, item)

    eligible: list[tuple[str, dict[str, Any], bool, int]] = []
    skipped_collected = 0
    skipped_exhausted = 0
    skipped_permanent = 0
    for sid in sorted(exact_by_id):
        item = exact_by_id[sid]
        entry = states.get(sid, {})
        force = sid in reprocess_source_ids or clean(item.get("candidate_id")) in reprocess_candidate_ids
        attempts_before = int(entry.get("attempts", 0) or 0)
        previous_status = clean(entry.get("status"))
        previous_error = clean(entry.get("last_error"))
        snapshot_transport_upgrade = (
            isinstance(item.get("institutional_snapshot"), dict)
            and previous_status == "failed"
            and (
                "HTTP 429" in previous_error
                or re.search(r"HTTP 5\\d\\d", previous_error)
                or "falha de rede" in previous_error.casefold()
                or "timeout" in previous_error.casefold()
            )
        )

        if not force and previous_status == "collected":
            skipped_collected += 1
            continue
        if not force and previous_status in {"quarantined", "rejected"}:
            skipped_permanent += 1
            continue
        if not force and attempts_before >= max_attempts and not snapshot_transport_upgrade:
            skipped_exhausted += 1
            continue

        effective_force = force or snapshot_transport_upgrade
        remaining = 1 if snapshot_transport_upgrade else (
            retries_per_run if force else min(
                retries_per_run, max(1, max_attempts - attempts_before)
            )
        )
        eligible.append((sid, item, effective_force, remaining))

    # Fair batching: round-robin by SQ_CANDIDATO so a candidate with hundreds
    # of institutional documents cannot monopolize one processing cycle.
    by_candidate: dict[str, list[tuple[str, dict[str, Any], bool, int]]] = {}
    priority = {
        "official_candidate": 0,
        "official_party": 1,
        "institutional": 2,
        "secondary": 3,
        "tse_declared_social": 4,
    }
    for row in eligible:
        cid = clean(row[1].get("candidate_id"))
        by_candidate.setdefault(cid, []).append(row)
    for cid in by_candidate:
        by_candidate[cid].sort(
            key=lambda row: (
                priority.get(clean(row[1].get("source_kind")), 9),
                clean(row[1].get("source_url")),
                row[0],
            )
        )

    queue: list[tuple[str, dict[str, Any], bool, int]] = []
    taken: dict[str, int] = {cid: 0 for cid in by_candidate}
    candidate_ids = sorted(by_candidate)
    while candidate_ids:
        next_round: list[str] = []
        for cid in candidate_ids:
            rows = by_candidate[cid]
            if per_candidate_limit is not None and taken[cid] >= max(0, per_candidate_limit):
                continue
            if not rows:
                continue
            queue.append(rows.pop(0))
            taken[cid] += 1
            if rows and (per_candidate_limit is None or taken[cid] < max(0, per_candidate_limit)):
                next_round.append(cid)
            if limit is not None and len(queue) >= max(0, limit):
                next_round = []
                break
        candidate_ids = next_round
        if limit is not None and len(queue) >= max(0, limit):
            break

    new_drafts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    collected = 0
    failed = 0
    quarantined = 0
    rejected = 0
    content_changed = 0

    def save_checkpoint() -> None:
        if checkpoint:
            state["updated_at"] = utc_now()
            checkpoint(state, merge_drafts(existing_drafts, new_drafts), list(failures))

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        future_map = {
            pool.submit(
                attempt_source,
                item,
                candidates=candidates,
                tries=tries,
                fetcher=fetcher,
            ): (sid, item, force)
            for sid, item, force, tries in queue
        }

        for future in as_completed(future_map):
            sid, item, force = future_map[future]
            previous = dict(states.get(sid, {}))
            try:
                draft, attempts_used, error = future.result()
            except Exception as exc:
                draft, attempts_used, error = None, 1, str(exc)

            total_attempts = int(previous.get("attempts", 0) or 0) + attempts_used
            entry = {
                "source_id": sid,
                "candidate_id": clean(item.get("candidate_id")),
                "source_url": discovery.canonicalize_url(clean(item.get("source_url"))),
                "attempts": total_attempts,
                "last_attempt_at": utc_now(),
                "reprocess_count": int(previous.get("reprocess_count", 0) or 0) + (1 if force else 0),
            }

            if draft is not None:
                previous_hash = clean(previous.get("content_sha256"))
                current_hash = clean(draft.get("content_sha256"))
                changed = bool(previous_hash and current_hash and previous_hash != current_hash)
                entry.update(
                    {
                        "status": "collected",
                        "draft_id": clean(draft.get("draft_id")),
                        "source_sha256": clean(draft.get("source_sha256")),
                        "content_sha256": current_hash,
                        "previous_content_sha256": previous_hash if changed else "",
                        "content_changed": changed,
                        "last_error": "",
                    }
                )
                states[sid] = entry
                new_drafts.append(draft)
                collected += 1
                content_changed += int(changed)
            else:
                normalized_error = clean(error)
                if normalized_error.startswith("quality_quarantine:"):
                    failure_status = "quarantined"
                    quarantined += 1
                elif normalized_error.startswith("quality_reject:"):
                    failure_status = "rejected"
                    rejected += 1
                else:
                    failure_status = "failed"
                    failed += 1

                entry.update(
                    {
                        "status": failure_status,
                        "draft_id": clean(previous.get("draft_id")),
                        "source_sha256": clean(previous.get("source_sha256")),
                        "content_sha256": clean(previous.get("content_sha256")),
                        "previous_content_sha256": clean(previous.get("previous_content_sha256")),
                        "content_changed": bool(previous.get("content_changed")),
                        "last_error": normalized_error[:1000],
                    }
                )
                states[sid] = entry
                failure = stable_failure(
                    source_id=sid,
                    item=item,
                    error=error,
                    attempts_used=attempts_used,
                )
                failure["processing_status"] = failure_status
                failures.append(failure)

            save_checkpoint()

    drafts = merge_drafts(existing_drafts, new_drafts)
    state["updated_at"] = utc_now()
    metrics = {
        "exact_sources": len(exact_by_id),
        "eligible_before_fair_batch": len(eligible),
        "queued": len(queue),
        "candidates_queued": len({clean(row[1].get("candidate_id")) for row in queue}),
        "collected": collected,
        "failed": failed,
        "quarantined": quarantined,
        "rejected": rejected,
        "skipped_collected": skipped_collected,
        "skipped_exhausted": skipped_exhausted,
        "skipped_permanent": skipped_permanent,
        "drafts_total": len(drafts),
        "state_records": len(states),
        "content_changed": content_changed,
    }
    return state, drafts, failures, metrics


def read_optional(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_outputs(
    *,
    state_path: Path,
    drafts_path: Path,
    failures_path: Path,
    metrics_path: Path,
    state: dict[str, Any],
    drafts: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    metrics: dict[str, int] | None = None,
) -> None:
    for path in (state_path, drafts_path, failures_path, metrics_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    drafts_path.write_text(
        json.dumps(collector.drafts_envelope(drafts), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    failures_path.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "updated_at": utc_now(),
                "semantics": "Falhas operacionais de coleta; não são conclusões editoriais.",
                "failures": failures,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    if metrics is not None:
        metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reliable exact-content batch processor.")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--existing-drafts", type=Path, default=DEFAULT_DRAFTS)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output-drafts", type=Path, required=True)
    parser.add_argument("--output-failures", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--retries-per-run", type=int, default=2)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--per-candidate-limit", type=int, default=None)
    parser.add_argument("--reprocess-source-id", action="append", default=[])
    parser.add_argument("--reprocess-candidate-id", action="append", default=[])
    args = parser.parse_args()

    candidates = collector.load_candidates()
    source_payload = collector.read_json(args.sources)
    existing_drafts_payload = read_optional(args.existing_drafts, collector.drafts_envelope([]))
    existing_drafts = existing_drafts_payload.get("drafts", [])
    if not isinstance(existing_drafts, list):
        raise RuntimeError("existing drafts inválido")
    state_payload = read_optional(args.state, empty_state())

    latest_failures: list[dict[str, Any]] = []

    def checkpoint(state, drafts, failures):
        nonlocal latest_failures
        latest_failures = failures
        write_outputs(
            state_path=args.state,
            drafts_path=args.output_drafts,
            failures_path=args.output_failures,
            metrics_path=args.metrics,
            state=state,
            drafts=drafts,
            failures=failures,
            metrics={},
        )

    state, drafts, failures, metrics = run_batch(
        source_payload=source_payload,
        candidates=candidates,
        existing_drafts=existing_drafts,
        state_payload=state_payload,
        max_attempts=max(1, args.max_attempts),
        retries_per_run=max(1, args.retries_per_run),
        workers=max(1, args.workers),
        limit=args.limit,
        per_candidate_limit=args.per_candidate_limit,
        reprocess_source_ids=set(args.reprocess_source_id),
        reprocess_candidate_ids=set(args.reprocess_candidate_id),
        checkpoint=checkpoint,
    )
    write_outputs(
        state_path=args.state,
        drafts_path=args.output_drafts,
        failures_path=args.output_failures,
        metrics_path=args.metrics,
        state=state,
        drafts=drafts,
        failures=failures,
        metrics=metrics,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
