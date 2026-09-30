#!/usr/bin/env python3
"""Selectively restore verified historical Câmara sources for recovery."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import coletor_evidencias as collector
import process_evidence_batch as batch

EXPECTED_ERROR = "conteúdo institucional API insuficiente para revisão"
MAX_RECOVERY_SOURCES = 20


def parse_source_ids(value: str) -> list[str]:
    parts = [part.strip() for part in value.split(",")]
    if (
        not parts
        or any(not part for part in parts)
        or len(parts) > MAX_RECOVERY_SOURCES
    ):
        raise ValueError(f"Informe entre 1 e {MAX_RECOVERY_SOURCES} source IDs.")
    source_ids = parts
    if any(not re.fullmatch(r"[0-9a-f]{20}", source_id) for source_id in source_ids):
        raise ValueError("Todos os source IDs devem conter 20 caracteres hexadecimais.")
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("Source IDs duplicados não são permitidos.")
    return source_ids


def read_run_metadata(path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        metadata[key] = value
    return metadata


def verify_artifact(
    artifact_dir: Path,
    *,
    expected_repository: str,
    expected_run_id: str,
    required_files: tuple[str, ...],
) -> dict[str, str]:
    metadata = read_run_metadata(artifact_dir / "RUN_METADATA.txt")
    if (
        metadata.get("repository") != expected_repository
        or metadata.get("run_id") != expected_run_id
        or not re.fullmatch(r"[0-9a-f]{40}", metadata.get("commit", ""))
    ):
        raise ValueError("Proveniência do artifact não corresponde ao run/repositório.")

    checksums: dict[str, str] = {}
    for line in (artifact_dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, separator, filename = line.partition("  ")
        if separator:
            checksums[filename] = digest
    for filename in required_files:
        path = artifact_dir / filename
        expected = checksums.get(filename)
        if not path.is_file() or not expected:
            raise ValueError(f"Artifact sem arquivo/checksum obrigatório: {filename}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Checksum inválido no artifact: {filename}")
    return metadata


def is_official_proposition(item: dict[str, Any]) -> bool:
    url = urlparse(str(item.get("source_url") or ""))
    source_ids = parse_qs(url.query).get("idProposicao", [])
    origin = item.get("source_origin") or {}
    snapshot = item.get("institutional_snapshot") or {}
    document = urlparse(str(snapshot.get("urlInteiroTeor") or ""))
    document_ids = parse_qs(document.query).get("codteor", [])
    return (
        url.scheme == "https"
        and url.hostname == "www.camara.leg.br"
        and url.path == "/proposicoesWeb/fichadetramitacao"
        and len(source_ids) == 1
        and source_ids[0].isdigit()
        and str(snapshot.get("proposition_id") or "") == source_ids[0]
        and str(snapshot.get("candidate_id") or "") == str(item.get("candidate_id") or "")
        and str(snapshot.get("chamber_id") or "") == str(origin.get("chamber_id") or "")
        and str(origin.get("proposition_id") or "") == source_ids[0]
        and str(origin.get("institution") or "").casefold() == "câmara dos deputados".casefold()
        and str(origin.get("chamber_id") or "").isdigit()
        and bool(str(origin.get("author_name") or "").strip())
        and origin.get("authorship_scope") == "listed_author_signatory"
        and document.scheme == "https"
        and document.hostname == "www.camara.leg.br"
        and document.path == "/proposicoesWeb/prop_mostrarintegra"
        and len(document_ids) == 1
        and document_ids[0].isdigit()
        and str(snapshot.get("siglaTipo") or "") in {"EMR", "SBT"}
        and item.get("attribution_trust") in collector.TRUSTED_CHAMBER_ATTRIBUTION
        and item.get("source_kind") == "institutional"
        and item.get("discovery_status") == "exact_content"
    )


def build_recovery_payload(
    *,
    sources: list[dict[str, Any]],
    states: dict[str, Any],
    source_ids: list[str],
) -> list[dict[str, Any]]:
    requested = set(source_ids)
    sources_by_id: dict[str, dict[str, Any]] = {}
    for item in sources:
        source_id = batch.make_source_id(item)
        if source_id not in requested:
            continue
        if source_id in sources_by_id:
            current = sources_by_id[source_id]
            fields = (
                "candidate_id",
                "source_url",
                "source_kind",
                "discovery_status",
                "attribution_trust",
                "source_origin",
                "institutional_snapshot",
            )
            if any(current.get(field) != item.get(field) for field in fields):
                raise ValueError(f"Proveniência duplicada e divergente no artifact: {source_id}")
            continue
        sources_by_id[source_id] = item

    selected: list[dict[str, Any]] = []
    for source_id in source_ids:
        item = sources_by_id.get(source_id)
        state = states.get(source_id)
        if item is None or not isinstance(state, dict):
            raise ValueError(f"Source ID ausente no artifact ou no estado atual: {source_id}")
        snapshot = item.get("institutional_snapshot") or {}
        if (
            state.get("status") != "failed"
            or int(state.get("attempts", 0) or 0) < 3
            or int(state.get("reprocess_count", 0) or 0) != 0
            or state.get("last_error") != EXPECTED_ERROR
            or state.get("chamber_section_recovery_v1")
        ):
            raise ValueError(f"Source ID não está elegível para migração seletiva: {source_id}")
        if (
            state.get("candidate_id") != item.get("candidate_id")
            or state.get("source_url") != item.get("source_url")
            or not isinstance(snapshot, dict)
            or snapshot.get("siglaTipo") not in {"EMR", "SBT"}
            or not is_official_proposition(item)
        ):
            raise ValueError(f"Proveniência incompatível para recuperação: {source_id}")
        selected.append(item)
    return selected


def restore_selected_baseline_states(
    *,
    current_states: dict[str, Any],
    baseline_states: dict[str, Any],
    source_ids: list[str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if not isinstance(current_states, dict) or not isinstance(baseline_states, dict):
        raise ValueError("Current/baseline processing state deve conter mapa de fontes.")
    restored = {source_id: dict(row) for source_id, row in current_states.items()}
    previous: dict[str, dict[str, Any]] = {}
    for source_id in source_ids:
        current = current_states.get(source_id)
        baseline = baseline_states.get(source_id)
        if not isinstance(current, dict) or not isinstance(baseline, dict):
            raise ValueError(f"Estado atual/baseline ausente: {source_id}")
        if (
            baseline.get("status") != "failed"
            or int(baseline.get("attempts", 0) or 0) < 3
            or int(baseline.get("reprocess_count", 0) or 0) != 0
            or baseline.get("last_error") != EXPECTED_ERROR
            or baseline.get("chamber_section_recovery_v1")
        ):
            raise ValueError(f"Estado baseline não é uma falha elegível: {source_id}")
        if (
            current.get("candidate_id") != baseline.get("candidate_id")
            or current.get("source_url") != baseline.get("source_url")
        ):
            raise ValueError(f"Identidade no estado atual diverge do baseline: {source_id}")

        is_unmigrated = (
            current.get("status") == "failed"
            and int(current.get("reprocess_count", 0) or 0) == 0
            and current.get("last_error") == EXPECTED_ERROR
            and not current.get("chamber_section_recovery_v1")
        )
        is_prior_migration = (
            current.get("status") == "collected"
            and current.get("chamber_section_recovery_v1") is True
        )
        if not (is_unmigrated or is_prior_migration):
            raise ValueError(f"Estado atual não pode ser restaurado seletivamente: {source_id}")
        previous[source_id] = dict(current)
        restored[source_id] = dict(baseline)
    return restored, previous


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--baseline-artifact-dir", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--source-ids", required=True)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-baseline-run-id", required=True)
    parser.add_argument("--expected-repository", required=True)
    parser.add_argument("--output-sources", type=Path, required=True)
    parser.add_argument("--output-audit", type=Path, required=True)
    args = parser.parse_args()

    try:
        source_ids = parse_source_ids(args.source_ids)
        metadata = verify_artifact(
            args.artifact_dir,
            expected_repository=args.expected_repository,
            expected_run_id=args.expected_run_id,
            required_files=("topic-evidence-sources.json",),
        )
        baseline_metadata = verify_artifact(
            args.baseline_artifact_dir,
            expected_repository=args.expected_repository,
            expected_run_id=args.expected_baseline_run_id,
            required_files=("processing-state.json",),
        )

        historical = json.loads(
            (args.artifact_dir / "topic-evidence-sources.json").read_text(encoding="utf-8")
        )
        current_state = json.loads(args.state.read_text(encoding="utf-8"))
        baseline_state = json.loads(
            (args.baseline_artifact_dir / "processing-state.json").read_text(encoding="utf-8")
        )
        restored_states, previous_states = restore_selected_baseline_states(
            current_states=current_state.get("sources", {}),
            baseline_states=baseline_state.get("sources", {}),
            source_ids=source_ids,
        )
        selected = build_recovery_payload(
            sources=historical.get("sources", []),
            states=baseline_state.get("sources", {}),
            source_ids=source_ids,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Recovery source validation failed: {exc}", file=sys.stderr)
        return 1

    current_state["sources"] = restored_states
    args.state.write_text(
        json.dumps(current_state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_sources.parent.mkdir(parents=True, exist_ok=True)
    args.output_audit.parent.mkdir(parents=True, exist_ok=True)
    args.output_sources.write_text(
        json.dumps(
            {
                "semantics": (
                    "Selected exact-content historical sources for non-canonical recovery only."
                ),
                "sources": selected,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    args.output_audit.write_text(
        json.dumps(
            {
                "source_run_id": args.expected_run_id,
                "source_commit": metadata["commit"],
                "baseline_state_run_id": args.expected_baseline_run_id,
                "baseline_state_commit": baseline_metadata["commit"],
                "source_ids": source_ids,
                "selected_sources": len(selected),
                "baseline_attempts": {
                    source_id: int(
                        baseline_state["sources"][source_id].get("attempts", 0) or 0
                    )
                    for source_id in source_ids
                },
                "previous_state": {
                    source_id: {
                        "status": previous_states[source_id].get("status"),
                        "attempts": previous_states[source_id].get("attempts"),
                        "reprocess_count": previous_states[source_id].get("reprocess_count"),
                        "chamber_section_recovery_v1": previous_states[source_id].get(
                            "chamber_section_recovery_v1", False
                        ),
                    }
                    for source_id in source_ids
                },
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"validated_recovery_sources={len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
