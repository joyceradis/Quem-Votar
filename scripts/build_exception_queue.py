#!/usr/bin/env python3
"""Build a deterministic, history-preserving exception queue.

The queue separates human judgement from retryable/technical failures.
It is operational metadata only and never approves or publishes political
evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import coletor_evidencias as collector

ROOT = Path(__file__).resolve().parents[1]


HUMAN_REASONS = {
    "ambiguous_attribution",
    "homonym",
    "conflicting_sources",
    "unclear_publication_date",
    "evidence_type_ambiguity",
    "unsupported_topic",
    "source_content_mismatch",
}

RETRYABLE_REASONS = {
    "transient_fetch_failure",
    "institutional_source_failure",
}

DATA_QUALITY_REASONS = {
    "insufficient_text",
    "dummy_text",
    "suspected_spam_content",
    "link_aggregator_internal_content",
    "unsupported_document_type",
    "invalid_declared_seed",
    "source_unavailable",
    "needs_ocr",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    return collector.clean(value)


def classify_error(error: str, fallback: str = "source_content_mismatch") -> str:
    text = clean(error).casefold()
    if not text:
        return fallback

    if "quality_quarantine:suspected_spam_content" in text:
        return "suspected_spam_content"
    if "quality_reject:dummy_text" in text:
        return "dummy_text"
    if "quality_reject:link_aggregator_internal_content" in text:
        return "link_aggregator_internal_content"
    if "ocr não é executado" in text or "ocr nao e executado" in text:
        return "needs_ocr"
    if "conteúdo textual insuficiente" in text or "conteudo textual insuficiente" in text:
        return "insufficient_text"
    if "tipo de conteúdo ainda não suportado" in text or "tipo de conteudo ainda nao suportado" in text:
        return "unsupported_document_type"
    if "redirecionamento terminou" in text or "não específica" in text or "nao especifica" in text:
        return "source_content_mismatch"
    if re.search(r"\b404\b", text):
        return "source_unavailable"
    if (
        "timeout" in text
        or "timed out" in text
        or "http 403" in text
        or "http 429" in text
        or "falha de rede" in text
        or "connection" in text
        or "temporar" in text
    ):
        return "transient_fetch_failure"
    return fallback


def normalize_discovery_reason(raw: str) -> str:
    raw = clean(raw)
    mapping = {
        "declared_seed_not_normalizable": "invalid_declared_seed",
        "site_seed_not_https": "invalid_declared_seed",
        "site_fetch_failed": "transient_fetch_failure",
        "site_html_parse_failed": "source_content_mismatch",
        "site_worker_failed": "transient_fetch_failure",
        "chamber_discovery_failed": "institutional_source_failure",
    }
    return mapping.get(raw, raw if raw in ALL_REASONS else "source_content_mismatch")


ALL_REASONS = HUMAN_REASONS | RETRYABLE_REASONS | DATA_QUALITY_REASONS


def queue_class(reason: str) -> str:
    if reason in HUMAN_REASONS:
        return "human_review"
    if reason in RETRYABLE_REASONS:
        return "retryable"
    return "data_quality"


def exception_id(
    *,
    candidate_id: str,
    reason: str,
    stage: str,
    source_url: str = "",
    draft_id: str = "",
) -> str:
    basis = "\n".join(
        (
            clean(candidate_id),
            clean(reason),
            clean(stage),
            clean(source_url),
            clean(draft_id),
        )
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]


def candidate_name_map(candidates: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {
        cid: collector.candidate_display_name(row)
        for cid, row in candidates.items()
    }


def disposition_for(reason: str) -> str:
    if reason == "suspected_spam_content":
        return "quarantine"
    if reason in {"dummy_text", "link_aggregator_internal_content"}:
        return "reject"
    if reason in RETRYABLE_REASONS:
        return "retry"
    if reason in HUMAN_REASONS:
        return "human_review"
    return "data_quality"


def trusted_institutional_attribution(draft: dict[str, Any]) -> bool:
    origin = draft.get("source_origin") or {}
    return (
        clean(draft.get("source_kind")) == "institutional"
        and clean(draft.get("attribution_trust"))
        in {"official_author_api", "official_author_bulk"}
        and clean(origin.get("institution")) == "Câmara dos Deputados"
        and clean(origin.get("discovery_method"))
        in {
            "api_idDeputadoAutor",
            "api_idDeputadoAutor_paginated_reacquisition",
            "bulk_proposicoesAutores_join",
        }
        and bool(clean(origin.get("chamber_id")))
        and bool(clean(origin.get("proposition_id")))
    )


def make_exception(
    *,
    candidate_id: str,
    candidate_name: str,
    reason: str,
    stage: str,
    source_url: str = "",
    draft_id: str = "",
    detail: str = "",
    origin_id: str = "",
) -> dict[str, Any]:
    if reason not in ALL_REASONS:
        raise RuntimeError(f"exception reason não enumerado: {reason}")
    kind = queue_class(reason)
    return {
        "exception_id": exception_id(
            candidate_id=candidate_id,
            reason=reason,
            stage=stage,
            source_url=source_url,
            draft_id=draft_id,
        ),
        "candidate_id": clean(candidate_id),
        "candidate_name": clean(candidate_name),
        "stage": clean(stage),
        "reason": reason,
        "queue_class": kind,
        "disposition": disposition_for(reason),
        "requires_human": kind == "human_review",
        "source_url": clean(source_url),
        "draft_id": clean(draft_id),
        "detail": clean(detail)[:1200],
        "origin_id": clean(origin_id),
        "status": "open",
    }


def from_discovery(
    payload: dict[str, Any],
    names: dict[str, str],
) -> list[dict[str, Any]]:
    rows = payload.get("rejections", [])
    if not isinstance(rows, list):
        raise RuntimeError("discovery rejections deve conter lista")
    out = []
    for row in rows:
        cid = clean(row.get("candidate_id"))
        reason = normalize_discovery_reason(clean(row.get("reason")))
        detail = clean(row.get("detail") or row.get("raw_value"))
        out.append(
            make_exception(
                candidate_id=cid,
                candidate_name=clean(row.get("candidate_name")) or names.get(cid, ""),
                reason=reason,
                stage="discovery",
                source_url=clean(row.get("source_url")),
                detail=detail,
                origin_id=clean(row.get("rejection_id")),
            )
        )
    return out


def from_processing(
    payload: dict[str, Any],
    names: dict[str, str],
) -> list[dict[str, Any]]:
    rows = payload.get("failures", [])
    if not isinstance(rows, list):
        raise RuntimeError("processing failures deve conter lista")
    out = []
    for row in rows:
        cid = clean(row.get("candidate_id"))
        error = clean(row.get("error"))
        reason = classify_error(error)
        out.append(
            make_exception(
                candidate_id=cid,
                candidate_name=clean(row.get("candidate_name")) or names.get(cid, ""),
                reason=reason,
                stage=clean(row.get("stage")) or "collection",
                source_url=clean(row.get("source_url")),
                detail=error,
                origin_id=clean(row.get("failure_id")),
            )
        )
    return out


def from_drafts(
    payload: dict[str, Any],
    names: dict[str, str],
) -> list[dict[str, Any]]:
    rows = payload.get("drafts", [])
    if not isinstance(rows, list):
        raise RuntimeError("draft payload deve conter lista")
    out = []
    for draft in rows:
        cid = clean(draft.get("candidate_id"))
        common = {
            "candidate_id": cid,
            "candidate_name": clean(draft.get("candidate_name")) or names.get(cid, ""),
            "stage": "draft_validation",
            "source_url": clean(draft.get("source_url")),
            "draft_id": clean(draft.get("draft_id")),
        }
        if draft.get("candidate_mentioned") is False and not trusted_institutional_attribution(draft):
            out.append(
                make_exception(
                    **common,
                    reason="ambiguous_attribution",
                    detail="O texto coletado não contém menção nominal detectável à candidatura.",
                )
            )
        if not clean(draft.get("published_at")):
            out.append(
                make_exception(
                    **common,
                    reason="unclear_publication_date",
                    detail="A data de publicação não foi determinada deterministicamente.",
                )
            )
    return out


def normalize_previous(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not payload:
        return {}
    rows = payload.get("exceptions", [])
    if not isinstance(rows, list):
        raise RuntimeError("previous exception queue deve conter lista")
    out = {}
    for row in rows:
        eid = clean(row.get("exception_id"))
        if eid:
            out[eid] = dict(row)
    return out


def merge_history(
    current: list[dict[str, Any]],
    previous_payload: dict[str, Any] | None,
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    now = observed_at or utc_now()
    previous = normalize_previous(previous_payload)
    current_by_id = {clean(x.get("exception_id")): dict(x) for x in current}
    merged: list[dict[str, Any]] = []

    for eid, item in current_by_id.items():
        old = previous.get(eid, {})
        history = list(old.get("history") or [])
        old_status = clean(old.get("status"))
        occurrences = int(old.get("occurrences", 0) or 0) + 1

        if old_status in {"resolved", "cleared"}:
            history.append(
                {
                    "at": now,
                    "event": "reopened",
                    "previous_status": old_status,
                }
            )

        item.update(
            {
                "status": "open",
                "first_seen_at": clean(old.get("first_seen_at")) or now,
                "last_seen_at": now,
                "occurrences": occurrences,
                "resolved_at": "",
                "resolved_by": "",
                "resolution_note": "",
                "history": history,
            }
        )
        merged.append(item)

    # Preserve resolved history. Open exceptions absent in the current run become
    # cleared automatically; this is operational resolution, not editorial approval.
    for eid, old in previous.items():
        if eid in current_by_id:
            continue
        item = dict(old)
        status = clean(item.get("status")) or "open"
        history = list(item.get("history") or [])
        if status == "open":
            history.append({"at": now, "event": "cleared_by_recheck"})
            item["status"] = "cleared"
            item["resolved_at"] = now
            item["resolved_by"] = "pipeline"
            item["resolution_note"] = "Exceção não reapareceu na execução atual."
            item["history"] = history
        item["last_seen_at"] = clean(item.get("last_seen_at")) or now
        merged.append(item)

    return sorted(
        merged,
        key=lambda x: (
            clean(x.get("status")) != "open",
            clean(x.get("queue_class")),
            clean(x.get("candidate_name")),
            clean(x.get("reason")),
            clean(x.get("exception_id")),
        ),
    )


def build_queue(
    *,
    candidates: dict[str, dict[str, Any]],
    discovery_payload: dict[str, Any],
    processing_payload: dict[str, Any],
    drafts_payload: dict[str, Any],
    previous_payload: dict[str, Any] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    names = candidate_name_map(candidates)
    current = (
        from_discovery(discovery_payload, names)
        + from_processing(processing_payload, names)
        + from_drafts(drafts_payload, names)
    )
    deduped = {
        clean(item.get("exception_id")): item
        for item in current
        if clean(item.get("exception_id"))
    }
    merged = merge_history(list(deduped.values()), previous_payload, observed_at)

    open_rows = [x for x in merged if clean(x.get("status")) == "open"]
    metrics = {
        "total_records": len(merged),
        "open": len(open_rows),
        "human_review_open": sum(
            1 for x in open_rows if x.get("queue_class") == "human_review"
        ),
        "retryable_open": sum(
            1 for x in open_rows if x.get("queue_class") == "retryable"
        ),
        "data_quality_open": sum(
            1 for x in open_rows if x.get("queue_class") == "data_quality"
        ),
        "cleared_or_resolved": sum(
            1 for x in merged if clean(x.get("status")) in {"cleared", "resolved"}
        ),
    }
    return {
        "version": "1.0.0",
        "updated_at": observed_at or utc_now(),
        "semantics": (
            "Fila operacional de exceções. human_review exige julgamento; retryable e "
            "data_quality devem ser tratados pela pipeline quando possível. Nenhum estado "
            "desta fila aprova evidência política."
        ),
        "allowed_reasons": {
            "human_review": sorted(HUMAN_REASONS),
            "retryable": sorted(RETRYABLE_REASONS),
            "data_quality": sorted(DATA_QUALITY_REASONS),
        },
        "metrics": metrics,
        "exceptions": merged,
    }


def resolve_exception(
    payload: dict[str, Any],
    *,
    exception_id_value: str,
    resolver: str,
    note: str,
    resolved_at: str | None = None,
) -> dict[str, Any]:
    exception_id_value = clean(exception_id_value)
    resolver = clean(resolver)
    note = clean(note)
    if not exception_id_value or not resolver or not note:
        raise RuntimeError("exception-id, resolver e note são obrigatórios")
    rows = payload.get("exceptions", [])
    if not isinstance(rows, list):
        raise RuntimeError("queue inválida")
    found = False
    now = resolved_at or utc_now()
    result = dict(payload)
    result_rows = []
    for row in rows:
        item = dict(row)
        if clean(item.get("exception_id")) == exception_id_value:
            found = True
            history = list(item.get("history") or [])
            history.append(
                {
                    "at": now,
                    "event": "resolved",
                    "resolver": resolver,
                    "note": note,
                }
            )
            item.update(
                {
                    "status": "resolved",
                    "resolved_at": now,
                    "resolved_by": resolver,
                    "resolution_note": note,
                    "history": history,
                }
            )
        result_rows.append(item)
    if not found:
        raise RuntimeError(f"exception_id inexistente: {exception_id_value}")
    result["updated_at"] = now
    result["exceptions"] = result_rows
    return result


def read_optional(path: Path | None, default: dict[str, Any]) -> dict[str, Any]:
    if path is None or not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/resolve deterministic exception queue.")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("--discovery-rejections", type=Path, required=True)
    build.add_argument("--processing-failures", type=Path, required=True)
    build.add_argument("--drafts", type=Path, required=True)
    build.add_argument("--previous", type=Path)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--metrics", type=Path, required=True)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--queue", type=Path, required=True)
    resolve.add_argument("--exception-id", required=True)
    resolve.add_argument("--resolver", required=True)
    resolve.add_argument("--note", required=True)
    resolve.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    if args.command == "resolve":
        payload = collector.read_json(args.queue)
        result = resolve_exception(
            payload,
            exception_id_value=args.exception_id,
            resolver=args.resolver,
            note=args.note,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return 0

    candidates = collector.load_candidates()
    result = build_queue(
        candidates=candidates,
        discovery_payload=collector.read_json(args.discovery_rejections),
        processing_payload=collector.read_json(args.processing_failures),
        drafts_payload=collector.read_json(args.drafts),
        previous_payload=read_optional(args.previous, {}) if args.previous else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.metrics.write_text(
        json.dumps(result["metrics"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
