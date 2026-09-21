#!/usr/bin/env python3
"""Targeted, read-only reacquisition of maintainer-approved Câmara sources.

This stage only rebuilds attributable exact-content source rows. It does not
perform semantic review, approve evidence, alter taxonomy, or write canonical
political data.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

import coletor_evidencias as collector
import discover_evidence_sources as discovery

ROOT = Path(__file__).resolve().parents[1]
CHAMBER_API = "https://dadosabertos.camara.leg.br/api/v2"
CHAMBER_PAGE = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao"


def clean(value: Any) -> str:
    return collector.clean(value)


def read_manifest(path: Path) -> dict[str, Any]:
    payload = collector.read_json(path)
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise RuntimeError("manifest deve conter lista records")
    return payload


def expected_page_url(proposition_id: int) -> str:
    return discovery.canonicalize_url(
        f"{CHAMBER_PAGE}?idProposicao={int(proposition_id)}"
    )


def author_matches(payload: dict[str, Any], chamber_id: int) -> dict[str, Any] | None:
    rows = payload.get("dados", [])
    if not isinstance(rows, list):
        return None
    wanted = str(int(chamber_id))
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_id = clean(row.get("id"))
        if raw_id and raw_id == wanted:
            return row
        uri = clean(row.get("uri"))
        if uri and re.search(rf"/deputados/{re.escape(wanted)}(?:$|[/?#])", uri):
            return row
    return None


def detail_row(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("dados")
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    raise RuntimeError("detalhe da proposição sem objeto dados")


def validate_record(
    row: dict[str, Any],
    *,
    candidates: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], int, int, str]:
    cid = clean(row.get("candidate_id"))
    if cid not in candidates:
        raise RuntimeError(f"SQ_CANDIDATO inexistente: {cid}")
    candidate = candidates[cid]
    mandate = candidate.get("current_mandate") or {}
    snapshot_chamber_id = mandate.get("chamber_id")
    try:
        chamber_id = int(row.get("chamber_id"))
        proposition_id = int(row.get("proposition_id"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("chamber_id/proposition_id inválido") from exc
    if int(snapshot_chamber_id or 0) != chamber_id:
        raise RuntimeError(
            f"chamber_id diverge do snapshot: manifest={chamber_id} snapshot={snapshot_chamber_id}"
        )
    source_url = discovery.canonicalize_url(clean(row.get("source_url")))
    expected = expected_page_url(proposition_id)
    if source_url != expected:
        raise RuntimeError(
            f"source_url não corresponde ao idProposicao: {source_url} != {expected}"
        )
    return candidate, chamber_id, proposition_id, source_url


def reacquire(
    *,
    manifest: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    fetch_json: Callable[[str], Any] = discovery.request_json,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    records = manifest.get("records") or []
    sources: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    for row in records:
        cid = clean(row.get("candidate_id"))
        order = row.get("curation_order")
        try:
            candidate, chamber_id, prop_id, source_url = validate_record(
                row, candidates=candidates
            )
            key = (cid, prop_id)
            if key in seen:
                raise RuntimeError("registro duplicado no manifest")
            seen.add(key)

            detail_url = f"{CHAMBER_API}/proposicoes/{prop_id}"
            authors_url = f"{CHAMBER_API}/proposicoes/{prop_id}/autores"
            detail = detail_row(fetch_json(detail_url))
            returned_id = detail.get("id")
            if int(returned_id or 0) != prop_id:
                raise RuntimeError(
                    f"API retornou idProposicao divergente: {returned_id}"
                )

            authors = fetch_json(authors_url)
            matched_author = author_matches(authors, chamber_id)
            if not matched_author:
                raise RuntimeError(
                    f"autoria oficial não contém chamber_id={chamber_id}"
                )

            sigla = clean(detail.get("siglaTipo"))
            numero = clean(detail.get("numero"))
            ano = clean(detail.get("ano"))
            ementa = clean(detail.get("ementa"))
            title = clean(f"{sigla} {numero}/{ano} — {ementa}")[:300]
            mandate = candidate.get("current_mandate") or {}

            sources.append(
                {
                    "candidate_id": cid,
                    "candidate_name": collector.candidate_display_name(candidate),
                    "source_kind": "institutional",
                    "discovery_status": "exact_content",
                    "seed_url": clean(mandate.get("profile_url")),
                    "source_url": source_url,
                    "source_title": title,
                    "source_publisher": "Câmara dos Deputados",
                    "published_at": collector.normalize_date(
                        clean(detail.get("dataApresentacao"))
                    ),
                    "collection_notes": (
                        "Reaquisição dirigida pela curadoria humana da #35. "
                        "Atribuição confirmada pela API oficial da Câmara no endpoint "
                        "de autores da própria proposição."
                    ),
                    "attribution_trust": "official_author_api",
                    "attribution_basis_hint": (
                        f"Câmara dos Deputados API: idDeputadoAutor={chamber_id}; "
                        f"idProposicao={prop_id}; autoria confirmada em /autores."
                    ),
                    "source_origin": {
                        "institution": "Câmara dos Deputados",
                        "discovery_method": "api_proposition_author_reacquisition",
                        "curation_order": order,
                        "chamber_id": chamber_id,
                        "proposition_id": prop_id,
                        "api_detail_url": detail_url,
                        "api_authors_url": authors_url,
                        "author_name": clean(
                            matched_author.get("nome")
                            or matched_author.get("nomeAutor")
                        ),
                        "author_uri": clean(matched_author.get("uri")),
                    },
                }
            )
        except Exception as exc:
            rejections.append(
                {
                    "candidate_id": cid,
                    "curation_order": order,
                    "proposition_id": row.get("proposition_id"),
                    "source_url": clean(row.get("source_url")),
                    "stage": "reacquisition",
                    "reason": "institutional_reacquisition_failed",
                    "detail": str(exc)[:1000],
                    "status": "open",
                }
            )

    sources = discovery.dedupe_sources(sources)
    metrics = {
        "requested": len(records),
        "reacquired": len(sources),
        "rejected": len(rejections),
        "candidate_count": len({clean(x.get("candidate_id")) for x in sources}),
    }
    return (
        {
            "version": "1.0.0",
            "semantics": (
                "Fontes exact-content reancoradas na API oficial da Câmara a partir "
                "de decisões humanas já registradas. Nenhuma entrada é evidência "
                "canônica sem coleta, binding de review e promoção explícita."
            ),
            "sources": sources,
        },
        {
            "version": "1.0.0",
            "semantics": (
                "Falhas de reaquisição institucional. Não são conclusões editoriais "
                "nem decisões políticas."
            ),
            "rejections": rejections,
        },
        metrics,
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reacquire curated Câmara sources with author verification."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-sources", type=Path, required=True)
    parser.add_argument("--output-rejections", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    args = parser.parse_args()

    manifest = read_manifest(args.manifest)
    candidates = collector.load_candidates()
    sources, rejections, metrics = reacquire(
        manifest=manifest,
        candidates=candidates,
    )
    write_json(args.output_sources, sources)
    write_json(args.output_rejections, rejections)
    write_json(args.metrics, metrics)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
