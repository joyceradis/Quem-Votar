#!/usr/bin/env python3
"""Targeted, read-only reacquisition of maintainer-approved Câmara sources.

This stage rebuilds attributable exact-content source rows by paginating the
official Câmara propositions endpoint filtered by idDeputadoAutor. It does not
perform semantic review, approve evidence, alter taxonomy, or write canonical
political data.
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import coletor_evidencias as collector
import discover_evidence_sources as discovery

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


def first_author_page(chamber_id: int) -> str:
    query = urllib.parse.urlencode(
        {
            "idDeputadoAutor": int(chamber_id),
            "ordem": "DESC",
            "ordenarPor": "id",
            "itens": 100,
            "pagina": 1,
        }
    )
    return f"{CHAMBER_API}/proposicoes?{query}"


def next_link(payload: dict[str, Any]) -> str:
    links = payload.get("links", [])
    if not isinstance(links, list):
        return ""
    for row in links:
        if not isinstance(row, dict):
            continue
        if clean(row.get("rel")).casefold() == "next":
            return clean(row.get("href"))
    return ""


def find_target_propositions(
    *,
    chamber_id: int,
    target_ids: set[int],
    fetch_json: Callable[[str], Any],
    max_pages: int = 25,
) -> tuple[dict[int, tuple[dict[str, Any], str, int]], str]:
    found: dict[int, tuple[dict[str, Any], str, int]] = {}
    url = first_author_page(chamber_id)
    visited: set[str] = set()
    page_number = 0

    while url and page_number < max_pages and target_ids - set(found):
        if url in visited:
            return found, "paginação da API entrou em ciclo"
        visited.add(url)
        page_number += 1
        try:
            payload = fetch_json(url)
        except Exception as exc:
            return found, f"falha na consulta paginada: {exc}"

        rows = payload.get("dados", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            return found, "API paginada não retornou lista em dados"

        for item in rows:
            if not isinstance(item, dict):
                continue
            try:
                prop_id = int(item.get("id"))
            except (TypeError, ValueError):
                continue
            if prop_id in target_ids and prop_id not in found:
                found[prop_id] = (item, url, page_number)

        url = next_link(payload) if isinstance(payload, dict) else ""

    if target_ids - set(found) and page_number >= max_pages:
        return found, f"limite de paginação atingido ({max_pages})"
    return found, ""


def source_from_api_item(
    *,
    row: dict[str, Any],
    candidate: dict[str, Any],
    chamber_id: int,
    prop_id: int,
    source_url: str,
    item: dict[str, Any],
    api_url: str,
    api_page: int,
) -> dict[str, Any]:
    sigla = clean(item.get("siglaTipo"))
    numero = clean(item.get("numero"))
    ano = clean(item.get("ano"))
    ementa = clean(item.get("ementa"))
    title = clean(f"{sigla} {numero}/{ano} — {ementa}")[:300]
    mandate = candidate.get("current_mandate") or {}

    return {
        "candidate_id": clean(row.get("candidate_id")),
        "candidate_name": collector.candidate_display_name(candidate),
        "source_kind": "institutional",
        "discovery_status": "exact_content",
        "seed_url": clean(mandate.get("profile_url")),
        "source_url": source_url,
        "source_title": title,
        "source_publisher": "Câmara dos Deputados",
        "published_at": collector.normalize_date(
            clean(item.get("dataApresentacao"))
        ),
        "collection_notes": (
            "Reaquisição dirigida pela curadoria humana da #35. "
            "Atribuição confirmada pela consulta oficial paginada "
            "idDeputadoAutor da Câmara."
        ),
        "attribution_trust": "official_author_api",
        "attribution_basis_hint": (
            f"Câmara dos Deputados API: idDeputadoAutor={chamber_id}; "
            f"idProposicao={prop_id}; item localizado em consulta oficial paginada."
        ),
        "source_origin": {
            "institution": "Câmara dos Deputados",
            "discovery_method": "api_idDeputadoAutor_paginated_reacquisition",
            "curation_order": row.get("curation_order"),
            "chamber_id": chamber_id,
            "proposition_id": prop_id,
            "api_url": api_url,
            "api_page": api_page,
            "api_item_uri": clean(item.get("uri")),
        },
    }


def rejection(row: dict[str, Any], detail: str) -> dict[str, Any]:
    return {
        "candidate_id": clean(row.get("candidate_id")),
        "curation_order": row.get("curation_order"),
        "proposition_id": row.get("proposition_id"),
        "source_url": clean(row.get("source_url")),
        "stage": "reacquisition",
        "reason": "institutional_reacquisition_failed",
        "detail": clean(detail)[:1000],
        "status": "open",
    }


def reacquire(
    *,
    manifest: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    fetch_json: Callable[[str], Any] = discovery.request_json,
    max_pages: int = 25,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    records = manifest.get("records") or []
    valid_groups: dict[tuple[str, int], list[tuple[dict[str, Any], dict[str, Any], int, str]]] = defaultdict(list)
    rejections: list[dict[str, Any]] = []

    for row in records:
        try:
            candidate, chamber_id, prop_id, source_url = validate_record(
                row, candidates=candidates
            )
            valid_groups[(clean(row.get("candidate_id")), chamber_id)].append(
                (row, candidate, prop_id, source_url)
            )
        except Exception as exc:
            rejections.append(rejection(row, str(exc)))

    sources: list[dict[str, Any]] = []
    for (_, chamber_id), group in valid_groups.items():
        target_ids = {prop_id for _, _, prop_id, _ in group}
        found, group_error = find_target_propositions(
            chamber_id=chamber_id,
            target_ids=target_ids,
            fetch_json=fetch_json,
            max_pages=max_pages,
        )
        for row, candidate, prop_id, source_url in group:
            located = found.get(prop_id)
            if not located:
                detail = group_error or (
                    f"idProposicao={prop_id} não localizado na consulta "
                    f"oficial idDeputadoAutor={chamber_id}"
                )
                rejections.append(rejection(row, detail))
                continue
            item, api_url, api_page = located
            sources.append(
                source_from_api_item(
                    row=row,
                    candidate=candidate,
                    chamber_id=chamber_id,
                    prop_id=prop_id,
                    source_url=source_url,
                    item=item,
                    api_url=api_url,
                    api_page=api_page,
                )
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
            "version": "1.1.0",
            "semantics": (
                "Fontes exact-content reancoradas por consulta paginada da API oficial "
                "da Câmara filtrada por idDeputadoAutor. Nenhuma entrada é evidência "
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
        description="Reacquire curated Câmara sources via paginated idDeputadoAutor."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-sources", type=Path, required=True)
    parser.add_argument("--output-rejections", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--max-pages", type=int, default=25)
    args = parser.parse_args()

    manifest = read_manifest(args.manifest)
    candidates = collector.load_candidates()
    sources, rejections, metrics = reacquire(
        manifest=manifest,
        candidates=candidates,
        max_pages=max(1, args.max_pages),
    )
    write_json(args.output_sources, sources)
    write_json(args.output_rejections, rejections)
    write_json(args.metrics, metrics)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
