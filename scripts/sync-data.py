#!/usr/bin/env python3
"""Sincronização do Quem-Votar ES 2026.

Fonte primária: TSE Dados Abertos.
Transporte operacional: quando o CDN do TSE bloqueia o GitHub Actions,
usa-se um espelho público que processa diariamente o arquivo oficial
consulta_cand_2026.zip. O espelho é registrado no metadata e nunca é
apresentado como fonte primária.

Histórico institucional federal: Câmara dos Deputados / Dados Abertos.
A plataforma não gera ranking, score ou recomendação.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "generated"
OUT.mkdir(parents=True, exist_ok=True)

UF = "ES"
YEAR = 2026
UA = "Quem-Votar-ES/3.0 (+https://github.com/joyceradis/Quem-Votar-)"

TSE_DATASET = "https://dadosabertos.tse.jus.br/dataset/candidatos-2026"
TSE_CAND_ZIP = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip"
TSE_COMPLEMENT_ZIP = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand_complementar/consulta_cand_complementar_2026.zip"
TSE_ASSETS_ZIP = "https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2026.zip"
TSE_SOCIAL_ZIP = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/rede_social_candidato_2026.zip"
TSE_HISTORY_ZIP = "https://cdn.tse.jus.br/estatistica/sead/odsele/historico_candidatura/historico_candidatura_2026.zip"
TSE_PHOTO_ZIP = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/fotos/foto_cand2026_ES_div.zip"
PHOTO_MIRROR_BASE = "https://realidadebrasil.com.br/media/photos"
DIVULGACAND = "https://divulgacandcontas.tse.jus.br/divulga/"
CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
ALES = "https://www.al.es.gov.br/"
ALES_REFERENCE_FILE = ROOT / "data" / "reference" / "ales-20a-legislatura-2025.json"
TOPIC_REFERENCE_FILE = ROOT / "data" / "reference" / "policy-topics.json"
TOPIC_EVIDENCE_FILE = ROOT / "data" / "reference" / "topic-evidence.json"

MIRROR_REPO = "herminiotorres/dossie-cidadao"
MIRROR_PATH_BASE = "docs/data/tse/candidatos/ES"
MIRROR_API = f"https://api.github.com/repos/{MIRROR_REPO}"

MIRROR_FILES = {
    "federal": ("deputado-federal.json", "DEPUTADO FEDERAL"),
    "estadual": ("deputado-estadual.json", "DEPUTADO ESTADUAL"),
}


def request_json(url: str, timeout: int = 20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json, */*",
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def clean(value):
    if value is None:
        return None
    value = str(value).strip()
    if value in {"", "#NULO", "#NE", "-1", "-3", "NÃO DIVULGÁVEL"}:
        return None
    return value


def number(value):
    value = clean(value)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return value


def norm(value):
    value = unicodedata.normalize("NFD", str(value or ""))
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = re.sub(r"[^A-Za-z0-9 ]+", " ", value)
    value = re.sub(
        r"\b(DR|DRA|DELEGADO|DELEGADA|ENG|ENGENHEIRO|ENGENHEIRA|CAPITAO|CORONEL)\b",
        " ",
        value.upper(),
    )
    return re.sub(r"\s+", " ", value).strip()


def request_bytes(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/octet-stream, application/json, */*",
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()



def _decode_tse_csv(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise RuntimeError("CSV TSE com codificação não reconhecida")


def _pick_archive_member(names, preferred_suffix: str | None = None):
    csv_names = [
        name for name in names
        if name.lower().endswith((".csv", ".txt")) and not name.endswith("/")
    ]
    if preferred_suffix:
        preferred = [
            name for name in csv_names
            if Path(name).name.lower().endswith(preferred_suffix.lower())
        ]
        if len(preferred) == 1:
            return preferred[0]
        if len(preferred) > 1:
            raise RuntimeError(
                f"arquivo TSE ambíguo para {preferred_suffix}: "
                + ", ".join(sorted(preferred)[:8])
            )
    es_candidates = [
        name for name in csv_names
        if re.search(r"_ES\.(csv|txt)$", Path(name).name, re.I)
    ]
    if len(es_candidates) == 1:
        return es_candidates[0]
    if len(csv_names) == 1:
        return csv_names[0]
    raise RuntimeError(
        "não foi possível identificar partição ES no ZIP TSE; membros: "
        + ", ".join(sorted(csv_names)[:12])
    )


def read_tse_archive(url: str, preferred_suffix: str | None = None, timeout: int = 90):
    raw = request_bytes(url, timeout=timeout)
    if len(raw) > 150 * 1024 * 1024:
        raise RuntimeError(f"arquivo TSE excede limite operacional: {len(raw)} bytes")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"resposta TSE não é ZIP válido: {url}") from exc

    member = _pick_archive_member(archive.namelist(), preferred_suffix)
    info = archive.getinfo(member)
    if info.file_size > 80 * 1024 * 1024:
        raise RuntimeError(f"CSV TSE excede limite operacional: {member}")
    text = _decode_tse_csv(archive.read(member))
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = list(reader)
    if not rows or not reader.fieldnames:
        raise RuntimeError(f"recurso TSE vazio: {member}")

    first = rows[0]
    generated_at = " ".join(
        value for value in (
            clean(first.get("DT_GERACAO")),
            clean(first.get("HH_GERACAO")),
        )
        if value
    ) or None
    return rows, {
        "institution": "TSE",
        "url": url,
        "archive_member": member,
        "sha256": digest,
        "generated_at": generated_at,
        "row_count": len(rows),
        "status": "fresh",
    }


def parse_brl(value):
    value = clean(value)
    if value is None:
        return None
    normalized = str(value).replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def decimal_json(value: Decimal | None):
    if value is None:
        return None
    return float(value.quantize(Decimal("0.01")))


def _safe_url(value):
    value = clean(value)
    if not value:
        return None
    if not re.match(r"^https?://", value, re.I):
        return None
    parts = urllib.parse.urlsplit(value)
    if not parts.netloc:
        return None
    scheme = parts.scheme.lower()
    host = parts.netloc.lower()
    return urllib.parse.urlunsplit((scheme, host, parts.path, parts.query, parts.fragment))


def _previous_candidate_map():
    rows = []
    rows.extend(read_existing_json("candidates-federal.json", []))
    rows.extend(read_existing_json("candidates-estadual.json", []))
    return {
        str(row.get("tse_id")): row
        for row in rows
        if row.get("tse_id")
    }


def _restore_field_from_previous(candidates, previous, field):
    restored = 0
    for candidate in candidates:
        old = previous.get(str(candidate.get("tse_id"))) or {}
        if field in old:
            candidate[field] = old.get(field)
            restored += 1
    return restored


def _require_known_candidate_rows(rows, by_id, dataset, candidate_field="SQ_CANDIDATO"):
    matched = sum(
        1 for row in rows
        if clean(row.get(candidate_field)) in by_id
    )
    if matched == 0:
        raise RuntimeError(
            f"{dataset}: nenhuma linha vinculável aos {len(by_id)} SQ_CANDIDATO atuais "
            f"pelo campo {candidate_field}"
        )
    return matched


def _history_join_field(rows, candidate_ids):
    if not rows:
        raise RuntimeError("Histórico TSE vazio")
    fields = list(rows[0].keys())
    candidates = [
        field for field in fields
        if "CANDIDATO" in field.upper() and (
            field.upper().startswith("SQ_") or "SQ_CANDIDATO" in field.upper()
        )
    ]
    scored = []
    for field in candidates:
        matches = sum(
            1 for row in rows
            if clean(row.get(field)) in candidate_ids
        )
        scored.append((matches, field))
    scored.sort(reverse=True)
    if not scored or scored[0][0] == 0:
        raise RuntimeError(
            "Histórico TSE sem chave de vínculo compatível com SQ_CANDIDATO atual; "
            f"campos candidatos={candidates}; campos disponíveis={fields}"
        )
    return scored[0][1]


def enrich_tse_open_data(groups):
    candidates = [item for group in groups for item in group]
    by_id = {
        str(candidate.get("tse_id")): candidate
        for candidate in candidates
        if candidate.get("tse_id")
    }
    previous = _previous_candidate_map()
    source_meta = {}

    for candidate in candidates:
        candidate["social_links"] = []
        candidate["previous_elections"] = []
        candidate["tse_additional"] = {}
        candidate["assets"] = {
            "total_declared_brl": None,
            "count": 0,
            "items": [],
            "source": None,
        }

    def load_dataset(key, url, suffix):
        try:
            rows, meta = read_tse_archive(url, preferred_suffix=suffix)
            source_meta[key] = meta
            return rows
        except Exception as exc:
            source_meta[key] = {
                "institution": "TSE",
                "url": url,
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(f"[aviso] TSE {key} indisponível: {exc}")
            return None

    complement = load_dataset(
        "candidate_complement",
        TSE_COMPLEMENT_ZIP,
        f"consulta_cand_complementar_{YEAR}_{UF}.csv",
    )
    if complement is not None:
        _require_known_candidate_rows(complement, by_id, "complementares")
        for row in complement:
            candidate = by_id.get(clean(row.get("SQ_CANDIDATO")))
            if not candidate:
                continue
            judgment = (
                clean(row.get("DS_SITUACAO_JULGAMENTO"))
                or clean(row.get("DS_SITUACAO_CANDIDATO_PLEITO"))
                or clean(row.get("DS_DETALHE_SITUACAO_CAND"))
            )
            if judgment:
                candidate["registration_status"] = judgment
            declares = clean(row.get("ST_DECLARAR_BENS"))
            additional = {
                "registration_judgment": judgment,
                "accepted_at": clean(row.get("DT_ACEITE_CANDIDATURA")),
                "declares_assets": (
                    True if declares == "S" else False if declares == "N" else None
                ),
            }
            candidate["tse_additional"] = {
                key: value for key, value in additional.items()
                if value is not None
            }
    else:
        restored = _restore_field_from_previous(candidates, previous, "tse_additional")
        for candidate in candidates:
            old = previous.get(str(candidate.get("tse_id"))) or {}
            if old.get("registration_status"):
                candidate["registration_status"] = old.get("registration_status")
        if restored:
            source_meta["candidate_complement"]["status"] = "stale_preserved"
        else:
            raise RuntimeError(
                "Complementares TSE indisponíveis e sem snapshot anterior validado"
            )

    assets_rows = load_dataset(
        "candidate_assets",
        TSE_ASSETS_ZIP,
        f"bem_candidato_{YEAR}_{UF}.csv",
    )
    if assets_rows is not None:
        _require_known_candidate_rows(assets_rows, by_id, "bens")
        grouped = defaultdict(list)
        for row in assets_rows:
            candidate_id = clean(row.get("SQ_CANDIDATO"))
            if candidate_id in by_id:
                grouped[candidate_id].append(row)
        for candidate_id, rows in grouped.items():
            items = []
            total = Decimal("0")
            for row in sorted(
                rows,
                key=lambda item: number(item.get("NR_ORDEM_BEM_CANDIDATO")) or 0,
            ):
                value = parse_brl(row.get("VR_BEM_CANDIDATO"))
                if value is not None:
                    total += value
                item = {
                    "order": number(row.get("NR_ORDEM_BEM_CANDIDATO")),
                    "type": clean(row.get("DS_TIPO_BEM_CANDIDATO")),
                    "description": clean(row.get("DS_BEM_CANDIDATO")),
                    "value_brl": decimal_json(value),
                    "updated_at": clean(row.get("DT_ULT_ATUAL_BEM_CANDIDATO")),
                }
                items.append({
                    key: value for key, value in item.items()
                    if value is not None
                })
            by_id[candidate_id]["assets"] = {
                "total_declared_brl": decimal_json(total),
                "count": len(items),
                "items": items,
                "source": {
                    "institution": "TSE",
                    "dataset": "Bens de candidatos - 2026",
                    "url": TSE_ASSETS_ZIP,
                },
            }
    else:
        restored = _restore_field_from_previous(candidates, previous, "assets")
        if restored:
            source_meta["candidate_assets"]["status"] = "stale_preserved"
        else:
            raise RuntimeError("Bens TSE indisponíveis e sem snapshot anterior validado")

    social_rows = load_dataset(
        "candidate_social",
        TSE_SOCIAL_ZIP,
        f"rede_social_candidato_{YEAR}_{UF}.csv",
    )
    if social_rows is not None:
        _require_known_candidate_rows(social_rows, by_id, "redes sociais")
        grouped = defaultdict(list)
        for row in social_rows:
            candidate_id = clean(row.get("SQ_CANDIDATO"))
            url = _safe_url(row.get("DS_URL"))
            if candidate_id in by_id and url:
                grouped[candidate_id].append(url)
        for candidate_id, urls in grouped.items():
            seen = set()
            normalized = []
            for url in urls:
                if url in seen:
                    continue
                seen.add(url)
                normalized.append(url)
            by_id[candidate_id]["social_links"] = normalized
    else:
        restored = _restore_field_from_previous(candidates, previous, "social_links")
        if restored:
            source_meta["candidate_social"]["status"] = "stale_preserved"
        else:
            raise RuntimeError(
                "Redes sociais TSE indisponíveis e sem snapshot anterior validado"
            )

    history_rows = load_dataset(
        "candidate_history",
        TSE_HISTORY_ZIP,
        None,
    )
    if history_rows is not None:
        join_field = _history_join_field(history_rows, set(by_id))
        source_meta["candidate_history"]["join_field"] = join_field
        grouped = defaultdict(list)
        for row in history_rows:
            candidate_id = clean(row.get(join_field))
            if candidate_id not in by_id:
                continue
            year = number(row.get("ANO_ELEICAO") or row.get("AA_ELEICAO"))
            if not isinstance(year, int) or year >= YEAR:
                continue
            record = {
                "year": year,
                "office": clean(
                    row.get("DS_CARGO")
                    or row.get("DS_CARGO_CANDIDATURA")
                    or row.get("DS_CARGO_ANTERIOR")
                ),
                "party": clean(
                    row.get("SG_PARTIDO")
                    or row.get("SG_PARTIDO_CANDIDATURA")
                    or row.get("SG_PARTIDO_ANTERIOR")
                ),
                "uf": clean(
                    row.get("SG_UF")
                    or row.get("SG_UE")
                    or row.get("SG_UF_CANDIDATURA")
                ),
                "result": clean(
                    row.get("DS_SIT_TOT_TURNO")
                    or row.get("DS_SITUACAO_CANDIDATURA")
                    or row.get("DS_RESULTADO")
                ),
            }
            record = {
                key: value for key, value in record.items()
                if value is not None
            }
            grouped[candidate_id].append(record)

        if not grouped:
            raise RuntimeError(
                f"Histórico TSE: chave {join_field} vinculou candidatos atuais, "
                "mas nenhum registro anterior a 2026 foi produzido"
            )

        for candidate_id, rows in grouped.items():
            seen = set()
            records = []
            for record in sorted(
                rows,
                key=lambda item: (
                    -(item.get("year") or 0),
                    item.get("office") or "",
                    item.get("party") or "",
                ),
            ):
                key = (
                    record.get("year"),
                    record.get("office"),
                    record.get("party"),
                    record.get("uf"),
                    record.get("result"),
                )
                if key in seen:
                    continue
                seen.add(key)
                records.append(record)
            by_id[candidate_id]["previous_elections"] = records
    else:
        restored = _restore_field_from_previous(candidates, previous, "previous_elections")
        if restored:
            source_meta["candidate_history"]["status"] = "stale_preserved"
        else:
            raise RuntimeError(
                "Histórico TSE indisponível e sem snapshot anterior validado"
            )

    counts = {
        "candidates_with_assets": sum(
            1 for candidate in candidates
            if (candidate.get("assets") or {}).get("count", 0) > 0
        ),
        "asset_records": sum(
            (candidate.get("assets") or {}).get("count", 0)
            for candidate in candidates
        ),
        "candidates_with_social_links": sum(
            1 for candidate in candidates if candidate.get("social_links")
        ),
        "social_links": sum(
            len(candidate.get("social_links") or [])
            for candidate in candidates
        ),
        "candidates_with_previous_elections": sum(
            1 for candidate in candidates if candidate.get("previous_elections")
        ),
        "previous_election_records": sum(
            len(candidate.get("previous_elections") or [])
            for candidate in candidates
        ),
        "candidates_with_registration_status": sum(
            1 for candidate in candidates if candidate.get("registration_status")
        ),
    }
    return source_meta, counts


def mirror_snapshot(filename: str):
    """Resolve uma revisão imutável e lê exatamente os bytes dessa revisão."""
    path = f"{MIRROR_PATH_BASE}/{filename}"
    query = urllib.parse.urlencode({"path": path, "per_page": 1})
    commits = request_json(f"{MIRROR_API}/commits?{query}")
    if not isinstance(commits, list) or not commits:
        raise RuntimeError(f"Não foi possível resolver revisão do espelho: {path}")
    commit_sha = clean(commits[0].get("sha"))
    if not commit_sha:
        raise RuntimeError(f"Commit do espelho ausente: {path}")
    encoded_ref = urllib.parse.quote(commit_sha, safe="")
    meta = request_json(f"{MIRROR_API}/contents/{path}?ref={encoded_ref}")
    blob_sha = clean(meta.get("sha"))
    if not blob_sha:
        raise RuntimeError(f"Blob SHA do espelho ausente: {path}")
    raw_url = f"https://raw.githubusercontent.com/{MIRROR_REPO}/{commit_sha}/{path}"
    raw = request_bytes(raw_url)
    content_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        rows = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"JSON inválido no espelho imutável {path}: {exc}") from exc
    if not isinstance(rows, list):
        raise RuntimeError(f"Espelho inválido: {raw_url}")
    return rows, {
        "repository": MIRROR_REPO,
        "path": path,
        "commit_sha": commit_sha,
        "blob_sha": blob_sha,
        "content_sha256": content_sha256,
        "html_url": f"https://github.com/{MIRROR_REPO}/blob/{commit_sha}/{path}",
        "raw_url": raw_url,
    }


def normalize_candidate(row, office, mirror_info):
    return {
        "tse_id": clean(row.get("SQ_CANDIDATO")),
        "ballot_name": clean(row.get("NM_URNA_CANDIDATO")),
        "full_name": clean(row.get("NM_CANDIDATO")),
        "social_name": clean(row.get("NM_SOCIAL_CANDIDATO")),
        "number": number(row.get("NR_CANDIDATO")),
        "office": office,
        "uf": UF,
        "party": clean(row.get("SG_PARTIDO")),
        "party_name": clean(row.get("NM_PARTIDO")),
        "coalition": clean(row.get("NM_COLIGACAO")),
        "coalition_composition": clean(row.get("DS_COMPOSICAO_COLIGACAO")),
        # O espelho básico contém #NE neste campo para todo o ES.
        # Isso NÃO é convertido em um status jurídico inventado.
        "registration_status": clean(row.get("DS_SITUACAO_CANDIDATURA")),
        "totalization_status": clean(row.get("DS_SIT_TOT_TURNO")),
        "occupation": clean(row.get("DS_OCUPACAO")),
        "education": clean(row.get("DS_GRAU_INSTRUCAO")),
        "photo_url": (
            f"{PHOTO_MIRROR_BASE}/{clean(row.get('SQ_CANDIDATO'))}.jpg"
            if clean(row.get("SQ_CANDIDATO"))
            else None
        ),
        "photo_source": {
            "institution": "TSE",
            "dataset": "ES - Fotos de candidatos",
            "official_archive_url": TSE_PHOTO_ZIP,
            "transport": "cache público do pacote oficial TSE",
            "mirror": "Realidade Brasil",
            "mirror_base_url": PHOTO_MIRROR_BASE,
        },
        "assets": {
            "total_declared_brl": None,
            "count": 0,
            "items": [],
            "source": None,
        },
        "social_links": [],
        "tse_additional": {},
        "previous_elections": [],
        "current_mandate": None,
        "institutional_history": None,
        "source": {
            "institution": "TSE",
            "type": "fonte primária",
            "dataset": "Candidatos - 2026",
            "url": TSE_DATASET,
            "official_portal": DIVULGACAND,
            "transport": {
                "mode": "espelho operacional do arquivo oficial consulta_cand_2026.zip",
                "mirror_repository": mirror_info.get("repository"),
                "mirror_path": mirror_info.get("path"),
                "mirror_blob_sha": mirror_info.get("blob_sha"),
                "mirror_url": mirror_info.get("html_url"),
            },
        },
    }


def load_mirror():
    result = {"federal": [], "estadual": []}
    mirror_meta = {}
    for kind, (filename, office) in MIRROR_FILES.items():
        rows, info = mirror_snapshot(filename)
        mirror_meta[kind] = info
        normalized = [
            normalize_candidate(row, office, info)
            for row in rows
            if clean(row.get("SG_UF")) == UF and clean(row.get("DS_CARGO")) == office
        ]
        if not normalized:
            raise RuntimeError(f"Nenhum registro {office} no espelho")
        result[kind] = normalized
    return result, mirror_meta


def read_existing_json(name, default):
    path = OUT / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[aviso] snapshot anterior {name} ilegível: {exc}")
        return default


def chamber_current_es():
    url = f"{CAMARA}/deputados?siglaUf=ES&ordem=ASC&ordenarPor=nome&itens=100"
    payload = request_json(url)
    return url, payload.get("dados", [])


def chamber_detail(dep_id):
    base = f"{CAMARA}/deputados/{dep_id}"
    detail = request_json(base, timeout=15).get("dados", {})
    history = []
    external = []
    for suffix, target in (("historico", history), ("mandatosExternos", external)):
        try:
            target.extend(request_json(f"{base}/{suffix}", timeout=10).get("dados", []))
        except Exception as exc:
            print(f"[aviso] Câmara {dep_id}/{suffix}: {exc}")
    return detail, history, external


def enrich_federal(candidates):
    # A Câmara possui vários endpoints. Uma indisponibilidade transitória de
    # detalhe/histórico não pode apagar informação já validada no snapshot anterior.
    previous_chamber_rows = read_existing_json("federal-chamber.json", [])
    previous_candidates = read_existing_json("candidates-federal.json", [])

    previous_chamber = {
        row.get("chamber_id"): row
        for row in previous_chamber_rows
        if row.get("chamber_id") is not None
    }
    previous_candidates_by_tse = {
        row.get("tse_id"): row
        for row in previous_candidates
        if row.get("tse_id")
    }

    by_name = defaultdict(list)
    for candidate in candidates:
        for value in (
            candidate.get("ballot_name"),
            candidate.get("full_name"),
            candidate.get("social_name"),
        ):
            key = norm(value)
            if key:
                by_name[key].append(candidate)

    try:
        list_url, deputies = chamber_current_es()
        if not deputies:
            raise RuntimeError("lista atual da Câmara retornou vazia")
    except Exception as exc:
        preserved = 0
        for candidate in candidates:
            previous_candidate = previous_candidates_by_tse.get(candidate.get("tse_id")) or {}
            previous_mandate = previous_candidate.get("current_mandate")
            if previous_mandate:
                candidate["current_mandate"] = previous_mandate
                candidate["institutional_history"] = previous_candidate.get("institutional_history")
                preserved += 1
        if not previous_chamber_rows or preserved == 0:
            raise RuntimeError(
                "Câmara indisponível e não existe snapshot federal previamente validado "
                "para preservação; sync abortado para evitar regressão"
            ) from exc
        list_url = f"{CAMARA}/deputados?siglaUf=ES&ordem=ASC&ordenarPor=nome&itens=100"
        print(
            f"[aviso] Câmara indisponível; preservando {preserved} vínculos "
            "previamente validados sem promover estado novo."
        )
        return list_url, previous_chamber_rows

    exported = []
    exported_by_id = {}
    current_chamber_ids = set()

    for dep in deputies:
        dep_id = dep.get("id")
        if dep_id is None:
            continue

        current_chamber_ids.add(dep_id)
        previous = previous_chamber.get(dep_id, {})

        try:
            detail, history_raw, external_raw = chamber_detail(dep_id)
        except Exception as exc:
            print(f"[aviso] detalhe Câmara {dep_id}: {exc}")
            detail, history_raw, external_raw = {}, [], []

        status = detail.get("ultimoStatus") or {}

        history = [
            {
                "legislature_id": h.get("idLegislatura"),
                "party": clean(h.get("siglaPartido")),
                "condition": clean(h.get("condicaoEleitoral")),
                "status": clean(h.get("situacao")),
                "status_date": clean(h.get("data")),
            }
            for h in history_raw
        ]
        if not history:
            history = previous.get("history") or []

        external = [
            {
                "office": clean(m.get("cargo")),
                "uf": clean(m.get("uf")),
                "municipality": clean(m.get("municipio")),
                "party": clean(m.get("siglaPartido")),
                "start_year": m.get("anoInicio"),
                "end_year": m.get("anoFim"),
            }
            for m in external_raw
        ]
        if not external:
            external = previous.get("external_mandates") or []

        institutional = {
            "chamber_id": dep_id,
            "parliamentary_name": clean(
                status.get("nomeEleitoral")
                or dep.get("nome")
                or previous.get("parliamentary_name")
            ),
            "civil_name": clean(
                detail.get("nomeCivil")
                or previous.get("civil_name")
            ),
            "party": clean(
                status.get("siglaPartido")
                or dep.get("siglaPartido")
                or previous.get("party")
            ),
            "uf": clean(
                status.get("siglaUf")
                or dep.get("siglaUf")
                or previous.get("uf")
            ),
            "legislature_id": (
                status.get("idLegislatura")
                if status.get("idLegislatura") is not None
                else previous.get("legislature_id")
            ),
            "condition": clean(
                status.get("condicaoEleitoral")
                or previous.get("condition")
            ),
            "status": clean(
                status.get("situacao")
                or previous.get("status")
            ),
            "profile_url": f"https://www.camara.leg.br/deputados/{dep_id}",
            "api_url": f"{CAMARA}/deputados/{dep_id}",
            "history": history,
            "external_mandates": external,
            "data_links": {
                "expenses": f"{CAMARA}/deputados/{dep_id}/despesas",
                "events": f"{CAMARA}/deputados/{dep_id}/eventos",
                "speeches": f"{CAMARA}/deputados/{dep_id}/discursos",
                "bodies": f"{CAMARA}/deputados/{dep_id}/orgaos",
            },
        }

        chamber_names = {
            norm(dep.get("nome")),
            norm(status.get("nomeEleitoral")),
            norm(detail.get("nomeCivil")),
            norm(previous.get("parliamentary_name")),
            norm(previous.get("civil_name")),
        }

        matches = {}
        for key in chamber_names:
            rows = by_name.get(key, [])
            if key and len(rows) == 1:
                matches[rows[0]["tse_id"]] = rows[0]

        for candidate in matches.values():
            candidate["current_mandate"] = {
                "institution": "Câmara dos Deputados",
                "type": "federal",
                "verified_via": (
                    "Dados Abertos da Câmara + correspondência nominal exata"
                ),
                **institutional,
            }
            candidate["institutional_history"] = institutional

        exported.append(institutional)
        exported_by_id[dep_id] = institutional

    # Se o endpoint de detalhe falhar, preserve um vínculo de identidade já
    # validado anteriormente SOMENTE quando o mesmo chamber_id continua na
    # lista atual de deputados do ES. Assim, a rotina tolera falha transitória
    # sem perpetuar mandato de quem deixou a Câmara.
    for candidate in candidates:
        if candidate.get("current_mandate"):
            continue

        previous_candidate = previous_candidates_by_tse.get(candidate.get("tse_id")) or {}
        previous_mandate = previous_candidate.get("current_mandate") or {}
        chamber_id = previous_mandate.get("chamber_id")

        if chamber_id not in current_chamber_ids:
            continue

        institutional = exported_by_id.get(chamber_id)
        if not institutional:
            continue

        candidate["current_mandate"] = {
            "institution": "Câmara dos Deputados",
            "type": "federal",
            "verified_via": (
                "Câmara atual + vínculo de identidade previamente validado "
                "para o mesmo SQ_CANDIDATO"
            ),
            **institutional,
        }
        candidate["institutional_history"] = institutional

    return list_url, exported

def enrich_ales_reference(groups):
    reference = json.loads(ALES_REFERENCE_FILE.read_text(encoding="utf-8"))
    roster = {norm(name): name for name in reference.get("members_documented", [])}
    linked = 0

    for c in [item for group in groups for item in group]:
        names = {
            norm(c.get("ballot_name")),
            norm(c.get("full_name")),
            norm(c.get("social_name")),
        }
        match = next((roster[name] for name in names if name and name in roster), None)

        if match:
            evidence = {
                "institution": reference["institution"],
                "legislature": reference["legislature"],
                "type": reference["evidence_type"],
                "reference_date": reference["reference_date"],
                "name_in_document": match,
                "source": reference["source"],
                "warning": reference["warning"],
            }
            c.setdefault("institutional_evidence", []).append(evidence)
            linked += 1

        if c.get("office") == "DEPUTADO ESTADUAL":
            c["state_legislature"] = {
                "institution": "Assembleia Legislativa do Estado do Espírito Santo",
                "portal_url": ALES,
                "current_mandate_verified": False,
                "note": (
                    "Mandato estadual atual não é inferido por ocupação nem por snapshot histórico. "
                    "Evidências datadas da ALES aparecem separadamente quando há vínculo nominal exato."
                ),
            }

    return linked



def enrich_topic_evidence(groups):
    """Anexa evidências temáticas curadas por SQ_CANDIDATO.

    A fonte canônica fica em data/reference/topic-evidence.json para que um
    novo sync eleitoral não apague propostas/declarações já validadas.
    """
    candidates = [item for group in groups for item in group]
    by_id = {str(c.get("tse_id")): c for c in candidates if c.get("tse_id")}

    for candidate in candidates:
        candidate["topic_evidence"] = []

    if not TOPIC_EVIDENCE_FILE.exists():
        return 0

    payload = json.loads(TOPIC_EVIDENCE_FILE.read_text(encoding="utf-8"))
    entries = payload.get("entries") or []

    topic_payload = json.loads(TOPIC_REFERENCE_FILE.read_text(encoding="utf-8"))
    topic_ids = {item.get("id") for item in topic_payload.get("topics", []) if item.get("id")}
    allowed_types = {"proposta", "declaração", "atuação"}
    allowed_status = {"verified", "dated", "secondary_source"}
    seen = set()

    for index, item in enumerate(entries, start=1):
        candidate_id = clean(item.get("candidate_id"))
        topic_id = clean(item.get("topic_id"))
        evidence_type = clean(item.get("evidence_type"))
        source_url = clean(item.get("source_url"))
        source_title = clean(item.get("source_title"))
        source_publisher = clean(item.get("source_publisher"))
        captured_at = clean(item.get("captured_at"))
        verification_status = clean(item.get("verification_status"))
        statement = clean(item.get("statement"))
        quote_or_summary = clean(item.get("quote_or_summary"))

        if candidate_id not in by_id:
            raise RuntimeError(f"topic-evidence #{index}: SQ_CANDIDATO inexistente: {candidate_id}")
        if topic_id not in topic_ids:
            raise RuntimeError(f"topic-evidence #{index}: tema inexistente: {topic_id}")
        if evidence_type not in allowed_types:
            raise RuntimeError(f"topic-evidence #{index}: evidence_type inválido: {evidence_type}")
        if verification_status not in allowed_status:
            raise RuntimeError(
                f"topic-evidence #{index}: verification_status inválido: {verification_status}"
            )
        if not source_url or not source_url.startswith("https://"):
            raise RuntimeError(f"topic-evidence #{index}: source_url HTTPS obrigatório")
        if not source_title or not source_publisher or not captured_at:
            raise RuntimeError(
                f"topic-evidence #{index}: source_title, source_publisher e captured_at obrigatórios"
            )
        if not statement and not quote_or_summary:
            raise RuntimeError(f"topic-evidence #{index}: conteúdo documental ausente")

        dedupe_key = (
            candidate_id,
            topic_id,
            evidence_type,
            source_url,
            clean(item.get("published_at")),
            statement or quote_or_summary,
        )
        if dedupe_key in seen:
            raise RuntimeError(f"topic-evidence #{index}: registro duplicado")
        seen.add(dedupe_key)

        record = {
            "topic_id": topic_id,
            "evidence_type": evidence_type,
            "statement": statement,
            "source_url": source_url,
            "source_title": source_title,
            "source_publisher": source_publisher,
            "published_at": clean(item.get("published_at")),
            "captured_at": captured_at,
            "scope": clean(item.get("scope")),
            "quote_or_summary": quote_or_summary,
            "verification_status": verification_status,
        }
        by_id[candidate_id]["topic_evidence"].append(record)

    return len(entries)


def write_json(name, value):
    (OUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    candidates, mirror_meta = load_mirror()

    federal = candidates["federal"]
    estadual = candidates["estadual"]

    tse_enrichment_sources, tse_enrichment_counts = enrich_tse_open_data([federal, estadual])

    chamber_url, chamber_rows = enrich_federal(federal)

    ales_links = enrich_ales_reference([federal, estadual])
    topic_evidence_count = enrich_topic_evidence([federal, estadual])

    key = lambda c: norm(c.get("ballot_name") or c.get("full_name"))
    federal.sort(key=key)
    estadual.sort(key=key)

    collected = datetime.now(timezone.utc).isoformat()
    write_json("candidates-federal.json", federal)
    write_json("candidates-estadual.json", estadual)
    write_json("federal-chamber.json", chamber_rows)
    write_json(
        "meta.json",
        {
            "collected_at": collected,
            "uf": UF,
            "election_year": YEAR,
            "counts": {
                "federal": len(federal),
                "estadual": len(estadual),
                "federal_current_mandates_linked": sum(
                    1 for c in federal if c.get("current_mandate")
                ),
                "ales_2025_evidence_linked": ales_links,
                "topic_evidence": topic_evidence_count,
                **tse_enrichment_counts,
            },
            "sources": {
                "primary_tse_dataset": TSE_DATASET,
                "primary_tse_candidate_zip": TSE_CAND_ZIP,
                "primary_tse_complement_zip": TSE_COMPLEMENT_ZIP,
                "primary_tse_assets_zip": TSE_ASSETS_ZIP,
                "primary_tse_social_zip": TSE_SOCIAL_ZIP,
                "primary_tse_history_zip": TSE_HISTORY_ZIP,
                "tse_enrichment": tse_enrichment_sources,
                "primary_tse_photo_zip_es": TSE_PHOTO_ZIP,
                "photo_transport_mirror": PHOTO_MIRROR_BASE,
                "operational_mirror": mirror_meta,
                "camara_federal": chamber_url,
                "ales": ALES,
            },
            "data_quality": {
                "registration_status": (
                    "O status básico pode vir como #NE no espelho; quando disponível, "
                    "a ficha usa o julgamento da base oficial de informações complementares."
                ),
                "assets": (
                    "Bens são incorporados somente do arquivo oficial bem_candidato_2026, "
                    "com valores somados por SQ_CANDIDATO e proveniência registrada."
                ),
                "photos": (
                    "A fonte primária é o pacote ES - Fotos de candidatos do TSE. "
                    "Como o CDN oficial bloqueia o runner, a UI usa temporariamente um "
                    "cache público por SQ_CANDIDATO; falhas de imagem caem para placeholder."
                ),
                "electoral_history": (
                    "Histórico eleitoral é incorporado do recurso oficial Histórico de "
                    "candidaturas e mantido separado do histórico institucional da Câmara."
                ),
                "state_current_mandate": (
                    "Não inferido automaticamente; a composição da ALES requer validação "
                    "institucional datada."
                ),
            },
            "normalizer_version": "4.0.0",
        },
    )
    print(
        f"OK: {len(federal)} candidatos a deputado federal; "
        f"{len(estadual)} a deputado estadual; "
        f"{sum(1 for c in federal if c.get('current_mandate'))} "
        "vínculos atuais com a Câmara confirmados; "
        f"{ales_links} vínculos históricos ALES documentados; "
        f"{topic_evidence_count} evidências temáticas curadas; "
        f"{tse_enrichment_counts['asset_records']} bens; "
        f"{tse_enrichment_counts['social_links']} redes declaradas; "
        f"{tse_enrichment_counts['previous_election_records']} registros históricos TSE."
    )


if __name__ == "__main__":
    main()
