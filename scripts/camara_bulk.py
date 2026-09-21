#!/usr/bin/env python3
"""Bulk Câmara discovery helpers for the wartime evidence worker.

This module consumes the official daily Câmara CSV files and performs only
technical joins/provenance enrichment. It does not classify political content,
approve evidence, map Câmara themes into the public V5.5 taxonomy, or write
canonical data.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

import coletor_evidencias as collector

BULK_ROOT = "https://dadosabertos.camara.leg.br/arquivos"
CHAMBER_PAGE = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao"
MAX_BULK_BYTES = 512 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    return collector.clean(value)


def normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", clean(value).casefold())


def normalized_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        normalized_key(key): clean(value)
        for key, value in row.items()
        if key is not None
    }


def pick(row: dict[str, str], *aliases: str) -> str:
    for alias in aliases:
        value = clean(row.get(normalized_key(alias)))
        if value:
            return value
    return ""


def bulk_url(dataset: str, year: int) -> str:
    return f"{BULK_ROOT}/{dataset}/csv/{dataset}-{int(year)}.csv"


def cache_paths(cache_dir: Path, dataset: str, year: int) -> tuple[Path, Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    data = cache_dir / f"{dataset}-{int(year)}.csv"
    meta = cache_dir / f"{dataset}-{int(year)}.meta.json"
    return data, meta


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def download_bulk_csv(
    dataset: str,
    year: int,
    *,
    cache_dir: Path,
    max_bytes: int = MAX_BULK_BYTES,
    timeout: int = 180,
    retries: int = 3,
) -> tuple[Path, dict[str, Any]]:
    """Materialize one official daily CSV with auditable cache + bounded retry.

    Large yearly Câmara files can legitimately take longer than ordinary API
    calls. Retries are transport-only: they never change semantic acceptance.
    A successful file is hash-pinned before it is exposed to the join stage.
    """
    url = bulk_url(dataset, year)
    data_path, meta_path = cache_paths(cache_dir, dataset, year)

    if data_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if clean(meta.get("url")) == url and clean(meta.get("sha256")):
            actual = sha256_file(data_path)
            if actual == clean(meta.get("sha256")):
                return data_path, {**meta, "cache_hit": True}

    collector.validate_public_https_url(url, resolve_dns=True)
    opener = urllib.request.build_opener(collector.SafeRedirectHandler())
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": collector.DEFAULT_USER_AGENT,
            "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.1",
        },
    )

    last_error: Exception | None = None
    attempts = max(1, int(retries))
    for attempt in range(1, attempts + 1):
        tmp_fd, tmp_name = tempfile.mkstemp(
            prefix=f".{dataset}-{year}-",
            suffix=".part",
            dir=str(cache_dir),
        )
        os.close(tmp_fd)
        tmp_path = Path(tmp_name)
        digest = hashlib.sha256()
        size = 0
        final_url = url
        headers: dict[str, str] = {}

        try:
            with opener.open(request, timeout=max(30, int(timeout))) as response, tmp_path.open("wb") as out:
                final_url = clean(response.geturl())
                collector.validate_public_https_url(final_url, resolve_dns=True)
                declared = clean(response.headers.get("Content-Length"))
                if declared.isdigit() and int(declared) > max_bytes:
                    raise RuntimeError(
                        f"{dataset}-{year}: resposta excede limite de {max_bytes} bytes"
                    )
                headers = {
                    "etag": clean(response.headers.get("ETag")),
                    "last_modified": clean(response.headers.get("Last-Modified")),
                    "content_type": clean(response.headers.get("Content-Type")),
                }
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise RuntimeError(
                            f"{dataset}-{year}: resposta excede limite de {max_bytes} bytes"
                        )
                    digest.update(chunk)
                    out.write(chunk)

            if size <= 0:
                raise RuntimeError(f"{dataset}-{year}: arquivo vazio")

            tmp_path.replace(data_path)
            meta = {
                "dataset": dataset,
                "year": int(year),
                "url": url,
                "final_url": final_url,
                "fetched_at": utc_now(),
                "sha256": digest.hexdigest(),
                "bytes": size,
                "etag": headers.get("etag", ""),
                "last_modified": headers.get("last_modified", ""),
                "content_type": headers.get("content_type", ""),
                "cache_hit": False,
                "download_attempts": attempt,
                "download_timeout_seconds": max(30, int(timeout)),
            }
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return data_path, meta

        except urllib.error.HTTPError as exc:
            tmp_path.unlink(missing_ok=True)
            last_error = RuntimeError(f"{dataset}-{year}: HTTP {exc.code}")
            retryable = exc.code in {408, 425, 429, 500, 502, 503, 504}
            if not retryable or attempt >= attempts:
                raise last_error from exc
        except urllib.error.URLError as exc:
            tmp_path.unlink(missing_ok=True)
            last_error = RuntimeError(
                f"{dataset}-{year}: falha de rede: {exc.reason}"
            )
            if attempt >= attempts:
                raise last_error from exc
        except TimeoutError as exc:
            tmp_path.unlink(missing_ok=True)
            last_error = RuntimeError(f"{dataset}-{year}: timeout")
            if attempt >= attempts:
                raise last_error from exc
        except RuntimeError:
            tmp_path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            last_error = RuntimeError(f"{dataset}-{year}: falha de transporte: {exc}")
            if attempt >= attempts:
                raise last_error from exc

        # Bounded backoff; transport recovery only.
        time.sleep(min(15, 2 ** attempt))

    raise last_error or RuntimeError(f"{dataset}-{year}: falha de transporte")


def iter_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        sample = handle.read(65536)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        if not reader.fieldnames:
            raise RuntimeError(f"{path.name}: CSV sem cabeçalho")
        for row in reader:
            if not row:
                continue
            yield normalized_row(row)


def proposition_id_from_author(row: dict[str, str]) -> str:
    value = pick(
        row,
        "idProposicao",
        "proposicaoId",
        "id_proposicao",
    )
    if value:
        return value
    uri = pick(row, "uriProposicao", "proposicaoUri")
    match = re.search(r"/proposicoes/(\d+)", uri)
    return match.group(1) if match else ""


def proposition_id_from_theme(row: dict[str, str]) -> str:
    value = pick(
        row,
        "idProposicao",
        "proposicaoId",
        "id_proposicao",
    )
    if value:
        return value
    uri = pick(row, "uriProposicao", "proposicaoUri")
    match = re.search(r"/proposicoes/(\d+)", uri)
    return match.group(1) if match else ""


def proposition_id_from_proposition(row: dict[str, str]) -> str:
    value = pick(row, "id", "idProposicao", "proposicaoId")
    if value:
        return value
    uri = pick(row, "uri", "uriProposicao")
    match = re.search(r"/proposicoes/(\d+)", uri)
    return match.group(1) if match else ""


def deputy_id_from_author(row: dict[str, str]) -> str:
    for key in ("uriAutor", "uriDeputado", "autorUri", "uri"):
        uri = pick(row, key)
        match = re.search(r"/deputados/(\d+)", uri)
        if match:
            return match.group(1)
    return pick(row, "idDeputado", "idDeputadoAutor")


def candidate_chamber_index(
    candidates: dict[str, dict[str, Any]],
) -> dict[str, tuple[str, dict[str, Any]]]:
    result: dict[str, tuple[str, dict[str, Any]]] = {}
    for cid, candidate in candidates.items():
        mandate = candidate.get("current_mandate") or {}
        chamber_id = clean(mandate.get("chamber_id"))
        if chamber_id:
            result[chamber_id] = (clean(cid), candidate)
    return result


def collect_author_links(
    rows: Iterable[dict[str, str]],
    *,
    candidates: dict[str, dict[str, Any]],
) -> dict[str, dict[str, dict[str, str]]]:
    chamber_index = candidate_chamber_index(candidates)
    links: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)

    for row in rows:
        deputy_id = deputy_id_from_author(row)
        if deputy_id not in chamber_index:
            continue
        prop_id = proposition_id_from_author(row)
        if not prop_id:
            continue
        cid, _candidate = chamber_index[deputy_id]
        links[prop_id][cid] = {
            "chamber_id": deputy_id,
            "author_name": pick(row, "nomeAutor", "nome"),
            "author_uri": pick(row, "uriAutor", "uriDeputado", "autorUri", "uri"),
            "author_type": pick(row, "tipoAutor", "descricaoTipoAutor"),
            "author_order": pick(
                row,
                "ordemAssinatura",
                "ordem",
                "sequenciaAssinatura",
            ),
            "proponente": pick(row, "proponente", "isProponente"),
        }
    return dict(links)


def collect_propositions(
    rows: Iterable[dict[str, str]],
    target_ids: set[str],
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        prop_id = proposition_id_from_proposition(row)
        if not prop_id or prop_id not in target_ids:
            continue
        result[prop_id] = {
            "id": prop_id,
            "uri": pick(row, "uri", "uriProposicao"),
            "siglaTipo": pick(row, "siglaTipo"),
            "codTipo": pick(row, "codTipo"),
            "numero": pick(row, "numero"),
            "ano": pick(row, "ano"),
            "ementa": pick(row, "ementa"),
            "dataApresentacao": pick(row, "dataApresentacao"),
            "urlInteiroTeor": pick(row, "urlInteiroTeor"),
            "keywords": pick(row, "keywords"),
        }
    return result


def collect_themes(
    rows: Iterable[dict[str, str]],
    target_ids: set[str],
) -> dict[str, list[dict[str, str]]]:
    result: dict[str, dict[tuple[str, str], dict[str, str]]] = defaultdict(dict)
    for row in rows:
        prop_id = proposition_id_from_theme(row)
        if not prop_id or prop_id not in target_ids:
            continue
        code = pick(row, "codTema", "codigoTema", "idTema")
        name = pick(row, "tema", "nomeTema", "descricaoTema")
        if not code and not name:
            continue
        result[prop_id][(code, name)] = {
            "codTema": code,
            "tema": name,
            "relevancia": pick(row, "relevancia"),
        }
    return {
        prop_id: sorted(values.values(), key=lambda x: (x["codTema"], x["tema"]))
        for prop_id, values in result.items()
    }


def combined_snapshot_sha256(
    *,
    year: int,
    files: list[dict[str, Any]],
) -> str:
    basis = "\n".join(
        [str(int(year))]
        + [
            f"{clean(item.get('dataset'))}:{clean(item.get('sha256'))}"
            for item in sorted(files, key=lambda x: clean(x.get("dataset")))
        ]
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def build_sources(
    *,
    candidates: dict[str, dict[str, Any]],
    year: int,
    author_links: dict[str, dict[str, dict[str, str]]],
    propositions: dict[str, dict[str, str]],
    themes: dict[str, list[dict[str, str]]],
    file_provenance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    target_ids = set(author_links)
    missing = sorted(target_ids - set(propositions))
    if missing:
        raise RuntimeError(
            f"bulk Câmara {year}: {len(missing)} proposições autorais sem registro "
            f"em proposicoes-{year}.csv; amostra={missing[:5]}"
        )

    snapshot_sha = combined_snapshot_sha256(year=year, files=file_provenance)
    compact_files = [
        {
            "dataset": clean(item.get("dataset")),
            "url": clean(item.get("url")),
            "sha256": clean(item.get("sha256")),
            "bytes": item.get("bytes"),
            "fetched_at": clean(item.get("fetched_at")),
            "last_modified": clean(item.get("last_modified")),
        }
        for item in sorted(file_provenance, key=lambda x: clean(x.get("dataset")))
    ]

    sources: list[dict[str, Any]] = []
    for prop_id in sorted(target_ids, key=lambda value: int(value) if value.isdigit() else value):
        proposition = propositions[prop_id]
        sigla = clean(proposition.get("siglaTipo"))
        numero = clean(proposition.get("numero"))
        prop_year = clean(proposition.get("ano")) or str(int(year))
        ementa = clean(proposition.get("ementa"))
        title = clean(f"{sigla} {numero}/{prop_year} — {ementa}")[:300]
        page_url = f"{CHAMBER_PAGE}?idProposicao={prop_id}"
        official_themes = themes.get(prop_id, [])

        for cid, author in sorted(author_links[prop_id].items()):
            candidate = candidates[cid]
            chamber_id = clean(author.get("chamber_id"))
            mandate = candidate.get("current_mandate") or {}
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
                        clean(proposition.get("dataApresentacao"))
                    ),
                    "collection_notes": (
                        "Proposição vinculada ao deputado pelo arquivo oficial diário "
                        "proposicoesAutores da Câmara. O vínculo confirma autoria/signatário "
                        "listado; não implica autoria exclusiva nem primeiro signatário. "
                        "Temas oficiais são metadata de staging e não mapeamento automático "
                        "para a taxonomia pública V5.5."
                    ),
                    "attribution_trust": "official_author_bulk",
                    "attribution_basis_hint": (
                        f"Câmara dos Deputados bulk: chamber_id={chamber_id}; "
                        f"idProposicao={prop_id}; ano={year}."
                    ),
                    "source_origin": {
                        "institution": "Câmara dos Deputados",
                        "discovery_method": "bulk_proposicoesAutores_join",
                        "chamber_id": chamber_id,
                        "proposition_id": prop_id,
                        "bulk_year": int(year),
                        "bulk_snapshot_sha256": snapshot_sha,
                        "author_uri": clean(author.get("author_uri")),
                        "author_name": clean(author.get("author_name")),
                        "authorship_scope": "listed_author_signatory",
                        "bulk_files": compact_files,
                    },
                    "institutional_snapshot": {
                        "transport": "camara_bulk_daily",
                        "candidate_id": cid,
                        "chamber_id": chamber_id,
                        "proposition_id": prop_id,
                        "api_item_uri": clean(proposition.get("uri")),
                        "siglaTipo": sigla,
                        "codTipo": clean(proposition.get("codTipo")),
                        "numero": numero,
                        "ano": prop_year,
                        "ementa": ementa,
                        "dataApresentacao": clean(proposition.get("dataApresentacao")),
                        "urlInteiroTeor": clean(proposition.get("urlInteiroTeor")),
                        "keywords": clean(proposition.get("keywords")),
                        "official_themes": official_themes,
                        "author_match": author,
                        "bulk_year": int(year),
                        "bulk_snapshot_sha256": snapshot_sha,
                        "title": title,
                    },
                }
            )
    return sources


def discover_chamber_bulk(
    candidates: dict[str, dict[str, Any]],
    *,
    cache_dir: Path,
    years: Iterable[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_sources: list[dict[str, Any]] = []
    all_files: list[dict[str, Any]] = []
    year_reports: list[dict[str, Any]] = []
    failed_years: list[dict[str, Any]] = []

    # Prefer freshest legislative years first. A slow historical year must not
    # erase already acquired current-year evidence.
    for year_value in sorted({int(value) for value in years}, reverse=True):
        try:
            authors_path, authors_meta = download_bulk_csv(
                "proposicoesAutores",
                year_value,
                cache_dir=cache_dir,
            )
            author_links = collect_author_links(
                iter_csv(authors_path),
                candidates=candidates,
            )
            target_ids = set(author_links)

            if not target_ids:
                all_files.append(authors_meta)
                year_reports.append(
                    {
                        "year": year_value,
                        "status": "ok",
                        "matched_propositions": 0,
                        "source_records": 0,
                        "theme_links": 0,
                    }
                )
                continue

            propositions_path, propositions_meta = download_bulk_csv(
                "proposicoes",
                year_value,
                cache_dir=cache_dir,
            )
            themes_path, themes_meta = download_bulk_csv(
                "proposicoesTemas",
                year_value,
                cache_dir=cache_dir,
            )

            propositions = collect_propositions(
                iter_csv(propositions_path),
                target_ids,
            )
            themes = collect_themes(
                iter_csv(themes_path),
                target_ids,
            )
            file_provenance = [authors_meta, propositions_meta, themes_meta]
            sources = build_sources(
                candidates=candidates,
                year=year_value,
                author_links=author_links,
                propositions=propositions,
                themes=themes,
                file_provenance=file_provenance,
            )

            all_files.extend(file_provenance)
            all_sources.extend(sources)
            year_reports.append(
                {
                    "year": year_value,
                    "status": "ok",
                    "matched_propositions": len(target_ids),
                    "source_records": len(sources),
                    "theme_links": sum(len(x) for x in themes.values()),
                }
            )
        except Exception as exc:
            failure = {
                "year": year_value,
                "status": "transport_failed",
                "error": str(exc)[:1000],
            }
            failed_years.append(failure)
            year_reports.append(
                {
                    **failure,
                    "matched_propositions": 0,
                    "source_records": 0,
                    "theme_links": 0,
                }
            )
            # Continue to other years. Partial coverage is explicit in report
            # and never promoted as completeness.
            continue

    has_chamber_candidates = any(
        clean((candidate.get("current_mandate") or {}).get("chamber_id"))
        for candidate in candidates.values()
    )
    if has_chamber_candidates and not all_sources:
        detail = "; ".join(
            f"{item['year']}: {item['error']}" for item in failed_years
        ) or "nenhum vínculo encontrado nos anos consultados"
        raise RuntimeError(f"bulk Câmara sem ano utilizável: {detail}")

    unique_candidates = {
        clean(item.get("candidate_id"))
        for item in all_sources
        if clean(item.get("candidate_id"))
    }
    unique_props = {
        clean((item.get("source_origin") or {}).get("proposition_id"))
        for item in all_sources
        if clean((item.get("source_origin") or {}).get("proposition_id"))
    }
    report = {
        "mode": (
            "camara_bulk_daily_partial"
            if failed_years
            else "camara_bulk_daily"
        ),
        "generated_at": utc_now(),
        "years": [x["year"] for x in year_reports],
        "successful_years": [
            x["year"] for x in year_reports if x.get("status") == "ok"
        ],
        "failed_years": failed_years,
        "coverage_complete_for_requested_years": not failed_years,
        "source_records": len(all_sources),
        "candidates_with_sources": len(unique_candidates),
        "unique_propositions": len(unique_props),
        "theme_links": sum(
            x["theme_links"]
            for x in year_reports
            if x.get("status") == "ok"
        ),
        "year_reports": year_reports,
        "files": [
            {
                key: value
                for key, value in item.items()
                if key
                in {
                    "dataset",
                    "year",
                    "url",
                    "final_url",
                    "fetched_at",
                    "sha256",
                    "bytes",
                    "etag",
                    "last_modified",
                    "cache_hit",
                    "download_attempts",
                    "download_timeout_seconds",
                }
            }
            for item in all_files
        ],
        "semantics": (
            "Official Câmara daily bulk transport. Authorship and official themes are "
            "staging metadata only; no political interpretation, V5.5 topic mapping, "
            "review approval, or canonical publication occurs here. Failed yearly "
            "transports are explicit and do not erase successfully acquired years."
        ),
    }
    return all_sources, report

