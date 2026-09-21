#!/usr/bin/env python3
"""Generate static social-preview entry points for candidate profiles.

These files exist for crawlers that do not execute JavaScript. They contain
only factual candidate identity fields already present in the generated TSE
snapshot and redirect human visitors to the existing dynamic profile page.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data" / "generated"
DEFAULT_OUTPUT = ROOT / "social"
DEFAULT_SITE_BASE = "https://joyceradis.github.io/Quem-Votar/"
ID_RE = re.compile(r"^\d+$")


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def load_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, kind in (
        ("candidates-federal.json", "federal"),
        ("candidates-estadual.json", "estadual"),
    ):
        payload = json.loads((GENERATED / name).read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise RuntimeError(f"{name}: snapshot deve ser lista")
        for row in payload:
            item = dict(row)
            item["_kind"] = kind
            rows.append(item)
    return rows


def role_label(candidate: dict[str, Any]) -> str:
    office = clean(candidate.get("office"))
    if office:
        return office.title()
    return (
        "Deputado Federal"
        if clean(candidate.get("_kind")) == "federal"
        else "Deputado Estadual"
    )


def factual_description(candidate: dict[str, Any]) -> str:
    name = clean(candidate.get("ballot_name") or candidate.get("full_name")) or "Candidatura"
    role = role_label(candidate)
    party = clean(candidate.get("party")) or "Partido não informado"
    number = clean(candidate.get("number")) or "—"
    return (
        f"{name} · {role} · {party} · nº {number}. "
        "Consulte dados públicos e fontes no Quem Votar?"
    )


def candidate_urls(
    candidate: dict[str, Any],
    *,
    site_base: str,
) -> tuple[str, str]:
    cid = clean(candidate.get("tse_id"))
    if not ID_RE.fullmatch(cid):
        raise RuntimeError(f"SQ_CANDIDATO inválido para preview: {cid!r}")
    kind = clean(candidate.get("_kind"))
    if kind not in {"federal", "estadual"}:
        raise RuntimeError(f"{cid}: cargo/kind inválido para preview")
    base = site_base.rstrip("/") + "/"
    preview = f"{base}social/{quote(cid, safe='')}/"
    profile = (
        f"{base}candidato.html?id={quote(cid, safe='')}"
        f"&cargo={quote(kind, safe='')}"
    )
    return preview, profile


def render_preview(
    candidate: dict[str, Any],
    *,
    site_base: str = DEFAULT_SITE_BASE,
) -> str:
    cid = clean(candidate.get("tse_id"))
    name = clean(candidate.get("ballot_name") or candidate.get("full_name")) or "Candidatura"
    title = f"{name} · Quem Votar?"
    description = factual_description(candidate)
    preview_url, profile_url = candidate_urls(candidate, site_base=site_base)
    photo_url = clean(candidate.get("photo_url"))
    if photo_url and not photo_url.startswith("https://"):
        photo_url = ""

    esc = lambda value: html.escape(str(value), quote=True)
    image_meta = ""
    if photo_url:
        image_meta = (
            f'<meta property="og:image" content="{esc(photo_url)}">\n'
            f'<meta property="og:image:alt" content="Foto pública de {esc(name)}">\n'
        )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,follow,max-image-preview:large">
<meta property="og:type" content="profile">
<meta property="og:site_name" content="Quem Votar?">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(preview_url)}">
{image_meta}<link rel="canonical" href="{esc(profile_url)}">
<meta http-equiv="refresh" content="0; url={esc(profile_url)}">
<title>{esc(title)}</title>
</head>
<body></body>
</html>
"""


def generate(
    *,
    output_dir: Path = DEFAULT_OUTPUT,
    site_base: str = DEFAULT_SITE_BASE,
) -> dict[str, Any]:
    candidates = load_candidates()
    ids = [clean(row.get("tse_id")) for row in candidates]
    if not ids or len(ids) != len(set(ids)):
        raise RuntimeError("SQ_CANDIDATO ausente ou duplicado no snapshot")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for candidate in sorted(candidates, key=lambda row: clean(row.get("tse_id"))):
        cid = clean(candidate.get("tse_id"))
        target = output_dir / cid
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(
            render_preview(candidate, site_base=site_base),
            encoding="utf-8",
        )

    manifest = {
        "version": "1.0.0",
        "semantics": (
            "Static social-preview routing generated from factual candidate identity "
            "fields. No ranking, recommendation or political inference."
        ),
        "site_base": site_base.rstrip("/") + "/",
        "candidate_count": len(candidates),
        "candidate_ids": sorted(ids),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--site-base", default=DEFAULT_SITE_BASE)
    args = parser.parse_args()
    manifest = generate(output_dir=args.output, site_base=args.site_base)
    print(
        json.dumps(
            {"candidate_count": manifest["candidate_count"], "output": str(args.output)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
