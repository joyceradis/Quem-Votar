#!/usr/bin/env python3
"""Auditoria rápida do estado publicável do Quem-Votar.

Valida contratos mínimos entre arquitetura, dados e interface. Não coleta dados,
não altera snapshots e não produz classificações políticas.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "generated"

REQUIRED_PAGES = {
    "index.html": 'data-page="home"',
    "candidatos.html": 'data-page="candidates"',
    "candidato.html": 'data-page="profile"',
    "temas.html": 'data-page="topics"',
    "comparar.html": 'data-page="compare"',
    "sobre.html": 'data-page="about"',
}

FORBIDDEN_FIELDS = {
    "cpf", "nr_cpf_candidato", "titulo_eleitoral", "nr_titulo_eleitoral",
    "email", "birth_date", "dt_nascimento", "telefone", "endereco",
}

def read(path: Path) -> str:
    assert path.exists(), f"arquivo obrigatório ausente: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")

def main() -> None:
    versions = set()
    for name, marker in REQUIRED_PAGES.items():
        text = read(ROOT / name)
        assert marker in text, f"{name}: marcador de página ausente"
        css = re.search(r'styles\.css\?v=([0-9.]+)', text)
        js = re.search(r'app\.js\?v=([0-9.]+)', text)
        assert css and js, f"{name}: assets sem versão explícita"
        assert css.group(1) == js.group(1), f"{name}: CSS/JS com versões diferentes"
        versions.add(css.group(1))
    assert len(versions) == 1, f"páginas com versões de assets divergentes: {sorted(versions)}"

    home = read(ROOT / "index.html")
    candidates_page = read(ROOT / "candidatos.html")
    profile_page = read(ROOT / "candidato.html")
    compare_page = read(ROOT / "comparar.html")
    topics_page = read(ROOT / "temas.html")
    app = read(ROOT / "app.js")
    styles = read(ROOT / "styles.css")
    quality_workflow = read(ROOT / ".github" / "workflows" / "quality.yml")
    sync_workflow = read(ROOT / ".github" / "workflows" / "sync-data.yml")
    delivery_governance = read(ROOT / "docs" / "DELIVERY_GOVERNANCE.md")
    governance = read(ROOT / "docs" / "GOVERNANCE.md")
    agents = read(ROOT / "AGENTS.md")
    agent_fence = read(ROOT / ".github" / "workflows" / "agent-fence.yml")
    codeowners = read(ROOT / ".github" / "CODEOWNERS")

    # Contrato visual e de entrega: impede herança silenciosa e tempestade de commits.
    assert len(re.findall(r":root\s*\{", styles)) == 1, "styles.css deve ter um único :root canônico"
    assert "visual depth pass" not in styles.lower(), "override visual legado reapareceu"
    assert "--green:" not in styles, "verde não faz parte da paleta estrutural azul/branco/rosa"
    assert all(token in styles for token in ("--blue:", "--blue-dark:", "--pink:", "--white:")), "tokens da identidade ES incompletos"
    assert "Tá, mas o que esse candidato pode mudar na sua vida?" in home, "Home deve manter a pergunta prática principal"
    assert re.search(r"\.desktop-nav\s*\{[^}]*display\s*:\s*none", styles), "navegação principal deve ficar no menu lateral"
    assert "\n  push:" not in sync_workflow, "sincronização de dados não deve rodar a cada push de interface"
    assert "[skip ci]" not in sync_workflow, "snapshot automático não pode pular CI"
    assert "git pull --rebase" not in sync_workflow, "sync não pode rebasear snapshot depois da auditoria"
    assert "python -m unittest discover" in quality_workflow, "Quality precisa executar testes"
    assert "Exigir checkpoint junto com data/generated" in agent_fence, (
        "Agent Fence precisa aplicar o acoplamento data/generated -> checkpoint"
    )
    assert "docs/CHECKPOINT_CURRENT.md" in agent_fence, (
        "checkpoint deve participar do gate de proveniência"
    )
    assert "data/generated/" in agent_fence, (
        "Agent Fence precisa detectar mudanças em data/generated"
    )
    assert "requirements-evidence.txt" in quality_workflow, "Quality precisa instalar dependências do coletor"
    assert "python scripts/audit-site.py" in sync_workflow, "sync precisa auditar o snapshot candidato"
    assert "python -m unittest discover" in sync_workflow, "sync precisa testar antes de exportar snapshot"
    assert "contents: read" in sync_workflow, "sync deve operar com contents read-only"
    assert "git push" not in sync_workflow and "git commit" not in sync_workflow, "sync não pode escrever diretamente em main"
    assert "actions/upload-artifact@v4" in sync_workflow, "sync deve exportar snapshot candidato como artifact"
    assert "\n    paths:" not in quality_workflow, "Quality deve rodar em todo push para main"
    assert "diretamente para `main`" not in agents, "AGENTS ainda autoriza escrita direta em main"
    assert "commit direto em `main`" not in governance, "GOVERNANCE ainda autoriza escrita direta em main"
    assert "Authorization-Issue:" in agent_fence, "mudança protegida precisa de autorização rastreável"
    assert "data/reference/topic-evidence\\.json" in agent_fence, "evidência canônica fora da cerca elétrica"
    assert "/data/reference/topic-evidence.json @joyceradis" in codeowners, "CODEOWNERS não cobre evidência canônica"
    assert "cancel-in-progress: false" in quality_workflow, "Quality deve enfileirar em vez de cancelar"
    assert "cancel-in-progress: false" in sync_workflow, "Sync deve enfileirar em vez de cancelar"
    assert "commit atômico" in delivery_governance.lower(), "governança de entrega atômica ausente"

    assert 'id="cards"' not in home, "Home voltou a concentrar a listagem"
    assert 'id="cards"' in candidates_page, "listagem sem mount de cards"
    assert 'id="pagination"' in candidates_page, "listagem sem paginação"
    assert 'id="compareMount"' in compare_page, "comparação sem mount próprio"
    assert 'id="topicCards"' in topics_page, "áreas/temas sem mount próprio"
    assert "const PAGE_SIZE=12" in app, "paginação deve permanecer explícita e auditável"
    public_markup = "\n".join(read(ROOT / name) for name in REQUIRED_PAGES) + "\n" + app
    assert public_markup.count('id="drawer"') == len(REQUIRED_PAGES), "menu lateral deve existir em todas as páginas"
    assert public_markup.count('id="menuButton"') == len(REQUIRED_PAGES), "botão do menu lateral deve existir em todas as páginas"
    assert "✓" not in public_markup, "UI pública não deve usar check como indicador visual"
    assert "selo" not in public_markup.lower(), 'UI pública não deve expor jargão "selo"'
    assert "topic-icon" not in public_markup and "step-no" not in public_markup, "ícones decorativos antigos reapareceram"
    assert "office-card.estadual" not in styles, "cargo estadual não pode receber cor partidária/semântica própria"
    assert "profile-tab" not in public_markup, "V5 não usa abas estreitas na ficha"
    assert "O que essa pessoa faz hoje?" in app and "O que ela diz que vai fazer?" in app and "Onde isso pode mexer na vida real?" in app, "ficha deve responder as três perguntas práticas"
    assert "data-snapshot-date" in home, "Home deve expor data de atualização"
    assert 'id="filterToggle"' in candidates_page and 'id="secondaryFilters"' in candidates_page, "filtros secundários devem usar divulgação progressiva"
    assert 'data-profile-url' in app, "cards devem oferecer navegação por toda a área útil"
    assert "Não vamos adivinhar posição pelo partido, profissão ou histórico." in app, "ficha deve explicitar limite contra inferência"
    assert "Orientação política" not in public_markup and "ideology" not in public_markup.lower(), "V5 não integra classificação ideológica própria"
    assert "Área profissional" not in public_markup, "V5 não usa profissão como tema público"
    assert 'id="topicFilter"' in candidates_page, "filtro temático documentado ausente"
    assert "policy-topics.json" in app, "UI deve usar taxonomia de temas de política pública"
    assert "evidencedTopicIds" in app and "visibleTopics" in app, "temas públicos devem depender de evidência documentada"
    assert 'id="profileShare"' in app and "navigator.share" in app, "compartilhamento de perfil ausente"
    assert 'property="og:title"' in profile_page and 'property="og:description"' in profile_page, "metadados sociais básicos ausentes"
    assert 'rel="canonical"' in profile_page, "URL canônica da ficha ausente"
    for init in ("initHome", "initCandidates", "initTopics", "initProfile", "initCompare", "initAbout"):
        assert f"function {init}" in app, f"controlador ausente: {init}"

    topics = json.loads(read(ROOT / "data" / "reference" / "policy-topics.json"))
    topic_evidence_source = json.loads(read(ROOT / "data" / "reference" / "topic-evidence.json"))
    assert isinstance(topic_evidence_source, dict), "topic-evidence deve ser objeto JSON"
    assert set(("version", "updated_at", "semantics", "entries")).issubset(topic_evidence_source), "topic-evidence: envelope canônico incompleto"
    assert isinstance(topic_evidence_source.get("entries"), list), "topic-evidence.entries deve ser lista"
    assert topics.get("topics"), "taxonomia de temas vazia"
    topic_ids = [x.get("id") for x in topics["topics"]]
    assert len(topic_ids) == len(set(topic_ids)), "id de tema duplicado"
    assert all(x.get("life_areas") for x in topics["topics"]), "todo assunto deve explicar onde pode aparecer na vida real"
    assert {"saude", "seguranca", "educacao", "economia"}.issubset(topic_ids), "temas essenciais ausentes"

    federal = json.loads(read(DATA / "candidates-federal.json"))
    estadual = json.loads(read(DATA / "candidates-estadual.json"))
    meta = json.loads(read(DATA / "meta.json"))
    rows = federal + estadual

    assert federal and estadual, "snapshot eleitoral vazio"
    assert meta["counts"]["federal"] == len(federal), "contagem federal divergente"
    assert meta["counts"]["estadual"] == len(estadual), "contagem estadual divergente"
    assert all(x.get("office") == "DEPUTADO FEDERAL" for x in federal)
    assert all(x.get("office") == "DEPUTADO ESTADUAL" for x in estadual)
    assert all(x.get("uf") == "ES" for x in rows)

    ids = [str(x.get("tse_id") or "") for x in rows]
    assert all(ids), "registro sem SQ_CANDIDATO"
    assert len(ids) == len(set(ids)), "SQ_CANDIDATO duplicado"

    social_root = ROOT / "social"
    social_manifest = json.loads(read(social_root / "manifest.json"))
    assert social_manifest.get("candidate_count") == len(rows), (
        "manifest de preview social diverge do snapshot"
    )
    assert social_manifest.get("candidate_ids") == sorted(ids), (
        "IDs do preview social divergem do snapshot eleitoral"
    )
    actual_social_ids = sorted(
        path.name
        for path in social_root.iterdir()
        if path.is_dir() and (path / "index.html").exists()
    )
    assert actual_social_ids == sorted(ids), (
        "cobertura de preview social deve ser 1:1 por SQ_CANDIDATO"
    )
    candidate_kind = {
        str(row.get("tse_id")): "federal" for row in federal
    } | {
        str(row.get("tse_id")): "estadual" for row in estadual
    }
    for cid in ids:
        preview = read(social_root / cid / "index.html")
        assert f'/social/{cid}/' in preview, f"{cid}: og:url social ausente"
        assert f"id={cid}" in preview, f"{cid}: redirect para ficha ausente"
        assert f"cargo={candidate_kind[cid]}" in preview, f"{cid}: cargo do redirect divergente"
        assert 'property="og:title"' in preview, f"{cid}: og:title ausente"
        assert 'property="og:description"' in preview, f"{cid}: og:description ausente"
        assert "googletagmanager.com" not in preview, (
            f"{cid}: wrapper social não deve carregar tracker"
        )

    source_entries = topic_evidence_source.get("entries") or []
    allowed_evidence_types = {"proposta", "declaração", "atuação"}
    allowed_evidence_status = {"verified", "dated", "secondary_source"}
    candidate_ids = set(ids)
    for index, item in enumerate(source_entries, start=1):
        candidate_id = str(item.get("candidate_id") or "")
        assert candidate_id in candidate_ids, f"topic-evidence #{index}: candidato inexistente"
        assert item.get("topic_id") in topic_ids, f"topic-evidence #{index}: tema inexistente"
        assert item.get("evidence_type") in allowed_evidence_types, f"topic-evidence #{index}: tipo inválido"
        assert item.get("verification_status") in allowed_evidence_status, f"topic-evidence #{index}: status inválido"
        assert str(item.get("source_url") or "").startswith("https://"), f"topic-evidence #{index}: fonte HTTPS obrigatória"
        assert item.get("source_title") and item.get("source_publisher") and item.get("captured_at"), f"topic-evidence #{index}: metadados de fonte incompletos"
        assert item.get("statement") or item.get("quote_or_summary"), f"topic-evidence #{index}: conteúdo vazio"

    generated_evidence = [item for row in rows for item in (row.get("topic_evidence") or [])]
    assert len(generated_evidence) == len(source_entries), "sync perdeu ou duplicou evidência temática"


    blob = json.dumps(rows, ensure_ascii=False).lower()
    assert "#ne" not in blob and "#nulo" not in blob, "sentinela TSE vazou no snapshot"
    unresolved_registration = [
        str(x.get("tse_id") or "")
        for x in rows
        if not isinstance(x.get("registration_status"), str)
        or not x.get("registration_status").strip()
    ]
    assert not unresolved_registration, (
        "registration_status não pode desaparecer em null/blank; "
        f"amostra={unresolved_registration[:5]}"
    )
    assert not any(f'"{field}"' in blob for field in FORBIDDEN_FIELDS), "campo pessoal proibido no snapshot"
    assert all(x.get("source", {}).get("institution") == "TSE" for x in rows), "origem eleitoral inconsistente"
    assert all(x.get("photo_source", {}).get("institution") == "TSE" for x in rows), "origem da foto não rastreável ao TSE"

    mirrors = meta.get("sources", {}).get("operational_mirror") or {}
    assert mirrors, "fallback sem proveniência"
    if meta.get("normalizer_version") == "3.1.0":
        for kind in ("federal", "estadual"):
            mirror = mirrors.get(kind) or {}
            assert mirror.get("commit_sha"), f"{kind}: commit imutável do espelho ausente"
            assert mirror.get("blob_sha"), f"{kind}: blob SHA do espelho ausente"
            assert mirror.get("content_sha256"), f"{kind}: hash dos bytes processados ausente"
    assert meta.get("sources", {}).get("camara_federal"), "fonte Câmara ausente: preservar último estado ou falhar fechado"

    with_photo_url = sum(bool(x.get("photo_url")) for x in rows)
    assert with_photo_url == len(rows), f"URLs de transporte de foto: {with_photo_url}/{len(rows)}"

    linked_federal = sum(bool(x.get("current_mandate")) for x in federal)
    linked_ales = sum(len(x.get("institutional_evidence") or []) for x in rows)
    assert linked_federal == meta["counts"].get("federal_current_mandates_linked"), "cobertura Câmara divergente"
    assert linked_ales == meta["counts"].get("ales_2025_evidence_linked"), "cobertura ALES divergente"

    print(
        "AUDITORIA OK | "
        f"assets v{next(iter(versions))} | "
        f"{len(federal)} federais | {len(estadual)} estaduais | "
        f"{with_photo_url}/{len(rows)} URLs de foto | "
        f"{linked_federal} vínculos Câmara | {linked_ales} evidências ALES | "
        f"{len(topic_ids)} temas de política pública | {len(source_entries)} evidências temáticas"
    )

if __name__ == "__main__":
    main()
