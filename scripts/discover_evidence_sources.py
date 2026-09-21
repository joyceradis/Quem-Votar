#!/usr/bin/env python3
"""Batch discovery of attributable evidence sources.

This stage discovers *where* candidate-specific material exists. It does not
classify political topics, approve evidence, or write canonical data.

Flow:
  TSE-declared seeds + institutional IDs
    -> conservative URL normalization
    -> official-site link discovery / Câmara propositions
    -> seed + exact_content source queue
    -> discovery rejections for deterministic failures
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

import coletor_evidencias as collector

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXISTING = ROOT / "data/staging/topic-evidence-sources.json"

SOCIAL_MIRROR_REPO = "pedrorosemberg/eleicoes.metadax.org"
SOCIAL_MIRROR_PATH = "data/2026/redes-sociais/ES.json"
SOCIAL_MIRROR_API = f"https://api.github.com/repos/{SOCIAL_MIRROR_REPO}"
SOCIAL_MIRROR_FALLBACK_COMMIT = "f40924558a99cd1b57da1024dc9dc67ad13a9950"

CHAMBER_API = "https://dadosabertos.camara.leg.br/api/v2"
CHAMBER_PAGE = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao"

LINK_AGGREGATOR_HOSTS = {"linktr.ee"}

SOCIAL_HOST_SUFFIXES = {
    "instagram.com",
    "facebook.com",
    "threads.net",
    "threads.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "linkedin.com",
    "whatsapp.com",
}

TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "igsh", "igshid", "mibextid", "share_url",
    "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term",
}

CONTENT_HINTS = {
    "proposta", "propostas", "plano", "planos", "programa", "programas",
    "projeto", "projetos", "compromisso", "compromissos", "ideia", "ideias",
    "manifesto", "prioridade", "prioridades", "noticia", "noticias", "artigo",
    "artigos", "blog", "agenda", "mandato", "realizacoes", "realizacao",
}

GENERIC_ONLY_SEGMENTS = {
    "sobre", "contato", "home", "inicio", "quem-sou", "biografia", "perfil",
    "login", "privacidade", "termos", "imprensa", "noticias", "blog", "artigos",
    "propostas", "projetos", "programa", "agenda",
}

ARCHIVE_ROUTE_SEGMENTS = {
    "categoria", "category", "tag", "tags", "tipo", "type", "autor", "author",
    "arquivo", "archive", "arquivos", "archives", "page", "pagina",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    return collector.clean(value)


def canonicalize_url(value: str) -> str:
    value = clean(value)
    if not value:
        return ""
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""
    scheme = parsed.scheme.lower()
    host = parsed.hostname.rstrip(".").lower()
    port = parsed.port
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = []
    for key, val in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in TRACKING_QUERY_KEYS or key.lower().startswith("utm_"):
            continue
        query.append((key, val))
    query.sort()
    return urllib.parse.urlunsplit(
        (scheme, netloc, path, urllib.parse.urlencode(query, doseq=True), "")
    )


def host_of(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def is_social_host(url: str) -> bool:
    host = host_of(url)
    return any(host == suffix or host.endswith("." + suffix) for suffix in SOCIAL_HOST_SUFFIXES)


def is_link_aggregator(url: str) -> bool:
    return host_of(url) in LINK_AGGREGATOR_HOSTS


def is_blocked_aggregator_content(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = (parsed.path or "/").casefold()
    return host == "linktr.ee" and (path == "/blog" or path.startswith("/blog/"))


def normalize_declared_value(raw: str) -> tuple[str, str]:
    """Return (url, basis). Never guess a platform for an ambiguous handle."""
    raw = clean(raw)
    direct = canonicalize_url(raw)
    if direct:
        return direct, "declared_http_url"

    rules = [
        (r"^INSTAGRAM\s*:\s*@?([A-Za-z0-9._]+)\s*$", "https://www.instagram.com/{0}", "explicit_instagram_handle"),
        (r"^(?:X|TWITTER)\s*:\s*@?([A-Za-z0-9_]+)\s*$", "https://x.com/{0}", "explicit_x_handle"),
        (r"^YOUTUBE\s*:\s*@?([A-Za-z0-9._-]+)\s*$", "https://www.youtube.com/@{0}", "explicit_youtube_handle"),
        (r"^TIKTOK\s*:\s*@?([A-Za-z0-9._]+)\s*$", "https://www.tiktok.com/@{0}", "explicit_tiktok_handle"),
        (r"^LINKEDIN\s*:\s*@?([A-Za-z0-9._-]+)\s*$", "https://www.linkedin.com/in/{0}", "explicit_linkedin_handle"),
        (r"^SITE(?:/DOMINIO)?\s*:\s*([A-Za-z0-9.-]+\.[A-Za-z]{2,})(?:/)?\s*$", "https://{0}", "explicit_site_domain"),
    ]
    for pattern, template, basis in rules:
        match = re.match(pattern, raw, re.I)
        if match:
            return canonicalize_url(template.format(match.group(1))), basis
    return "", ""


def request_json(url: str) -> Any:
    body, _, _ = collector.fetch_bytes(url, max_bytes=16 * 1024 * 1024)
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"JSON inválido em {url}: {exc}") from exc


def social_rows_from_mirror() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    commit_sha = SOCIAL_MIRROR_FALLBACK_COMMIT
    try:
        query = urllib.parse.urlencode({"path": SOCIAL_MIRROR_PATH, "per_page": 1})
        commits = request_json(f"{SOCIAL_MIRROR_API}/commits?{query}")
        if isinstance(commits, list) and commits and clean(commits[0].get("sha")):
            commit_sha = clean(commits[0]["sha"])
    except Exception:
        pass

    encoded = urllib.parse.quote(commit_sha, safe="")
    blob_sha = ""
    try:
        meta = request_json(f"{SOCIAL_MIRROR_API}/contents/{SOCIAL_MIRROR_PATH}?ref={encoded}")
        blob_sha = clean(meta.get("sha"))
    except Exception:
        pass

    raw_url = (
        f"https://raw.githubusercontent.com/{SOCIAL_MIRROR_REPO}/"
        f"{commit_sha}/{SOCIAL_MIRROR_PATH}"
    )
    raw, _, _ = collector.fetch_bytes(raw_url, max_bytes=32 * 1024 * 1024)
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list):
        raise RuntimeError("espelho de redes sociais não retornou lista")
    return rows, {
        "institution": "TSE",
        "transport": "immutable_public_mirror",
        "repository": SOCIAL_MIRROR_REPO,
        "path": SOCIAL_MIRROR_PATH,
        "commit_sha": commit_sha,
        "blob_sha": blob_sha,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "official_dataset": collector.TSE_DATASET,
        "official_resource": collector.TSE_SOCIAL_ZIP,
    }


def declared_seed_sources(
    candidates: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]]
    provenance: dict[str, Any]
    try:
        official = collector.discover_tse_social_sources(candidates=candidates)
        rows = [
            {"sqCandidato": x.get("candidate_id"), "url": x.get("seed_url")}
            for x in official
        ]
        provenance = {
            "institution": "TSE",
            "transport": "official_resource",
            "official_dataset": collector.TSE_DATASET,
            "official_resource": collector.TSE_SOCIAL_ZIP,
        }
    except Exception as exc:
        rows, provenance = social_rows_from_mirror()
        provenance = {**provenance, "official_fetch_error": str(exc)[:500]}

    sources: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for row in rows:
        cid = clean(row.get("sqCandidato") or row.get("candidate_id"))
        raw = clean(row.get("url") or row.get("seed_url"))
        if cid not in candidates or not raw:
            continue
        url, basis = normalize_declared_value(raw)
        candidate = candidates[cid]
        if not url:
            rejected.append(
                rejection(
                    cid,
                    candidate,
                    "declared_seed_not_normalizable",
                    raw_value=raw,
                    detail="Valor declarado não identifica deterministicamente plataforma + URL.",
                )
            )
            continue
        key = (cid, url)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "candidate_id": cid,
                "candidate_name": collector.candidate_display_name(candidate),
                "source_kind": "tse_declared_social",
                "discovery_status": "seed",
                "seed_url": url,
                "source_url": "",
                "source_publisher": host_of(url),
                "source_origin": {
                    **provenance,
                    "raw_declared_value": raw,
                    "normalization_basis": basis,
                },
            }
        )
    return sources, rejected, provenance


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        values = {k.lower(): clean(v) for k, v in attrs if k}
        self._href = values.get("href", "")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            value = clean(data)
            if value:
                self._text.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, clean(" ".join(self._text))))
            self._href = ""
            self._text = []


def looks_like_exact_content(url: str, anchor_text: str = "") -> bool:
    parsed = urllib.parse.urlsplit(url)
    if is_link_aggregator(url) or is_blocked_aggregator_content(url):
        return False
    path = parsed.path.casefold()
    segments = [x for x in path.split("/") if x]
    if not segments:
        return False
    if re.search(r"\.(pdf|docx?|odt)$", path, re.I):
        return True

    normalized = re.sub(r"[^a-z0-9]+", " ", collector.norm(path + " " + anchor_text))
    tokens = set(normalized.split())
    hints = CONTENT_HINTS.intersection(tokens)
    if not hints:
        return False

    if len(segments) == 1 and segments[0].casefold() in GENERIC_ONLY_SEGMENTS:
        return False

    # Category/tag/archive indexes are discovery surfaces, not evidence items.
    # Keep specific article/project slugs such as /artigos/<slug>, while rejecting
    # routes such as /categoria/noticias/ and /tipo/artigos/.
    folded_segments = [segment.casefold() for segment in segments]
    if (
        len(folded_segments) >= 2
        and folded_segments[-2] in ARCHIVE_ROUTE_SEGMENTS
        and folded_segments[-1] in GENERIC_ONLY_SEGMENTS
    ):
        return False

    if len(segments) >= 2:
        return True

    single = re.sub(r"[^a-z0-9]+", " ", collector.norm(segments[0]))
    return any(hint in single for hint in CONTENT_HINTS)


def discover_site(
    seed: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    max_links: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cid = clean(seed.get("candidate_id"))
    candidate = candidates[cid]
    seed_url = canonicalize_url(clean(seed.get("seed_url")))
    if not seed_url or is_social_host(seed_url):
        return [], []
    if not seed_url.startswith("https://"):
        return [], [
            rejection(cid, candidate, "site_seed_not_https", source_url=seed_url)
        ]

    exact: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    if looks_like_exact_content(seed_url):
        exact.append(exact_source_from_site(candidate, seed, seed_url, ""))

    try:
        raw, final_url, content_type = collector.fetch_bytes(
            seed_url, timeout=12, max_bytes=3 * 1024 * 1024
        )
    except Exception as exc:
        rejected.append(
            rejection(
                cid, candidate, "site_fetch_failed", source_url=seed_url,
                detail=str(exc)[:500],
            )
        )
        return exact, rejected

    if "html" not in clean(content_type).casefold():
        return exact, rejected

    parser = LinkExtractor()
    try:
        charset = "utf-8"
        match = re.search(r"charset=([a-z0-9._-]+)", content_type, re.I)
        if match:
            charset = match.group(1)
        parser.feed(raw.decode(charset, errors="replace"))
        parser.close()
    except Exception as exc:
        rejected.append(
            rejection(
                cid, candidate, "site_html_parse_failed", source_url=seed_url,
                detail=str(exc)[:500],
            )
        )
        return exact, rejected

    final_host = host_of(final_url)

    # Linktree is a link aggregator, not a candidate-content publisher. Never
    # ingest linktr.ee/blog or other Linktree-owned pages as candidate evidence.
    # Instead, preserve external destinations as derived seeds and, when a
    # destination is already a specific content URL, emit that destination.
    if final_host in LINK_AGGREGATOR_HOSTS:
        found: list[dict[str, Any]] = []
        seen_destinations: set[str] = set()
        for href, label in parser.links:
            absolute = canonicalize_url(urllib.parse.urljoin(final_url, href))
            if not absolute or not absolute.startswith("https://"):
                continue
            if is_link_aggregator(absolute) or is_blocked_aggregator_content(absolute):
                continue
            if absolute in seen_destinations:
                continue
            seen_destinations.add(absolute)

            derived_seed = {
                "candidate_id": cid,
                "candidate_name": collector.candidate_display_name(candidate),
                "source_kind": "official_candidate",
                "discovery_status": "seed",
                "seed_url": absolute,
                "source_url": "",
                "source_publisher": host_of(absolute),
                "source_origin": {
                    "institution": "TSE-declared candidate channel",
                    "discovery_method": "link_aggregator_outbound",
                    "aggregator_url": seed_url,
                },
            }
            found.append(derived_seed)

            if looks_like_exact_content(absolute, label):
                found.append(
                    exact_source_from_site(
                        candidate,
                        derived_seed,
                        absolute,
                        label,
                        discovery_method="link_aggregator_outbound_exact",
                        aggregator_url=seed_url,
                    )
                )
            elif not is_social_host(absolute):
                nested, nested_rejected = discover_site(
                    derived_seed,
                    candidates,
                    max(1, min(max_links, 5)),
                )
                found.extend(nested)
                rejected.extend(nested_rejected)

            if len(seen_destinations) >= max_links:
                break
        return found, rejected

    seen_urls = {canonicalize_url(x.get("source_url", "")) for x in exact}
    for href, label in parser.links:
        absolute = canonicalize_url(urllib.parse.urljoin(final_url, href))
        if not absolute or not absolute.startswith("https://"):
            continue
        if host_of(absolute) != final_host:
            continue
        if is_blocked_aggregator_content(absolute):
            continue
        if absolute in seen_urls:
            continue
        if not looks_like_exact_content(absolute, label):
            continue
        seen_urls.add(absolute)
        exact.append(exact_source_from_site(candidate, seed, absolute, label))
        if len(exact) >= max_links:
            break

    return exact, rejected


def exact_source_from_site(
    candidate: dict[str, Any],
    seed: dict[str, Any],
    url: str,
    label: str,
    *,
    discovery_method: str = "same_host_content_link",
    aggregator_url: str = "",
) -> dict[str, Any]:
    return {
        "candidate_id": clean(candidate.get("tse_id")),
        "candidate_name": collector.candidate_display_name(candidate),
        "source_kind": "official_candidate",
        "discovery_status": "exact_content",
        "seed_url": clean(seed.get("seed_url")),
        "source_url": canonicalize_url(url),
        "source_title": clean(label)[:240],
        "source_publisher": host_of(url),
        "published_at": "",
        "collection_notes": (
            "URL específica descoberta deterministicamente em site declarado ao TSE. "
            "Ainda não é evidência aprovada."
        ),
        "source_origin": {
            "institution": "TSE-declared candidate channel",
            "discovery_method": discovery_method,
            "seed_url": clean(seed.get("seed_url")),
            "aggregator_url": clean(aggregator_url),
        },
    }


def discover_chamber(
    candidates: dict[str, dict[str, Any]],
    fetch_json: Callable[[str], Any] = request_json,
    min_year: int = 2023,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for cid, candidate in candidates.items():
        mandate = candidate.get("current_mandate") or {}
        chamber_id = mandate.get("chamber_id")
        if not chamber_id:
            continue
        query = urllib.parse.urlencode(
            {
                "idDeputadoAutor": chamber_id,
                "ordem": "DESC",
                "ordenarPor": "id",
                "itens": 100,
            }
        )
        api_url = f"{CHAMBER_API}/proposicoes?{query}"
        try:
            payload = fetch_json(api_url)
        except Exception as exc:
            rejected.append(
                rejection(
                    cid, candidate, "chamber_discovery_failed",
                    source_url=api_url, detail=str(exc)[:500],
                )
            )
            continue

        for item in payload.get("dados", []) if isinstance(payload, dict) else []:
            prop_id = item.get("id")
            year = item.get("ano")
            if not prop_id:
                continue
            try:
                year_int = int(year)
            except (TypeError, ValueError):
                year_int = 0
            if year_int and year_int < min_year:
                continue
            sigla = clean(item.get("siglaTipo"))
            numero = clean(item.get("numero"))
            ementa = clean(item.get("ementa"))
            title = clean(f"{sigla} {numero}/{year or ''} — {ementa}")[:300]
            page_url = canonicalize_url(f"{CHAMBER_PAGE}?idProposicao={prop_id}")
            sources.append(
                {
                    "candidate_id": cid,
                    "candidate_name": collector.candidate_display_name(candidate),
                    "source_kind": "institutional",
                    "discovery_status": "exact_content",
                    "seed_url": clean(mandate.get("profile_url")),
                    "source_url": page_url,
                    "source_title": title,
                    "source_publisher": "Câmara dos Deputados",
                    "published_at": collector.normalize_date(
                        clean(item.get("dataApresentacao"))
                    ),
                    "collection_notes": (
                        "Proposição localizada pela API oficial usando idDeputadoAutor. "
                        "A atribuição institucional deriva do identificador oficial do autor; "
                        "o conteúdo permanece sujeito à curadoria semântica."
                    ),
                    "attribution_trust": "official_author_api",
                    "attribution_basis_hint": (
                        f"Câmara dos Deputados API: idDeputadoAutor={chamber_id}; "
                        f"idProposicao={prop_id}."
                    ),
                    "source_origin": {
                        "institution": "Câmara dos Deputados",
                        "discovery_method": "api_idDeputadoAutor",
                        "chamber_id": chamber_id,
                        "proposition_id": prop_id,
                        "api_url": api_url,
                        "api_item_uri": clean(item.get("uri")),
                    },
                    "institutional_snapshot": {
                        "transport": "camara_dados_abertos",
                        "query": "idDeputadoAutor",
                        "candidate_id": cid,
                        "chamber_id": chamber_id,
                        "proposition_id": prop_id,
                        "api_url": api_url,
                        "api_item_uri": clean(item.get("uri")),
                        "siglaTipo": sigla,
                        "numero": numero,
                        "ano": year_int or clean(year),
                        "ementa": ementa,
                        "dataApresentacao": clean(item.get("dataApresentacao")),
                        "title": title,
                    },
                }
            )
    return sources, rejected


def rejection(
    cid: str,
    candidate: dict[str, Any],
    reason: str,
    *,
    source_url: str = "",
    raw_value: str = "",
    detail: str = "",
) -> dict[str, Any]:
    basis = "\n".join((cid, reason, source_url, raw_value, detail))
    return {
        "rejection_id": hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20],
        "candidate_id": cid,
        "candidate_name": collector.candidate_display_name(candidate),
        "stage": "discovery",
        "reason": reason,
        "source_url": source_url,
        "raw_value": raw_value,
        "detail": detail,
        "status": "open",
    }


def dedupe_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in items:
        cid = clean(item.get("candidate_id"))
        status = clean(item.get("discovery_status"))
        url = canonicalize_url(clean(item.get("source_url") or item.get("seed_url")))
        if not cid or not status or not url:
            continue
        item = dict(item)
        if status == "seed":
            item["seed_url"] = url
        else:
            item["source_url"] = url
        by_key[(cid, status, url)] = item
    return sorted(
        by_key.values(),
        key=lambda x: (
            clean(x.get("candidate_name")),
            clean(x.get("discovery_status")),
            clean(x.get("source_url") or x.get("seed_url")),
        ),
    )


def dedupe_rejections(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {clean(x.get("rejection_id")): x for x in items if clean(x.get("rejection_id"))}
    return sorted(
        by_id.values(),
        key=lambda x: (clean(x.get("candidate_name")), clean(x.get("reason")), clean(x.get("rejection_id"))),
    )


def run_discovery(
    *,
    candidates: dict[str, dict[str, Any]],
    existing_sources: list[dict[str, Any]],
    max_links_per_site: int = 20,
    site_workers: int = 8,
    discover_sites: bool = True,
    discover_chamber_sources: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    seeds, rejected, seed_provenance = declared_seed_sources(candidates)
    exact: list[dict[str, Any]] = []

    if discover_sites:
        site_seeds = [x for x in seeds if not is_social_host(clean(x.get("seed_url")))]
        with ThreadPoolExecutor(max_workers=max(1, site_workers)) as pool:
            futures = {
                pool.submit(discover_site, seed, candidates, max_links_per_site): seed
                for seed in site_seeds
            }
            for future in as_completed(futures):
                try:
                    found, failures = future.result()
                except Exception as exc:
                    seed = futures[future]
                    cid = clean(seed.get("candidate_id"))
                    found = []
                    failures = [
                        rejection(
                            cid, candidates[cid], "site_worker_failed",
                            source_url=clean(seed.get("seed_url")), detail=str(exc)[:500],
                        )
                    ]
                exact.extend(found)
                rejected.extend(failures)

    if discover_chamber_sources:
        chamber_sources, chamber_rejected = discover_chamber(candidates)
        exact.extend(chamber_sources)
        rejected.extend(chamber_rejected)

    merged = dedupe_sources(existing_sources + seeds + exact)
    rejected = dedupe_rejections(rejected)

    candidate_ids = set(candidates)
    with_seed = {clean(x.get("candidate_id")) for x in merged if x.get("discovery_status") == "seed"}
    with_exact = {clean(x.get("candidate_id")) for x in merged if x.get("discovery_status") == "exact_content"}

    sources_payload = {
        "version": "1.1.0",
        "updated_at": utc_now(),
        "semantics": (
            "Fila de descoberta não-canônica. seed identifica ponto de partida; "
            "exact_content identifica URL específica potencialmente coletável. "
            "Nenhuma entrada deste arquivo é evidência política aprovada."
        ),
        "discovery_run": {
            "candidate_universe": len(candidate_ids),
            "candidates_with_seed": len(with_seed & candidate_ids),
            "candidates_with_exact_content": len(with_exact & candidate_ids),
            "source_records": len(merged),
            "seed_provenance": seed_provenance,
        },
        "sources": merged,
    }
    rejections_payload = {
        "version": "1.0.0",
        "updated_at": utc_now(),
        "semantics": "Falhas/rejeições determinísticas da etapa de discovery; não são conclusões políticas.",
        "rejections": rejected,
    }
    metrics = {
        "candidate_universe": len(candidate_ids),
        "candidates_with_seed": len(with_seed & candidate_ids),
        "candidates_with_exact_content": len(with_exact & candidate_ids),
        "seed_records": sum(x.get("discovery_status") == "seed" for x in merged),
        "exact_content_records": sum(x.get("discovery_status") == "exact_content" for x in merged),
        "rejections": len(rejected),
        "source_records": len(merged),
    }
    return sources_payload, rejections_payload, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch source-first evidence discovery.")
    parser.add_argument("--existing-sources", type=Path, default=DEFAULT_EXISTING)
    parser.add_argument("--output-sources", type=Path, required=True)
    parser.add_argument("--output-rejections", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--max-links-per-site", type=int, default=20)
    parser.add_argument("--site-workers", type=int, default=8)
    parser.add_argument("--skip-sites", action="store_true")
    parser.add_argument("--skip-chamber", action="store_true")
    args = parser.parse_args()

    candidates = collector.load_candidates()
    existing_payload = collector.read_json(args.existing_sources)
    existing_sources = existing_payload.get("sources", [])
    if not isinstance(existing_sources, list):
        raise RuntimeError("existing sources payload inválido")

    sources, rejections, metrics = run_discovery(
        candidates=candidates,
        existing_sources=existing_sources,
        max_links_per_site=max(1, args.max_links_per_site),
        site_workers=max(1, args.site_workers),
        discover_sites=not args.skip_sites,
        discover_chamber_sources=not args.skip_chamber,
    )

    args.output_sources.parent.mkdir(parents=True, exist_ok=True)
    args.output_sources.write_text(
        json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output_rejections.write_text(
        json.dumps(rejections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.metrics.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
