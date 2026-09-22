#!/usr/bin/env python3
"""Validation-only gates for the already materialized TSE enrichment snapshot (#86).

This script does not fetch, mutate, promote, rank, classify, or infer political
content. It compares the public snapshot against the versioned source capture
and enforces the four validation gates requested for issue #86.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data" / "generated"
BOOTSTRAP = ROOT / "data" / "reference" / "tse-enrichment-bootstrap.json"
SAMPLE_IDS = ("80002549468", "80002549069", "80002549979")
CANDIDATE_FILES = (
    GENERATED / "candidates-federal.json",
    GENERATED / "candidates-estadual.json",
)
FORBIDDEN_KEY = re.compile(
    r"(^|_)(cpf|email|titulo_eleitoral|titulo_de_eleitor|nr_titulo)(_|$)",
    re.I,
)
EMAIL_VALUE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
FORMATTED_CPF_VALUE = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in CANDIDATE_FILES:
        rows.extend(load_json(path))
    return rows


def source_maps() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    generated = {
        str(row["tse_id"]): row
        for row in load_candidates()
        if row.get("tse_id")
    }
    bootstrap = load_json(BOOTSTRAP)
    source = {
        str(row["candidate_id"]): row
        for row in bootstrap.get("entries", [])
        if row.get("candidate_id")
    }
    return generated, source


def gate_assets(
    generated: dict[str, dict[str, Any]],
    source: dict[str, dict[str, Any]],
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for cid, row in generated.items():
        expected = source.get(cid)
        if expected is None:
            failures.append(f"{cid}: ausente no bootstrap")
            continue
        assets = row.get("assets") or {}
        if assets != (expected.get("assets") or {}):
            failures.append(f"{cid}: patrimônio diverge do source capture")
            continue
        items = assets.get("items") or []
        count = int(assets.get("count") or 0)
        if count != len(items):
            failures.append(f"{cid}: count={count} != items={len(items)}")
        item_sum = round(sum(float(item.get("value_brl") or 0) for item in items), 2)
        declared = assets.get("total_declared_brl")
        if items:
            if declared is None or abs(item_sum - float(declared)) > 0.001:
                failures.append(
                    f"{cid}: soma dos itens={item_sum:.2f} != total={declared}"
                )
        elif declared is not None:
            failures.append(f"{cid}: sem itens mas total={declared}")

    details = [
        f"{cid}: total={generated[cid]['assets'].get('total_declared_brl')} "
        f"count={generated[cid]['assets'].get('count')}"
        for cid in SAMPLE_IDS
    ]
    details.append(f"universo_validado={len(generated)}")
    details.extend(f"FAIL {item}" for item in failures[:12])
    return not failures, details


def normalized_url_shape(value: str) -> str | None:
    try:
        parts = urllib.parse.urlsplit(value)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    netloc = parts.netloc.lower()
    return urllib.parse.urlunsplit(
        (parts.scheme.lower(), netloc, parts.path, parts.query, parts.fragment)
    )


def gate_social(
    generated: dict[str, dict[str, Any]],
    source: dict[str, dict[str, Any]],
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    duplicate_candidates: list[str] = []
    for cid, row in generated.items():
        expected = source.get(cid)
        links = list(row.get("social_links") or [])
        if expected is None:
            failures.append(f"{cid}: ausente no bootstrap")
            continue
        if links != list(expected.get("social_links") or []):
            failures.append(f"{cid}: links divergem do source capture")

        folded = [link.casefold() for link in links]
        if len(set(folded)) != len(folded):
            duplicate_candidates.append(cid)

        for link in links:
            normalized = normalized_url_shape(link)
            if normalized is None:
                failures.append(f"{cid}: URL inválida {link!r}")
            elif normalized != link:
                failures.append(f"{cid}: URL não normalizada {link!r}")

    if duplicate_candidates:
        failures.append(
            "duplicatas case-insensitive em: " + ", ".join(duplicate_candidates)
        )

    details = [
        f"{cid}: links={len(generated[cid].get('social_links') or [])}"
        for cid in SAMPLE_IDS
    ]
    details.append(f"duplicatas_casefold={len(duplicate_candidates)}")
    details.extend(f"FAIL {item}" for item in failures[:12])
    return not failures, details


def gate_history(
    generated: dict[str, dict[str, Any]],
    source: dict[str, dict[str, Any]],
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    missing = {"year": 0, "office": 0, "uf": 0, "party": 0, "result": 0}
    records = 0
    for cid, row in generated.items():
        expected = source.get(cid)
        history = list(row.get("previous_elections") or [])
        if expected is None:
            failures.append(f"{cid}: ausente no bootstrap")
            continue
        if history != list(expected.get("previous_elections") or []):
            failures.append(f"{cid}: histórico diverge do source capture")
        for item in history:
            records += 1
            for field in missing:
                value = item.get(field)
                if field == "year":
                    if not isinstance(value, int):
                        missing[field] += 1
                elif not value:
                    missing[field] += 1

    for field, count in missing.items():
        if count:
            failures.append(f"{count}/{records} registros sem {field}")

    details = [
        f"{cid}: registros={len(generated[cid].get('previous_elections') or [])}"
        for cid in SAMPLE_IDS
    ]
    details.append("missing=" + json.dumps(missing, sort_keys=True))
    details.extend(f"FAIL {item}" for item in failures[:12])
    return not failures, details


def walk_pii(value: Any, path: str, hits: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if FORBIDDEN_KEY.search(str(key)):
                hits.append(f"campo proibido: {child_path}")
            walk_pii(child, child_path, hits)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            walk_pii(child, f"{path}[{index}]", hits)
        return
    if isinstance(value, str):
        if EMAIL_VALUE.search(value):
            hits.append(f"e-mail em {path}")
        if FORMATTED_CPF_VALUE.search(value):
            hits.append(f"CPF formatado em {path}")


def gate_pii() -> tuple[bool, list[str]]:
    hits: list[str] = []
    scanned = 0
    for path in sorted(GENERATED.glob("*.json")):
        payload = load_json(path)
        scanned += 1
        walk_pii(payload, path.name, hits)
    details = [f"arquivos_publicos_varridos={scanned}", f"hits={len(hits)}"]
    details.extend(f"FAIL {item}" for item in hits[:12])
    return not hits, details


def meta_gate() -> tuple[bool, list[str]]:
    meta = load_json(GENERATED / "meta.json")
    enrichment = (meta.get("sources") or {}).get("tse_enrichment") or {}
    failures: list[str] = []
    for key in ("candidate_assets", "candidate_social", "candidate_history"):
        item = enrichment.get(key) or {}
        if item.get("origin_status") != "bootstrap_mirror":
            failures.append(f"{key}: origin_status != bootstrap_mirror")
        source = item.get("source") or {}
        if source.get("institution") != "TSE":
            failures.append(f"{key}: fonte factual primária não é TSE")
        if source.get("transport") != "MeuVoto static candidate pages":
            failures.append(f"{key}: transporte de contingência não declarado")
        if not source.get("aggregate_sha256"):
            failures.append(f"{key}: aggregate_sha256 ausente")
    return not failures, failures


def emit(name: str, passed: bool, details: list[str]) -> None:
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    for item in details:
        print(f"  - {item}")


def main() -> int:
    generated, source = source_maps()
    universe_ok = len(generated) == len(source) == 547
    if not universe_ok:
        print(
            f"UNIVERSE: FAIL generated={len(generated)} source={len(source)} expected=547"
        )
        return 1

    meta_ok, meta_details = meta_gate()
    print(f"META_PROVENANCE: {'PASS' if meta_ok else 'FAIL'}")
    for item in meta_details:
        print(f"  - {item}")

    gates = [
        ("GATE_A_ASSETS",) + gate_assets(generated, source),
        ("GATE_B_SOCIAL",) + gate_social(generated, source),
        ("GATE_C_HISTORY",) + gate_history(generated, source),
        ("GATE_D_PII",) + gate_pii(),
    ]
    for name, passed, details in gates:
        emit(name, passed, details)

    passed = meta_ok and all(result for _, result, _ in gates)
    print(f"OVERALL: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
