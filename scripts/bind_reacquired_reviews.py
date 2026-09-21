#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import coletor_evidencias as collector

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def norm(value):
    return collector.norm(value)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--drafts",type=Path,required=True)
    ap.add_argument("--decisions",type=Path,required=True)
    ap.add_argument("--canonical",type=Path,required=True)
    ap.add_argument("--reviews",type=Path,required=True)
    ap.add_argument("--promotion-candidate",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    args=ap.parse_args()

    drafts_payload=load(args.drafts)
    decisions=load(args.decisions)
    canonical=load(args.canonical)
    drafts=drafts_payload.get("drafts") or []
    by_order={}
    for d in drafts:
        origin=d.get("source_origin") or {}
        order=origin.get("curation_order")
        if order is not None:
            if order in by_order:
                raise RuntimeError(f"curation_order duplicada nos drafts: {order}")
            by_order[order]=d

    reviews=[]
    for dec in decisions.get("approved_for_technical_binding") or []:
        order=dec["curation_order"]
        d=by_order.get(order)
        if not d:
            raise RuntimeError(f"decisão sem draft reancorado: {order}")
        if d.get("attribution_trust")!="official_author_api":
            raise RuntimeError(f"draft {order} sem confiança institucional")
        origin=d.get("source_origin") or {}
        if origin.get("discovery_method")!="api_idDeputadoAutor_paginated_reacquisition":
            raise RuntimeError(f"draft {order} sem método institucional esperado")
        title=collector.clean(d.get("source_title"))
        raw=collector.clean(d.get("raw_excerpt"))
        if not title or norm(title) not in norm(raw):
            raise RuntimeError(f"draft {order}: source_title não ancorado no raw_excerpt")
        chamber_id=origin.get("chamber_id")
        prop_id=origin.get("proposition_id")
        reviews.append({
            "draft_id":d["draft_id"],
            "status":"approved",
            "attempts":2,
            "topic_id":dec["topic_id"],
            "evidence_type":dec["evidence_type"],
            "statement":dec["statement"],
            "quote_or_summary":"",
            "scope":dec["scope"],
            "verification_status":dec["verification_status"],
            "support_text":title,
            "attribution_basis":(
                f"Câmara dos Deputados: proposição {prop_id} localizada na consulta "
                f"oficial paginada idDeputadoAutor={chamber_id}; título/ementa "
                "recoletados e ancorados no conteúdo bruto."
            ),
            "reviewed_at":"2026-09-21T13:34:09Z",
            "reviewer":"joyceradis",
        })

    reviews_payload={
        "version":"1.0.0",
        "updated_at":"2026-09-21T13:34:09Z",
        "semantics":"Decisões humanas pré-existentes reancoradas a drafts institucionais corrigidos; nenhum julgamento político novo foi automatizado.",
        "reviews":reviews,
    }
    candidates=collector.load_candidates()
    topics=collector.load_topic_ids()
    result,stats=collector.promote_reviews(
        drafts_payload=drafts_payload,
        reviews_payload=reviews_payload,
        canonical_payload=canonical,
        candidates=candidates,
        topic_ids=topics,
    )
    if stats["promoted"]!=len(reviews):
        raise RuntimeError(f"promoção seca incompleta: {stats}")

    args.reviews.write_text(json.dumps(reviews_payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    args.promotion_candidate.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report={
        "reacquired_drafts":len(drafts),
        "human_approved_bound":len(reviews),
        "held_by_frozen_taxonomy":len(decisions.get("held_by_frozen_taxonomy") or []),
        "dry_run_promoted":stats["promoted"],
        "canonical_before":len(canonical.get("entries") or []),
        "canonical_candidate_total":stats["total"],
        "canonical_writes":0,
    }
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
