#!/usr/bin/env python3
"""Bootstrap auditável das camadas TSE quando o CDN oficial bloqueia o runner.

Origem factual: Tribunal Superior Eleitoral.
Transporte de contingência: API/páginas estáticas do MeuVoto, que declara
materializar dados do TSE/DivulgaCandContas na mesma build.

Este script NÃO roda no sync periódico. Ele produz um snapshot versionado em
data/reference que depois é consumido pelo sync-data.py somente como fallback.

Modos:
- sem argumentos: recaptura o universo inteiro (deputados e cargos majoritários);
- `--merge-missing`: busca SÓ as candidaturas do universo atual que ainda não
  estão no bootstrap (hoje, Governador e Senador) e as acrescenta, sem tocar
  nas entradas já capturadas. Falha de uma candidatura nunca vira dado: ela
  fica fora do arquivo, é listada no resumo e segue como "não disponível".
"""
from __future__ import annotations

import argparse
import hashlib
import html as html_module
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data" / "generated"
OUT = ROOT / "data" / "reference" / "tse-enrichment-bootstrap.json"
BASE = "https://meuvoto.org.br/candidato/{candidate_id}.html"
UA = "Quem-Votar-ES/4.0 (+https://github.com/joyceradis/Quem-Votar)"
MAX_WORKERS = 8
RETRIES = 3
# Universo público de cargos (1º turno). Todos obrigatórios: snapshot ausente
# aborta em vez de encolher o universo em silêncio.
OFFICE_SNAPSHOT_FILES = (
    "candidates-federal.json",
    "candidates-estadual.json",
    "candidates-governador.json",
    "candidates-senador.json",
)
# Seções que a página completa do MeuVoto traz. Página sem elas tem estrutura
# inesperada: não pode virar "zero verificado". Única exceção documentada:
# "historico" é omitida de quem não tem candidatura anterior e a própria
# página declara isso na identificação (ver `declared_previous_elections`).
REQUIRED_SECTIONS = ("patrimonio", "canais", "historico")


def clean_text(value: str) -> str:
    value = re.sub(r"<small\b.*?</small>", "", value, flags=re.I | re.S)
    value = re.sub(r"<span\b.*?</span>", "", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html_module.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_brl(text: str):
    value = clean_text(text).replace("R$", "").strip()
    if not value or value == "—":
        return None
    if re.fullmatch(r"[\d.]+,\d{2}", value):
        normalized = value.replace(".", "").replace(",", ".")
    else:
        return None
    try:
        return float(Decimal(normalized).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def has_section(html: str, section_id: str) -> bool:
    return bool(
        re.search(
            rf'<h2[^>]+id=["\']{re.escape(section_id)}["\'][^>]*>',
            html,
            flags=re.I,
        )
    )


def section(html: str, section_id: str) -> str:
    match = re.search(
        rf'<h2[^>]+id=["\']{re.escape(section_id)}["\'][^>]*>.*?</h2>(.*?)(?=<h2\b|\Z)',
        html,
        flags=re.I | re.S,
    )
    return match.group(1) if match else ""


def table_rows_by_caption(block: str, caption_prefix: str):
    match = re.search(
        rf"<table\b.*?<caption\b[^>]*>\s*{re.escape(caption_prefix)}.*?</caption>"
        rf".*?<tbody>(.*?)</tbody>.*?</table>",
        block,
        flags=re.I | re.S,
    )
    if not match:
        return []
    rows = []
    for row_html in re.findall(r"<tr\b[^>]*>(.*?)</tr>", match.group(1), flags=re.I | re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row_html, flags=re.I | re.S)
        if cells:
            rows.append(cells)
    return rows


def extract_assets(html: str, official_url: str | None):
    block = section(html, "patrimonio")
    rows = table_rows_by_caption(block, "Bens declarados, do maior valor para o menor")
    items = []
    total = Decimal("0")
    for index, cells in enumerate(rows, start=1):
        if len(cells) < 3:
            continue
        value = parse_brl(cells[2])
        if value is not None:
            total += Decimal(str(value))
        items.append({
            "order": index,
            "type": clean_text(cells[0]) or None,
            "description": clean_text(cells[1]) or None,
            "value_brl": value,
        })
    return {
        "total_declared_brl": float(total.quantize(Decimal("0.01"))) if items else None,
        "count": len(items),
        "items": [
            {key: value for key, value in item.items() if value is not None}
            for item in items
        ],
        "source": {
            "institution": "TSE",
            "dataset": "Bens de candidatos - 2026",
            "official_candidate_url": official_url,
        },
    }


def normalize_social_url(value: str):
    value = html_module.unescape(value).strip()
    if not re.match(r"^https?://", value, re.I):
        return None
    try:
        parts = urllib.parse.urlsplit(value)
    except ValueError:
        return None
    if not parts.netloc:
        return None
    query_parts = []
    for component in parts.query.split("&") if parts.query else []:
        if "=" in component:
            key, raw_value = component.split("=", 1)
            query_parts.append(f"{key.lower()}={raw_value}")
        else:
            query_parts.append(component.lower())
    return urllib.parse.urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path,
            "&".join(query_parts),
            parts.fragment,
        )
    )


def extract_social_links(html: str):
    block = section(html, "canais")
    match = re.search(r'<ul\b[^>]*class=["\'][^"\']*\bcanais\b[^"\']*["\'][^>]*>(.*?)</ul>', block, re.I | re.S)
    if not match:
        return []
    links = []
    seen = set()
    for href in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\']', match.group(1), re.I):
        normalized = normalize_social_url(href)
        if not normalized:
            continue
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        links.append(normalized)
    return links


def history_uf_from_source_url(source_url: str | None):
    if not source_url:
        return None
    match = re.search(
        r"/candidato/[^/]+/([A-Z]{2})/",
        source_url,
        flags=re.I,
    )
    return match.group(1).upper() if match else None


def extract_history(html: str):
    block = section(html, "historico")
    rows = table_rows_by_caption(block, "Candidaturas anteriores desta pessoa")
    records = []
    for cells in rows:
        if len(cells) < 8:
            continue
        year_text = clean_text(cells[0])
        if not year_text.isdigit():
            continue
        office = clean_text(cells[1])
        party = clean_text(re.sub(r"<small\b.*?</small>", "", cells[2], flags=re.I | re.S))
        location = clean_text(cells[3])
        votes_text = clean_text(re.sub(r"<small\b.*?</small>", "", cells[4], flags=re.I | re.S))
        votes_digits = re.sub(r"\D", "", votes_text)
        result = clean_text(cells[6])
        source_match = re.search(r'href=["\']([^"\']+)["\']', cells[7], re.I)
        source_url = html_module.unescape(source_match.group(1)) if source_match else None
        record = {
            "year": int(year_text),
            "office": office or None,
            "party": party or None,
            "uf": history_uf_from_source_url(source_url),
            "location": location or None,
            "votes": int(votes_digits) if votes_digits else None,
            "result": result or None,
            "source_url": source_url,
        }
        records.append({key: value for key, value in record.items() if value is not None})
    return records


def declared_previous_elections(html: str):
    """Contagem de "Eleições anteriores" que a própria página declara na
    identificação (`<dt>Eleições anteriores</dt><dd>N</dd>`), ou None se a
    página não a traz. É a afirmação da fonte — não uma inferência nossa por
    ausência de seção — e só ela autoriza tratar a falta da seção `historico`
    como lista vazia (primeira disputa mapeada)."""
    match = re.search(
        r"<dt>\s*Elei(?:ç|c)(?:õ|o)es anteriores\s*</dt>\s*<dd[^>]*>\s*(\d+)\s*</dd>",
        html,
        flags=re.I,
    )
    return int(match.group(1)) if match else None


def extract_official_candidate_url(html: str):
    matches = re.findall(
        r'href=["\'](https://divulgacandcontas\.tse\.jus\.br/divulga/#/candidato/[^"\']+)["\']',
        html,
        re.I,
    )
    return html_module.unescape(matches[-1]) if matches else None


def extract_source_sync_at(html: str):
    match = re.search(r'data-quando=["\']([^"\']+)["\']', html, re.I)
    if match:
        return html_module.unescape(match.group(1)).strip()
    match = re.search(r"Sincronização:\s*([^<]+)", html, re.I)
    return clean_text(match.group(1)) if match else None


def fetch_candidate(
    candidate_id: str,
    *,
    require_sections: bool = False,
    captured_at: str | None = None,
):
    url = BASE.format(candidate_id=candidate_id)
    last_exc = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": UA, "Accept": "text/html"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
            text = raw.decode("utf-8", errors="strict")
            if f'data-salvar="{candidate_id}"' not in text:
                raise RuntimeError("página não corresponde ao SQ_CANDIDATO esperado")
            official_url = extract_official_candidate_url(text)
            if not official_url:
                raise RuntimeError("página sem vínculo explícito ao DivulgaCandContas")
            if require_sections:
                absent = [sid for sid in REQUIRED_SECTIONS if not has_section(text, sid)]
                # A página omite "historico" de quem não tem candidatura anterior
                # e diz isso ("Eleições anteriores: 0 — primeira disputa
                # mapeada"). Só com essa declaração explícita a omissão vira
                # lista vazia; sem ela (ou com contagem > 0) segue sendo
                # estrutura inesperada.
                if absent == ["historico"] and declared_previous_elections(text) == 0:
                    absent = []
                if absent:
                    raise RuntimeError(
                        "página sem as seções " + ", ".join(absent)
                        + ": estrutura inesperada, não registrar como zero"
                    )
            entry = {
                "candidate_id": candidate_id,
                "transport_url": url,
                "transport_sha256": hashlib.sha256(raw).hexdigest(),
                "source_sync_at": extract_source_sync_at(text),
                "official_candidate_url": official_url,
                "assets": extract_assets(text, official_url),
                "social_links": extract_social_links(text),
                "previous_elections": extract_history(text),
            }
            if captured_at:
                entry["captured_at"] = captured_at
            return entry
        except Exception as exc:
            last_exc = exc
            if attempt + 1 < RETRIES:
                time.sleep(0.75 * (attempt + 1))
    raise RuntimeError(f"{candidate_id}: {type(last_exc).__name__}: {last_exc}")


def current_candidate_ids():
    result = []
    for filename in OFFICE_SNAPSHOT_FILES:
        rows = json.loads((GENERATED / filename).read_text(encoding="utf-8"))
        result.extend(str(row["tse_id"]) for row in rows if row.get("tse_id"))
    return sorted(set(result))


def aggregate_sha256(entries):
    """Hash agregado por (SQ_CANDIDATO, hash dos bytes processados), na ordem
    do arquivo. Mesma fórmula da captura original: reproduzível a qualquer hora."""
    digest_input = "\n".join(
        f"{item['candidate_id']}:{item['transport_sha256']}"
        for item in sorted(entries, key=lambda item: item["candidate_id"])
    ).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()


def merge_payload(existing, new_entries):
    """Acrescenta entradas novas a um bootstrap existente.

    As entradas já capturadas passam intactas (nunca são recapturadas nem
    sobrescritas) e o `captured_at` do arquivo continua sendo o da captura mais
    antiga: uma captura nova não rejuvenesce o que foi capturado antes. Cada
    entrada nova carrega o próprio `captured_at`.
    """
    current = list(existing.get("entries") or [])
    known = {item["candidate_id"] for item in current}
    clash = sorted(known & {item["candidate_id"] for item in new_entries})
    if clash:
        raise RuntimeError(f"merge não sobrescreve entradas existentes: {clash[:8]}")
    entries = sorted([*current, *new_entries], key=lambda item: item["candidate_id"])
    source = dict(existing.get("source") or {})
    observed = set(source.get("observed_source_sync_at") or [])
    observed |= {item["source_sync_at"] for item in new_entries if item.get("source_sync_at")}
    source["observed_source_sync_at"] = sorted(observed)
    source["aggregate_sha256"] = aggregate_sha256(entries)
    source["candidate_count"] = len(entries)
    return {**existing, "source": source, "entries": entries}


def dump_payload(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def run_merge_missing(strict: bool) -> int:
    existing = json.loads(OUT.read_text(encoding="utf-8"))
    universe = current_candidate_ids()
    known = {item["candidate_id"] for item in existing.get("entries") or []}
    unknown = sorted(known - set(universe))
    if unknown:
        raise RuntimeError(f"bootstrap contém IDs fora do universo atual: {unknown[:8]}")
    todo = sorted(set(universe) - known)
    if not todo:
        print(json.dumps({"requested": 0, "fetched": [], "failed": []}, ensure_ascii=False))
        return 0

    captured_at = datetime.now(timezone.utc).isoformat()
    entries, failed = [], []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                fetch_candidate, cid, require_sections=True, captured_at=captured_at
            ): cid
            for cid in todo
        }
        for future in as_completed(futures):
            cid = futures[future]
            try:
                entries.append(future.result())
            except Exception as exc:  # falha não vira dado: fica fora do arquivo
                failed.append({"candidate_id": cid, "error": str(exc)})
    failed.sort(key=lambda item: item["candidate_id"])

    summary = {
        "requested": len(todo),
        "fetched": sorted(item["candidate_id"] for item in entries),
        "failed": failed,
        "totals_fetched": {
            "bens": sum(item["assets"]["count"] for item in entries),
            "redes": sum(len(item["social_links"]) for item in entries),
            "historico": sum(len(item["previous_elections"]) for item in entries),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if entries:
        OUT.write_text(dump_payload(merge_payload(existing, entries)), encoding="utf-8")
    return 1 if (strict and failed) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--merge-missing",
        action="store_true",
        help="busca só as candidaturas ausentes do bootstrap e as acrescenta",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="com --merge-missing, sai com erro se alguma candidatura falhar",
    )
    args = parser.parse_args(argv)
    if args.merge_missing:
        return run_merge_missing(args.strict)
    return run_full()


def run_full():
    candidate_ids = current_candidate_ids()
    entries = []
    failures = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_candidate, cid): cid for cid in candidate_ids}
        for future in as_completed(futures):
            cid = futures[future]
            try:
                entries.append(future.result())
            except Exception as exc:
                failures.append(str(exc))

    if failures:
        raise RuntimeError(
            f"bootstrap incompleto: {len(failures)}/{len(candidate_ids)} falharam: "
            + " | ".join(failures[:12])
        )

    entries.sort(key=lambda item: item["candidate_id"])
    observed_syncs = sorted({
        item["source_sync_at"] for item in entries if item.get("source_sync_at")
    })

    payload = {
        "version": "1.0.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "semantics": (
            "Snapshot factual TSE transportado por páginas estáticas do MeuVoto "
            "porque os endpoints oficiais retornam HTTP 403 ao runner. "
            "Não contém ranking, inferência ou conteúdo editorial."
        ),
        "source": {
            "institution": "TSE",
            "official_dataset": "https://dadosabertos.tse.jus.br/dataset/candidatos-2026",
            "transport": "MeuVoto static candidate pages",
            "transport_base": "https://meuvoto.org.br/candidato/",
            "transport_api_docs": "https://meuvoto.org.br/api.html",
            "observed_source_sync_at": observed_syncs,
            "aggregate_sha256": aggregate_sha256(entries),
            "candidate_count": len(entries),
        },
        "entries": entries,
    }
    OUT.write_text(dump_payload(payload), encoding="utf-8")
    print(
        "OK:",
        len(entries),
        "candidaturas;",
        sum(item["assets"]["count"] for item in entries),
        "bens;",
        sum(len(item["social_links"]) for item in entries),
        "links declarados;",
        sum(len(item["previous_elections"]) for item in entries),
        "registros históricos.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
