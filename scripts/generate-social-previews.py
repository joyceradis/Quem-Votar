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
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data" / "generated"
DEFAULT_OUTPUT = ROOT / "social"
DEFAULT_SITEMAP = ROOT / "sitemap.xml"
DEFAULT_SITE_BASE = "https://joyceradis.github.io/Quem-Votar/"
FALLBACK_OG_IMAGE_PATH = "assets/og-fallback-neutral.png"
ID_RE = re.compile(r"^\d+$")

# Universo público de cargos (1º turno). Todos são obrigatórios: um snapshot
# ausente derruba a geração em vez de omitir candidaturas em silêncio.
OFFICE_SNAPSHOTS: tuple[tuple[str, str], ...] = (
    ("candidates-federal.json", "federal"),
    ("candidates-estadual.json", "estadual"),
    ("candidates-governador.json", "governador"),
    ("candidates-senador.json", "senador"),
)
KINDS = frozenset(kind for _, kind in OFFICE_SNAPSHOTS)
ROLE_LABELS = {
    "federal": "Deputado Federal",
    "estadual": "Deputado Estadual",
    "governador": "Governador",
    "senador": "Senador",
}
STATIC_ROUTES = (
    "",
    "candidatos.html",
    "temas.html",
    "comparar.html",
    "sobre.html",
    "apoio.html",
)


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def is_valid_https_url(value: Any) -> bool:
    raw = clean(value)
    if not raw:
        return False
    parsed = urlsplit(raw)
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


def resolve_og_image(
    candidate: dict[str, Any],
    *,
    site_base: str,
) -> tuple[str, bool]:
    photo_url = clean(candidate.get("photo_url"))
    if is_valid_https_url(photo_url):
        return photo_url, True
    base = site_base.rstrip("/") + "/"
    return f"{base}{FALLBACK_OG_IMAGE_PATH}", False


def load_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, kind in OFFICE_SNAPSHOTS:
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
    return ROLE_LABELS.get(clean(candidate.get("_kind")), "Candidatura")


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
    if kind not in KINDS:
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
    image_url, _uses_candidate_photo = resolve_og_image(
        candidate,
        site_base=site_base,
    )

    esc = lambda value: html.escape(str(value), quote=True)
    image_alt = "Imagem de compartilhamento da candidatura"
    image_meta = (
        f'<meta property="og:image" content="{esc(image_url)}">\n'
        f'<meta property="og:image:alt" content="{esc(image_alt)}">\n'
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
<title>Quem Votar?</title>
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


def snapshot_date(meta_path: Path | None = None) -> str:
    """Data (AAAA-MM-DD) da coleta do snapshot; base determinística do lastmod."""
    meta = json.loads((meta_path or GENERATED / "meta.json").read_text(encoding="utf-8"))
    collected = clean(meta.get("collected_at"))
    if not re.match(r"^\d{4}-\d{2}-\d{2}", collected):
        raise RuntimeError("meta.json sem collected_at válido para o sitemap")
    return collected[:10]


def render_sitemap(
    candidates: list[dict[str, Any]],
    *,
    lastmod: str,
    site_base: str = DEFAULT_SITE_BASE,
) -> str:
    """Sitemap determinístico: rotas estáticas + uma ficha por SQ_CANDIDATO.

    Ordem estável (cargo na ordem do registry, depois SQ_CANDIDATO); nenhuma
    ordenação valorativa, só a ordem de geração.
    """
    base = site_base.rstrip("/") + "/"
    esc = lambda value: html.escape(str(value), quote=True)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for route in STATIC_ROUTES:
        lines.append(f"  <url><loc>{esc(base + route)}</loc><lastmod>{lastmod}</lastmod></url>")
    order = {kind: index for index, (_, kind) in enumerate(OFFICE_SNAPSHOTS)}
    for candidate in sorted(
        candidates,
        key=lambda row: (order[clean(row.get("_kind"))], clean(row.get("tse_id"))),
    ):
        _, profile = candidate_urls(candidate, site_base=site_base)
        lines.append(f"  <url><loc>{esc(profile)}</loc><lastmod>{lastmod}</lastmod></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--site-base", default=DEFAULT_SITE_BASE)
    parser.add_argument("--sitemap", type=Path, default=DEFAULT_SITEMAP)
    args = parser.parse_args()
    manifest = generate(output_dir=args.output, site_base=args.site_base)
    args.sitemap.write_text(
        render_sitemap(load_candidates(), lastmod=snapshot_date(), site_base=args.site_base),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"candidate_count": manifest["candidate_count"], "output": str(args.output)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
