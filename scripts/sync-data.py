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

import json
import re
import unicodedata
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "generated"
OUT.mkdir(parents=True, exist_ok=True)

UF = "ES"
YEAR = 2026
UA = "Quem-Votar-ES/3.0 (+https://github.com/joyceradis/Quem-Votar-)"

TSE_DATASET = "https://dadosabertos.tse.jus.br/dataset/candidatos-2026"
TSE_CAND_ZIP = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip"
TSE_PHOTO_ZIP = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/fotos/foto_cand2026_ES_div.zip"
PHOTO_MIRROR_BASE = "https://realidadebrasil.com.br/media/photos"
DIVULGACAND = "https://divulgacandcontas.tse.jus.br/divulga/"
CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
ALES = "https://www.al.es.gov.br/"
ALES_REFERENCE_FILE = ROOT / "data" / "reference" / "ales-20a-legislatura-2025.json"
TOPIC_REFERENCE_FILE = ROOT / "data" / "reference" / "policy-topics.json"
TOPIC_EVIDENCE_FILE = ROOT / "data" / "reference" / "topic-evidence.json"

MIRROR_REPO = "herminiotorres/dossie-cidadao"
MIRROR_BASE = "https://raw.githubusercontent.com/herminiotorres/dossie-cidadao/main/docs/data/tse/candidatos/ES"
MIRROR_API_BASE = "https://api.github.com/repos/herminiotorres/dossie-cidadao/contents/docs/data/tse/candidatos/ES"

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


def mirror_metadata(filename):
    try:
        meta = request_json(f"{MIRROR_API_BASE}/{filename}?ref=main")
        return {
            "repository": MIRROR_REPO,
            "path": meta.get("path"),
            "blob_sha": meta.get("sha"),
            "html_url": meta.get("html_url"),
            "raw_url": meta.get("download_url"),
        }
    except Exception as exc:
        return {"repository": MIRROR_REPO, "path": filename, "error": str(exc)}


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
            "status": "não integrado neste snapshot básico",
        },
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
        raw_url = f"{MIRROR_BASE}/{filename}"
        rows = request_json(raw_url)
        if not isinstance(rows, list):
            raise RuntimeError(f"Espelho inválido: {raw_url}")
        info = mirror_metadata(filename)
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

    list_url, deputies = chamber_current_es()
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

    chamber_url = None
    chamber_rows = []
    try:
        chamber_url, chamber_rows = enrich_federal(federal)
    except Exception as exc:
        print(f"[aviso] Câmara indisponível: {exc}")

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
            },
            "sources": {
                "primary_tse_dataset": TSE_DATASET,
                "primary_tse_candidate_zip": TSE_CAND_ZIP,
                "primary_tse_photo_zip_es": TSE_PHOTO_ZIP,
                "photo_transport_mirror": PHOTO_MIRROR_BASE,
                "operational_mirror": mirror_meta,
                "camara_federal": chamber_url,
                "ales": ALES,
            },
            "data_quality": {
                "registration_status": (
                    "O arquivo básico espelhado retorna #NE para a situação de candidatura "
                    "dos registros ES; o sistema publica null em vez de atribuir significado."
                ),
                "assets": (
                    "Patrimônio não é publicado até haver ingestão auditável do "
                    "bem_candidato_2026."
                ),
                "photos": (
                    "A fonte primária é o pacote ES - Fotos de candidatos do TSE. "
                    "Como o CDN oficial bloqueia o runner, a UI usa temporariamente um "
                    "cache público por SQ_CANDIDATO; falhas de imagem caem para placeholder."
                ),
                "electoral_history": (
                    "Histórico eleitoral TSE ainda não é incorporado automaticamente neste "
                    "snapshot; histórico institucional federal é obtido da Câmara."
                ),
                "state_current_mandate": (
                    "Não inferido automaticamente; a composição da ALES requer validação "
                    "institucional datada."
                ),
            },
            "normalizer_version": "3.0.0",
        },
    )
    print(
        f"OK: {len(federal)} candidatos a deputado federal; "
        f"{len(estadual)} a deputado estadual; "
        f"{sum(1 for c in federal if c.get('current_mandate'))} "
        "vínculos atuais com a Câmara confirmados; "
        f"{ales_links} vínculos históricos ALES documentados; "
        f"{topic_evidence_count} evidências temáticas curadas."
    )


if __name__ == "__main__":
    main()
