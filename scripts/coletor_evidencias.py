#!/usr/bin/env python3
"""Coletor auditável de evidências temáticas do Quem-Votar.

Fluxo:
  fonte permitida -> staging de fontes -> coleta bruta -> revisão semântica
  -> validação determinística -> promoção explícita -> fonte canônica

Este módulo não publica interpretação política automaticamente. Perfis sociais
declarados ao TSE entram como sementes de descoberta; somente URLs de conteúdo
específico podem gerar rascunhos de evidência.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import ipaddress
import json
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data" / "generated"
REFERENCE = ROOT / "data" / "reference"
STAGING = ROOT / "data" / "staging"

FEDERAL_FILE = GENERATED / "candidates-federal.json"
ESTADUAL_FILE = GENERATED / "candidates-estadual.json"
TOPICS_FILE = REFERENCE / "policy-topics.json"
CANONICAL_FILE = REFERENCE / "topic-evidence.json"

SOURCE_QUEUE_FILE = STAGING / "topic-evidence-sources.json"
DRAFTS_FILE = STAGING / "topic-evidence-drafts.json"
REVIEWS_FILE = STAGING / "topic-evidence-reviews.json"

TSE_SOCIAL_ZIP = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/"
    "rede_social_candidato_2026.zip"
)
TSE_DATASET = "https://dadosabertos.tse.jus.br/dataset/candidatos-2026"

ALLOWED_EVIDENCE_TYPES = {"proposta", "declaração", "atuação"}
ALLOWED_VERIFICATION_STATUS = {"verified", "dated", "secondary_source"}
ALLOWED_REVIEW_STATUS = {"pending", "approved", "rejected", "quarantine"}
ALLOWED_SOURCE_KINDS = {
    "official_candidate",
    "official_party",
    "tse_declared_social",
    "institutional",
    "secondary",
}
ALLOWED_DISCOVERY_STATUS = {"seed", "exact_content"}

MAX_FETCH_BYTES = 8 * 1024 * 1024
MAX_TSE_ZIP_BYTES = 64 * 1024 * 1024
MAX_EXCERPT_CHARS = 9000
MAX_PDF_PAGES = 250
MAX_PDF_TEXT_CHARS = 500_000
DEFAULT_TIMEOUT = 20
DEFAULT_USER_AGENT = (
    "Quem-Votar-Evidence-Collector/1.0 "
    "(civic-data-audit; https://github.com/joyceradis/Quem-Votar)"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def norm(value: Any) -> str:
    text = clean(value)
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    return text.casefold()


def read_json(path: Path) -> Any:
    if not path.exists():
        raise RuntimeError(f"arquivo ausente: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_candidates() -> dict[str, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in (FEDERAL_FILE, ESTADUAL_FILE):
        payload = read_json(path)
        if not isinstance(payload, list):
            raise RuntimeError(f"{path.relative_to(ROOT)} deve ser uma lista")
        rows.extend(payload)

    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        candidate_id = clean(row.get("tse_id"))
        if not candidate_id:
            raise RuntimeError("snapshot contém candidatura sem SQ_CANDIDATO")
        if candidate_id in by_id:
            raise RuntimeError(f"SQ_CANDIDATO duplicado no snapshot: {candidate_id}")
        by_id[candidate_id] = row
    return by_id


def load_topic_ids() -> set[str]:
    payload = read_json(TOPICS_FILE)
    return {
        clean(item.get("id"))
        for item in payload.get("topics", [])
        if clean(item.get("id"))
    }


def candidate_display_name(candidate: dict[str, Any]) -> str:
    return clean(candidate.get("ballot_name") or candidate.get("full_name"))


def _host_is_public(host: str) -> bool:
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise RuntimeError(f"host não resolvido: {host}") from exc

    if not addresses:
        raise RuntimeError(f"host sem endereço resolvido: {host}")

    for item in addresses:
        ip_text = item[4][0]
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def validate_public_https_url(url: str, *, resolve_dns: bool = False) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(clean(url))
    if parsed.scheme != "https":
        raise RuntimeError("URL precisa usar HTTPS")
    if not parsed.hostname:
        raise RuntimeError("URL sem host")
    if parsed.username or parsed.password:
        raise RuntimeError("URL com credenciais embutidas não é permitida")
    if parsed.port not in (None, 443):
        raise RuntimeError("porta não permitida para coleta")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"}:
        raise RuntimeError("host local não é permitido")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise RuntimeError("endereço privado/local não é permitido")
    if resolve_dns and not _host_is_public(host):
        raise RuntimeError("host resolve para endereço não público")
    return parsed


SOCIAL_HOSTS = {
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "x.com",
    "www.x.com",
    "twitter.com",
    "www.twitter.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "tiktok.com",
    "www.tiktok.com",
}


def is_exact_content_url(url: str, source_kind: str = "") -> bool:
    try:
        parsed = validate_public_https_url(url)
    except RuntimeError:
        return False

    path = parsed.path or "/"
    host = (parsed.hostname or "").lower()
    segments = [x for x in path.split("/") if x]

    if path in {"", "/"} and not parsed.query:
        return False

    if source_kind == "tse_declared_social" or host in SOCIAL_HOSTS:
        low = path.casefold()
        if host.endswith("instagram.com"):
            return any(token in low for token in ("/p/", "/reel/", "/tv/"))
        if host.endswith("x.com") or host.endswith("twitter.com"):
            return "/status/" in low
        if host.endswith("facebook.com"):
            return (
                "/posts/" in low
                or "/videos/" in low
                or "story.php" in low
                or "permalink.php" in low
            )
        if host.endswith("youtube.com"):
            return path == "/watch" and bool(urllib.parse.parse_qs(parsed.query).get("v"))
        if host == "youtu.be":
            return bool(segments)
        if host.endswith("tiktok.com"):
            return "/video/" in low
        return False

    return len(segments) >= 1 or bool(parsed.query)


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        validate_public_https_url(newurl, resolve_dns=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_bytes(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    max_bytes: int = MAX_FETCH_BYTES,
    user_agent: str = DEFAULT_USER_AGENT,
) -> tuple[bytes, str, str]:
    validate_public_https_url(url, resolve_dns=True)
    opener = urllib.request.build_opener(SafeRedirectHandler())
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,text/plain,application/xhtml+xml,application/zip;q=0.8,*/*;q=0.2",
        },
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            validate_public_https_url(final_url, resolve_dns=True)
            content_type = clean(response.headers.get("Content-Type")).lower()
            declared = response.headers.get("Content-Length")
            if declared and declared.isdigit() and int(declared) > max_bytes:
                raise RuntimeError(f"resposta excede limite de {max_bytes} bytes")
            body = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} ao coletar {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"falha de rede ao coletar {url}: {exc.reason}") from exc

    if len(body) > max_bytes:
        raise RuntimeError(f"resposta excede limite de {max_bytes} bytes")
    return body, final_url, content_type


class PageTextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "p", "article", "section", "li", "blockquote", "h1", "h2", "h3", "h4",
        "h5", "h6", "time", "figcaption", "div"
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._current: list[str] = []
        self.blocks: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.canonical_url = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = {k.lower(): clean(v) for k, v in attrs if k}
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (
                attrs_dict.get("property")
                or attrs_dict.get("name")
                or attrs_dict.get("itemprop")
            )
            value = attrs_dict.get("content")
            if key and value:
                self.meta[key.casefold()] = value
        elif tag == "link":
            rel = attrs_dict.get("rel", "").casefold()
            href = attrs_dict.get("href", "")
            if "canonical" in rel and href:
                self.canonical_url = href
        if tag in self.BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = clean(html.unescape(data))
        if not value:
            return
        if self._in_title:
            self.title_parts.append(value)
        self._current.append(value)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        value = clean(" ".join(self._current))
        self._current = []
        if value and (not self.blocks or value != self.blocks[-1]):
            self.blocks.append(value)


def parse_page_html(raw: bytes, content_type: str = "") -> dict[str, Any]:
    charset = "utf-8"
    match = re.search(r"charset=([a-z0-9._-]+)", content_type, re.I)
    if match:
        charset = match.group(1)
    try:
        text = raw.decode(charset, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")

    parser = PageTextExtractor()
    parser.feed(text)
    parser.close()

    title = (
        parser.meta.get("og:title")
        or parser.meta.get("twitter:title")
        or clean(" ".join(parser.title_parts))
    )
    publisher = parser.meta.get("og:site_name") or ""
    published_at = (
        parser.meta.get("article:published_time")
        or parser.meta.get("datepublished")
        or parser.meta.get("date")
        or ""
    )
    published_at = normalize_date(published_at)
    normalized_text = clean("\n".join(parser.blocks))
    return {
        "title": clean(title),
        "publisher": clean(publisher),
        "published_at": published_at,
        "canonical_url": clean(parser.canonical_url),
        "blocks": parser.blocks,
        "text": normalized_text,
    }


def parse_pdf_document(raw: bytes) -> dict[str, Any]:
    """Extrai texto de PDF textual sem OCR.

    O PDF continua sendo material bruto de staging. Esta etapa não classifica
    tema, tipo de evidência ou posição política.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "extração de PDF requer pypdf; instale requirements-evidence.txt"
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(raw), strict=False)
    except Exception as exc:
        raise RuntimeError(f"PDF inválido ou corrompido: {exc}") from exc

    if reader.is_encrypted:
        try:
            result = reader.decrypt("")
        except Exception as exc:
            raise RuntimeError("PDF criptografado não pôde ser aberto") from exc
        if not result:
            raise RuntimeError("PDF criptografado exige senha")

    try:
        page_count = len(reader.pages)
    except Exception as exc:
        raise RuntimeError(f"não foi possível ler as páginas do PDF: {exc}") from exc

    if page_count <= 0:
        raise RuntimeError("PDF sem páginas")
    if page_count > MAX_PDF_PAGES:
        raise RuntimeError(
            f"PDF excede limite de {MAX_PDF_PAGES} páginas para coleta automática"
        )

    blocks: list[str] = []
    total_chars = 0
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            if "/Contents" not in page:
                page_text = ""
            else:
                try:
                    page_text = page.extract_text(
                        extraction_mode="layout",
                        layout_mode_space_vertically=False,
                    )
                except TypeError:
                    page_text = page.extract_text()
        except Exception as exc:
            raise RuntimeError(
                f"falha ao extrair texto da página {page_number}: {exc}"
            ) from exc

        page_text = page_text or ""
        page_blocks = [clean(line) for line in page_text.splitlines() if clean(line)]
        for block in page_blocks:
            if total_chars >= MAX_PDF_TEXT_CHARS:
                break
            remaining = MAX_PDF_TEXT_CHARS - total_chars
            value = block[:remaining]
            if value:
                blocks.append(value)
                total_chars += len(value)
        if total_chars >= MAX_PDF_TEXT_CHARS:
            break

    normalized_text = clean("\n".join(blocks))
    if len(normalized_text) < 40:
        raise RuntimeError(
            "PDF sem texto suficiente para revisão; OCR não é executado automaticamente"
        )

    metadata = reader.metadata or {}
    title = clean(
        getattr(metadata, "title", "")
        or (metadata.get("/Title") if hasattr(metadata, "get") else "")
    )
    return {
        "title": title,
        "publisher": "",
        "published_at": "",
        "canonical_url": "",
        "blocks": blocks,
        "text": normalized_text,
        "page_count": page_count,
    }


def normalize_date(value: str) -> str:
    value = clean(value)
    if not value:
        return ""
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", value)
    if match:
        return match.group(1)
    return value


def source_host_label(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return (parsed.hostname or "").removeprefix("www.")


def candidate_mentioned(text: str, candidate: dict[str, Any]) -> bool:
    haystack = norm(text)
    names = {
        norm(candidate.get("ballot_name")),
        norm(candidate.get("full_name")),
        norm(candidate.get("social_name")),
    }
    names.discard("")
    for name in names:
        if len(name) >= 5 and name in haystack:
            return True
    return False


def build_excerpt(blocks: Iterable[str], candidate: dict[str, Any]) -> str:
    blocks = [clean(x) for x in blocks if clean(x)]
    if not blocks:
        return ""
    name_tokens = {
        token
        for candidate_name in (
            norm(candidate.get("ballot_name")),
            norm(candidate.get("full_name")),
            norm(candidate.get("social_name")),
        )
        for token in candidate_name.split()
        if len(token) >= 4
    }
    matching = [
        block
        for block in blocks
        if any(token in norm(block) for token in name_tokens)
    ]
    chosen = matching[:8] if matching else blocks[:12]
    excerpt = "\n\n".join(chosen)
    if len(excerpt) > MAX_EXCERPT_CHARS:
        excerpt = excerpt[:MAX_EXCERPT_CHARS].rstrip() + "…"
    return excerpt


def source_queue_envelope(sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "updated_at": utc_now(),
        "semantics": (
            "Fila de fontes para descoberta/coleta. Perfis declarados ao TSE são sementes, "
            "não evidências publicáveis."
        ),
        "sources": sources,
    }


def drafts_envelope(drafts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "updated_at": utc_now(),
        "semantics": (
            "Material bruto de staging. Nenhum registro deste arquivo é publicado na UI "
            "sem revisão e promoção explícitas."
        ),
        "drafts": drafts,
    }


def reviews_envelope(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "updated_at": utc_now(),
        "semantics": (
            "Decisões de revisão semântica sobre rascunhos. Aprovação aqui ainda precisa "
            "passar pela validação determinística antes da promoção."
        ),
        "reviews": reviews,
    }


def _decode_tse_csv(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _find_social_csv(zip_bytes: bytes) -> tuple[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = [
            name for name in archive.namelist()
            if name.lower().endswith(".csv") and not name.endswith("/")
        ]
        if not names:
            raise RuntimeError("ZIP de redes sociais do TSE não contém CSV")
        preferred = [
            name for name in names
            if "rede_social" in norm(Path(name).name).replace(" ", "_")
        ]
        chosen = preferred[0] if preferred else names[0]
        return chosen, archive.read(chosen)


def discover_tse_social_sources(
    *,
    candidates: dict[str, dict[str, Any]],
    tse_zip_url: str = TSE_SOCIAL_ZIP,
    fetcher=fetch_bytes,
) -> list[dict[str, Any]]:
    body, final_url, _ = fetcher(
        tse_zip_url,
        max_bytes=MAX_TSE_ZIP_BYTES,
    )
    _, csv_bytes = _find_social_csv(body)
    text = _decode_tse_csv(csv_bytes)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";"

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise RuntimeError("CSV do TSE sem cabeçalho")

    field_map = {norm(name): name for name in reader.fieldnames if name}
    candidate_field = (
        field_map.get("sq_candidato")
        or field_map.get("sequencial_candidato")
    )
    url_field = (
        field_map.get("ds_url")
        or field_map.get("ds_url_rede_social")
        or field_map.get("url_rede_social")
    )
    uf_field = field_map.get("sg_uf")
    order_field = field_map.get("nr_ordem")

    if not candidate_field or not url_field:
        raise RuntimeError(
            "CSV de redes sociais sem SQ_CANDIDATO/DS_URL reconhecíveis"
        )

    seen: set[tuple[str, str]] = set()
    sources: list[dict[str, Any]] = []
    for row in reader:
        if uf_field and clean(row.get(uf_field)).upper() not in {"", "ES"}:
            continue
        candidate_id = clean(row.get(candidate_field))
        seed_url = clean(row.get(url_field))
        if candidate_id not in candidates or not seed_url:
            continue
        key = (candidate_id, seed_url)
        if key in seen:
            continue
        seen.add(key)
        candidate = candidates[candidate_id]
        sources.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": candidate_display_name(candidate),
                "source_kind": "tse_declared_social",
                "discovery_status": "seed",
                "seed_url": seed_url,
                "source_url": "",
                "source_publisher": source_host_label(seed_url),
                "declared_order": clean(row.get(order_field)) if order_field else "",
                "source_origin": {
                    "institution": "TSE",
                    "dataset_url": TSE_DATASET,
                    "resource_url": final_url,
                },
            }
        )

    sources.sort(key=lambda item: (item["candidate_name"], item["seed_url"]))
    return sources


def validate_source_entry(
    item: dict[str, Any],
    *,
    candidates: dict[str, dict[str, Any]],
    resolve_dns: bool = False,
) -> None:
    candidate_id = clean(item.get("candidate_id"))
    source_kind = clean(item.get("source_kind"))
    discovery_status = clean(item.get("discovery_status"))

    if candidate_id not in candidates:
        raise RuntimeError(f"SQ_CANDIDATO inexistente: {candidate_id}")
    if source_kind not in ALLOWED_SOURCE_KINDS:
        raise RuntimeError(f"source_kind inválido: {source_kind}")
    if discovery_status not in ALLOWED_DISCOVERY_STATUS:
        raise RuntimeError(f"discovery_status inválido: {discovery_status}")

    if discovery_status == "seed":
        seed_url = clean(item.get("seed_url"))
        if not seed_url:
            raise RuntimeError("fonte seed sem seed_url")
        parsed = urllib.parse.urlparse(seed_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise RuntimeError("seed_url inválida")
        return

    source_url = clean(item.get("source_url"))
    validate_public_https_url(source_url, resolve_dns=resolve_dns)
    if not is_exact_content_url(source_url, source_kind):
        raise RuntimeError("source_url não parece apontar para conteúdo específico")


def make_draft_id(candidate_id: str, source_url: str, content_hash: str) -> str:
    raw = f"{candidate_id}\n{source_url}\n{content_hash}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def collect_source(
    item: dict[str, Any],
    *,
    candidates: dict[str, dict[str, Any]],
    fetcher=fetch_bytes,
) -> dict[str, Any]:
    validate_source_entry(item, candidates=candidates, resolve_dns=False)
    if item.get("discovery_status") != "exact_content":
        raise RuntimeError("perfil/seed não pode ser coletado como evidência")

    candidate_id = clean(item.get("candidate_id"))
    candidate = candidates[candidate_id]
    source_url = clean(item.get("source_url"))
    body, final_url, content_type = fetcher(source_url)
    final_url = clean(final_url)
    normalized_content_type = clean(content_type).casefold()
    final_path = urllib.parse.urlparse(final_url).path.casefold()
    is_pdf = "application/pdf" in normalized_content_type or final_path.endswith(".pdf")

    if is_pdf:
        page = parse_pdf_document(body)
        document_type = "pdf"
    elif "text/plain" in normalized_content_type:
        text = body.decode("utf-8", errors="replace")
        page = {
            "title": "",
            "publisher": "",
            "published_at": "",
            "canonical_url": "",
            "blocks": [clean(x) for x in text.splitlines() if clean(x)],
            "text": clean(text),
            "page_count": None,
        }
        document_type = "text"
    elif (
        "text/html" in normalized_content_type
        or "application/xhtml+xml" in normalized_content_type
        or not normalized_content_type
    ):
        page = parse_page_html(body, content_type)
        page["page_count"] = None
        document_type = "html"
    else:
        raise RuntimeError(
            f"tipo de conteúdo ainda não suportado para extração: {content_type or 'desconhecido'}"
        )

    if not is_exact_content_url(final_url, clean(item.get("source_kind"))):
        raise RuntimeError("redirecionamento terminou em URL genérica/não específica")

    normalized_text = clean(page.get("text"))
    if len(normalized_text) < 40:
        raise RuntimeError("conteúdo textual insuficiente para revisão")

    source_hash = hashlib.sha256(body).hexdigest()
    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    excerpt = build_excerpt(page.get("blocks") or [], candidate)
    source_title = clean(item.get("source_title") or page.get("title"))
    source_publisher = clean(
        item.get("source_publisher") or page.get("publisher") or source_host_label(final_url)
    )
    published_at = normalize_date(
        clean(item.get("published_at") or page.get("published_at"))
    )

    draft_id = make_draft_id(candidate_id, final_url, content_hash)
    return {
        "draft_id": draft_id,
        "candidate_id": candidate_id,
        "candidate_name": candidate_display_name(candidate),
        "office": clean(candidate.get("office")),
        "party": clean(candidate.get("party")),
        "source_kind": clean(item.get("source_kind")),
        "source_url": final_url,
        "source_title": source_title,
        "source_publisher": source_publisher,
        "published_at": published_at,
        "captured_at": utc_now(),
        "document_type": document_type,
        "page_count": page.get("page_count"),
        "source_sha256": source_hash,
        "content_sha256": content_hash,
        "candidate_mentioned": candidate_mentioned(normalized_text, candidate),
        "raw_excerpt": excerpt,
        "review_status": "pending",
        "collection_notes": clean(item.get("collection_notes")),
    }


def collect_sources(
    source_payload: dict[str, Any],
    *,
    candidates: dict[str, dict[str, Any]],
    limit: int | None = None,
    delay_seconds: float = 0.0,
    fetcher=fetch_bytes,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources = source_payload.get("sources")
    if not isinstance(sources, list):
        raise RuntimeError("staging de fontes deve conter lista 'sources'")

    drafts: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    count = 0
    for item in sources:
        if item.get("discovery_status") != "exact_content":
            continue
        if limit is not None and count >= limit:
            break
        count += 1
        try:
            draft = collect_source(item, candidates=candidates, fetcher=fetcher)
            drafts.append(draft)
        except Exception as exc:
            rejected.append(
                {
                    "candidate_id": clean(item.get("candidate_id")),
                    "source_url": clean(item.get("source_url")),
                    "error": str(exc),
                }
            )
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    deduped: dict[str, dict[str, Any]] = {item["draft_id"]: item for item in drafts}
    return list(deduped.values()), rejected


@dataclass(frozen=True)
class ReviewDecision:
    draft_id: str
    status: str
    attempts: int
    topic_id: str
    evidence_type: str
    statement: str
    quote_or_summary: str
    scope: str
    verification_status: str
    support_text: str
    attribution_basis: str
    reviewed_at: str
    reviewer: str


def parse_review(item: dict[str, Any]) -> ReviewDecision:
    try:
        attempts = int(item.get("attempts", 0))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("attempts precisa ser inteiro") from exc
    return ReviewDecision(
        draft_id=clean(item.get("draft_id")),
        status=clean(item.get("status")),
        attempts=attempts,
        topic_id=clean(item.get("topic_id")),
        evidence_type=clean(item.get("evidence_type")),
        statement=clean(item.get("statement")),
        quote_or_summary=clean(item.get("quote_or_summary")),
        scope=clean(item.get("scope")),
        verification_status=clean(item.get("verification_status")),
        support_text=clean(item.get("support_text")),
        attribution_basis=clean(item.get("attribution_basis")),
        reviewed_at=clean(item.get("reviewed_at")),
        reviewer=clean(item.get("reviewer")),
    )


def validate_review_for_promotion(
    review: ReviewDecision,
    draft: dict[str, Any],
    *,
    candidate_ids: set[str],
    topic_ids: set[str],
) -> None:
    if review.status != "approved":
        raise RuntimeError("somente review aprovada pode ser promovida")
    if not review.draft_id or review.draft_id != clean(draft.get("draft_id")):
        raise RuntimeError("draft_id da revisão não corresponde ao rascunho")
    if review.attempts < 1 or review.attempts > 3:
        raise RuntimeError("review aprovada deve registrar entre 1 e 3 tentativas")
    candidate_id = clean(draft.get("candidate_id"))
    if candidate_id not in candidate_ids:
        raise RuntimeError("SQ_CANDIDATO do rascunho não existe no snapshot")
    if review.topic_id not in topic_ids:
        raise RuntimeError(f"topic_id inválido: {review.topic_id}")
    if review.evidence_type not in ALLOWED_EVIDENCE_TYPES:
        raise RuntimeError(f"evidence_type inválido: {review.evidence_type}")
    if review.verification_status not in ALLOWED_VERIFICATION_STATUS:
        raise RuntimeError(
            f"verification_status inválido: {review.verification_status}"
        )
    if not review.scope:
        raise RuntimeError("scope obrigatório")
    if not review.statement and not review.quote_or_summary:
        raise RuntimeError("statement ou quote_or_summary obrigatório")
    if not review.support_text:
        raise RuntimeError("support_text obrigatório para ancorar a revisão na fonte")
    raw_excerpt = clean(draft.get("raw_excerpt"))
    if norm(review.support_text) not in norm(raw_excerpt):
        raise RuntimeError("support_text não foi encontrado no trecho bruto coletado")
    if not review.attribution_basis:
        raise RuntimeError("attribution_basis obrigatório")
    if not review.reviewed_at or not review.reviewer:
        raise RuntimeError("reviewed_at e reviewer obrigatórios")

    source_url = clean(draft.get("source_url"))
    source_kind = clean(draft.get("source_kind"))
    if not is_exact_content_url(source_url, source_kind):
        raise RuntimeError("fonte não é URL específica publicável")
    if not clean(draft.get("source_title")):
        raise RuntimeError("source_title ausente")
    if not clean(draft.get("source_publisher")):
        raise RuntimeError("source_publisher ausente")
    if not clean(draft.get("captured_at")):
        raise RuntimeError("captured_at ausente")
    if not clean(draft.get("content_sha256")):
        raise RuntimeError("hash do conteúdo ausente")


def canonical_record_from_review(
    review: ReviewDecision,
    draft: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_id": clean(draft.get("candidate_id")),
        "topic_id": review.topic_id,
        "evidence_type": review.evidence_type,
        "statement": review.statement,
        "quote_or_summary": review.quote_or_summary,
        "source_url": clean(draft.get("source_url")),
        "source_title": clean(draft.get("source_title")),
        "source_publisher": clean(draft.get("source_publisher")),
        "published_at": normalize_date(clean(draft.get("published_at"))),
        "captured_at": clean(draft.get("captured_at")),
        "scope": review.scope,
        "verification_status": review.verification_status,
    }


def dedupe_key(item: dict[str, Any]) -> tuple[str, ...]:
    return (
        clean(item.get("candidate_id")),
        clean(item.get("topic_id")),
        clean(item.get("evidence_type")),
        clean(item.get("source_url")),
        normalize_date(clean(item.get("published_at"))),
        clean(item.get("statement") or item.get("quote_or_summary")),
    )


def validate_canonical_record(
    item: dict[str, Any],
    *,
    candidate_ids: set[str],
    topic_ids: set[str],
) -> None:
    candidate_id = clean(item.get("candidate_id"))
    if candidate_id not in candidate_ids:
        raise RuntimeError(f"SQ_CANDIDATO inexistente: {candidate_id}")
    if clean(item.get("topic_id")) not in topic_ids:
        raise RuntimeError(f"topic_id inválido: {item.get('topic_id')}")
    if clean(item.get("evidence_type")) not in ALLOWED_EVIDENCE_TYPES:
        raise RuntimeError(f"evidence_type inválido: {item.get('evidence_type')}")
    if clean(item.get("verification_status")) not in ALLOWED_VERIFICATION_STATUS:
        raise RuntimeError(
            f"verification_status inválido: {item.get('verification_status')}"
        )
    source_url = clean(item.get("source_url"))
    if not is_exact_content_url(source_url, ""):
        raise RuntimeError("source_url precisa ser HTTPS e apontar para conteúdo específico")
    if not clean(item.get("source_title")):
        raise RuntimeError("source_title obrigatório")
    if not clean(item.get("source_publisher")):
        raise RuntimeError("source_publisher obrigatório")
    if not clean(item.get("captured_at")):
        raise RuntimeError("captured_at obrigatório")
    if not clean(item.get("scope")):
        raise RuntimeError("scope obrigatório")
    if not clean(item.get("statement")) and not clean(item.get("quote_or_summary")):
        raise RuntimeError("statement ou quote_or_summary obrigatório")


def promote_reviews(
    *,
    drafts_payload: dict[str, Any],
    reviews_payload: dict[str, Any],
    canonical_payload: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    topic_ids: set[str],
) -> tuple[dict[str, Any], dict[str, int]]:
    drafts_list = drafts_payload.get("drafts")
    reviews_list = reviews_payload.get("reviews")
    if not isinstance(drafts_list, list):
        raise RuntimeError("arquivo de drafts deve conter lista 'drafts'")
    if not isinstance(reviews_list, list):
        raise RuntimeError("arquivo de reviews deve conter lista 'reviews'")
    if not isinstance(canonical_payload, dict) or not isinstance(
        canonical_payload.get("entries"), list
    ):
        raise RuntimeError("envelope canônico de topic-evidence inválido")

    drafts_by_id = {
        clean(item.get("draft_id")): item
        for item in drafts_list
        if clean(item.get("draft_id"))
    }
    candidate_ids = set(candidates)
    existing = list(canonical_payload["entries"])
    seen = {dedupe_key(item) for item in existing}
    promoted = 0
    skipped = 0

    for raw_review in reviews_list:
        review = parse_review(raw_review)
        if review.status not in ALLOWED_REVIEW_STATUS:
            raise RuntimeError(f"status de review inválido: {review.status}")
        if review.status != "approved":
            skipped += 1
            continue
        draft = drafts_by_id.get(review.draft_id)
        if not draft:
            raise RuntimeError(f"review aponta para draft inexistente: {review.draft_id}")
        validate_review_for_promotion(
            review,
            draft,
            candidate_ids=candidate_ids,
            topic_ids=topic_ids,
        )
        record = canonical_record_from_review(review, draft)
        validate_canonical_record(
            record,
            candidate_ids=candidate_ids,
            topic_ids=topic_ids,
        )
        key = dedupe_key(record)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        existing.append(record)
        promoted += 1

    result = dict(canonical_payload)
    result["updated_at"] = datetime.now(timezone.utc).date().isoformat()
    result["entries"] = existing
    return result, {"promoted": promoted, "skipped": skipped, "total": len(existing)}


def validate_all_staging(
    *,
    source_payload: dict[str, Any],
    drafts_payload: dict[str, Any],
    reviews_payload: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    topic_ids: set[str],
) -> dict[str, int]:
    sources = source_payload.get("sources")
    drafts = drafts_payload.get("drafts")
    reviews = reviews_payload.get("reviews")
    if not isinstance(sources, list):
        raise RuntimeError("sources precisa ser lista")
    if not isinstance(drafts, list):
        raise RuntimeError("drafts precisa ser lista")
    if not isinstance(reviews, list):
        raise RuntimeError("reviews precisa ser lista")

    for item in sources:
        validate_source_entry(item, candidates=candidates, resolve_dns=False)

    draft_ids: set[str] = set()
    for draft in drafts:
        draft_id = clean(draft.get("draft_id"))
        if not draft_id:
            raise RuntimeError("draft sem draft_id")
        if draft_id in draft_ids:
            raise RuntimeError(f"draft_id duplicado: {draft_id}")
        draft_ids.add(draft_id)
        if clean(draft.get("candidate_id")) not in candidates:
            raise RuntimeError(f"draft {draft_id}: candidatura inexistente")
        if not clean(draft.get("source_url")):
            raise RuntimeError(f"draft {draft_id}: source_url ausente")
        if not clean(draft.get("content_sha256")):
            raise RuntimeError(f"draft {draft_id}: hash ausente")
        if clean(draft.get("review_status")) not in {"", "pending"}:
            raise RuntimeError(
                f"draft {draft_id}: decisão semântica deve ficar no arquivo de reviews"
            )

    approved = 0
    quarantined = 0
    for item in reviews:
        review = parse_review(item)
        if review.status not in ALLOWED_REVIEW_STATUS:
            raise RuntimeError(f"status de review inválido: {review.status}")
        if review.attempts < 0 or review.attempts > 3:
            raise RuntimeError("attempts deve ficar entre 0 e 3")
        if review.draft_id not in draft_ids:
            raise RuntimeError(f"review aponta para draft inexistente: {review.draft_id}")
        if review.status == "approved":
            draft = next(d for d in drafts if clean(d.get("draft_id")) == review.draft_id)
            validate_review_for_promotion(
                review,
                draft,
                candidate_ids=set(candidates),
                topic_ids=topic_ids,
            )
            approved += 1
        elif review.status == "quarantine":
            quarantined += 1

    return {
        "sources": len(sources),
        "drafts": len(drafts),
        "reviews": len(reviews),
        "approved": approved,
        "quarantine": quarantined,
    }


def _load_or_empty_sources(path: Path) -> dict[str, Any]:
    if not path.exists():
        return source_queue_envelope([])
    payload = read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise RuntimeError("arquivo de fontes inválido")
    return payload


def add_source(
    *,
    path: Path,
    candidates: dict[str, dict[str, Any]],
    candidate_id: str,
    url: str,
    source_kind: str,
    publisher: str,
    discovery_status: str,
) -> dict[str, Any]:
    candidate_id = clean(candidate_id)
    item = {
        "candidate_id": candidate_id,
        "candidate_name": candidate_display_name(candidates.get(candidate_id, {})),
        "source_kind": clean(source_kind),
        "discovery_status": clean(discovery_status),
        "seed_url": clean(url) if discovery_status == "seed" else "",
        "source_url": clean(url) if discovery_status == "exact_content" else "",
        "source_publisher": clean(publisher),
        "source_origin": {"institution": "manual_discovery"},
    }
    validate_source_entry(item, candidates=candidates, resolve_dns=False)

    payload = _load_or_empty_sources(path)
    sources = payload["sources"]
    key = (
        candidate_id,
        item["seed_url"] or item["source_url"],
        item["discovery_status"],
    )
    existing = {
        (
            clean(x.get("candidate_id")),
            clean(x.get("seed_url") or x.get("source_url")),
            clean(x.get("discovery_status")),
        )
        for x in sources
    }
    if key not in existing:
        sources.append(item)
    sources.sort(
        key=lambda x: (
            clean(x.get("candidate_name")),
            clean(x.get("source_url") or x.get("seed_url")),
        )
    )
    payload["updated_at"] = utc_now()
    write_json(path, payload)
    return item


def command_discover(args: argparse.Namespace) -> int:
    candidates = load_candidates()
    sources = discover_tse_social_sources(
        candidates=candidates,
        tse_zip_url=args.tse_url,
    )
    payload = source_queue_envelope(sources)
    write_json(Path(args.output), payload)
    print(
        f"OK: {len(sources)} perfis/redes declarados ao TSE em staging; "
        "nenhum foi tratado como evidência publicável."
    )
    return 0


def command_add_source(args: argparse.Namespace) -> int:
    candidates = load_candidates()
    item = add_source(
        path=Path(args.output),
        candidates=candidates,
        candidate_id=args.candidate_id,
        url=args.url,
        source_kind=args.source_kind,
        publisher=args.publisher,
        discovery_status=args.discovery_status,
    )
    print(
        "OK: fonte adicionada ao staging | "
        f"{item['candidate_id']} | {item['discovery_status']}"
    )
    return 0


def command_collect(args: argparse.Namespace) -> int:
    candidates = load_candidates()
    source_payload = read_json(Path(args.sources))
    drafts, rejected = collect_sources(
        source_payload,
        candidates=candidates,
        limit=args.limit,
        delay_seconds=args.delay,
    )

    existing_payload = (
        read_json(Path(args.output))
        if Path(args.output).exists()
        else drafts_envelope([])
    )
    existing = existing_payload.get("drafts")
    if not isinstance(existing, list):
        raise RuntimeError("arquivo de drafts existente inválido")
    by_id = {
        clean(item.get("draft_id")): item
        for item in existing + drafts
        if clean(item.get("draft_id"))
    }
    payload = drafts_envelope(list(by_id.values()))
    write_json(Path(args.output), payload)

    if rejected:
        rejection_path = Path(args.rejections)
        write_json(
            rejection_path,
            {
                "version": "1.0.0",
                "updated_at": utc_now(),
                "rejections": rejected,
            },
        )
    print(
        f"OK: {len(drafts)} rascunhos coletados; {len(rejected)} rejeições; "
        "0 publicações canônicas."
    )
    return 0 if not rejected else 2


def command_validate(args: argparse.Namespace) -> int:
    candidates = load_candidates()
    stats = validate_all_staging(
        source_payload=read_json(Path(args.sources)),
        drafts_payload=read_json(Path(args.drafts)),
        reviews_payload=read_json(Path(args.reviews)),
        candidates=candidates,
        topic_ids=load_topic_ids(),
    )
    print(
        "VALIDAÇÃO OK | "
        f"{stats['sources']} fontes | {stats['drafts']} drafts | "
        f"{stats['reviews']} reviews | {stats['approved']} aprovadas | "
        f"{stats['quarantine']} em quarentena"
    )
    return 0


def command_promote(args: argparse.Namespace) -> int:
    candidates = load_candidates()
    result, stats = promote_reviews(
        drafts_payload=read_json(Path(args.drafts)),
        reviews_payload=read_json(Path(args.reviews)),
        canonical_payload=read_json(Path(args.canonical)),
        candidates=candidates,
        topic_ids=load_topic_ids(),
    )
    print(
        f"PROMOÇÃO VALIDADA | {stats['promoted']} novas | "
        f"{stats['skipped']} ignoradas/duplicadas | {stats['total']} totais"
    )
    if args.write_canonical:
        write_json(Path(args.canonical), result)
        print(f"ESCRITO: {Path(args.canonical).relative_to(ROOT)}")
    else:
        print("DRY-RUN: fonte canônica não foi alterada. Use --write-canonical explicitamente.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coleta e validação auditável de topic_evidence."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser(
        "discover-tse-socials",
        help="Importa redes sociais declaradas ao TSE como sementes de descoberta.",
    )
    discover.add_argument("--tse-url", default=TSE_SOCIAL_ZIP)
    discover.add_argument("--output", default=str(SOURCE_QUEUE_FILE))
    discover.set_defaults(func=command_discover)

    add = sub.add_parser(
        "add-source",
        help="Adiciona uma fonte descoberta à fila de staging.",
    )
    add.add_argument("--candidate-id", required=True)
    add.add_argument("--url", required=True)
    add.add_argument("--source-kind", choices=sorted(ALLOWED_SOURCE_KINDS), required=True)
    add.add_argument(
        "--discovery-status",
        choices=sorted(ALLOWED_DISCOVERY_STATUS),
        default="exact_content",
    )
    add.add_argument("--publisher", default="")
    add.add_argument("--output", default=str(SOURCE_QUEUE_FILE))
    add.set_defaults(func=command_add_source)

    collect = sub.add_parser(
        "collect",
        help="Extrai conteúdo bruto somente de URLs específicas aprovadas para coleta.",
    )
    collect.add_argument("--sources", default=str(SOURCE_QUEUE_FILE))
    collect.add_argument("--output", default=str(DRAFTS_FILE))
    collect.add_argument(
        "--rejections",
        default=str(STAGING / "topic-evidence-rejections.json"),
    )
    collect.add_argument("--limit", type=int, default=None)
    collect.add_argument("--delay", type=float, default=0.5)
    collect.set_defaults(func=command_collect)

    validate = sub.add_parser(
        "validate",
        help="Valida staging e reviews sem publicar.",
    )
    validate.add_argument("--sources", default=str(SOURCE_QUEUE_FILE))
    validate.add_argument("--drafts", default=str(DRAFTS_FILE))
    validate.add_argument("--reviews", default=str(REVIEWS_FILE))
    validate.set_defaults(func=command_validate)

    promote = sub.add_parser(
        "promote",
        help="Valida reviews aprovadas e prepara/persiste a fonte canônica.",
    )
    promote.add_argument("--drafts", default=str(DRAFTS_FILE))
    promote.add_argument("--reviews", default=str(REVIEWS_FILE))
    promote.add_argument("--canonical", default=str(CANONICAL_FILE))
    promote.add_argument(
        "--write-canonical",
        action="store_true",
        help="Necessário para alterar topic-evidence.json; sem a flag é dry-run.",
    )
    promote.set_defaults(func=command_promote)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
