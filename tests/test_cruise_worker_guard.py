#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cruise_worker_guard as guard


class CruiseWorkerGuardTests(unittest.TestCase):
    def test_success_is_silent_and_reports_backlog(self):
        sources={"sources":[{
            "candidate_id":"1",
            "source_url":"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=10",
            "source_publisher":"Câmara dos Deputados",
            "discovery_status":"exact_content",
            "source_origin":{"institution":"Câmara dos Deputados"},
        }]}
        drafts={"drafts":[{
            "candidate_id":"1","draft_id":"d1",
            "source_url":"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=10",
            "source_publisher":"Câmara dos Deputados",
            "attribution_trust":"official_author_api",
            "source_origin":{"institution":"Câmara dos Deputados","chamber_id":100,"proposition_id":10},
        }]}
        report=guard.build_report(
            sources_payload=sources,failures_payload={"failures":[]},drafts_payload=drafts,
            canonical_payload={"entries":[]},candidate_chamber_ids={"1":"100"},
        )
        self.assertEqual(0,report["metrics"]["actionable_incidents"])
        self.assertFalse(report["batching"]["auto_pr"])
        self.assertEqual(1,report["batching"]["accumulated_noncanonical_draft_urls"])

    def test_collection_failure_on_current_chamber_source_stays_recorded_but_does_not_page(self):
        url="https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=10"
        report=guard.build_report(
            sources_payload={"sources":[{"source_url":url,"source_publisher":"Câmara dos Deputados","discovery_status":"exact_content"}]},
            failures_payload={"failures":[{
                "candidate_id":"1","source_url":url,"source_id":"s1","stage":"collection",
                "error":"conteúdo institucional API insuficiente para revisão",
            }]},
            drafts_payload={"drafts":[]},canonical_payload={"entries":[]},candidate_chamber_ids={},
        )
        self.assertEqual(0,report["metrics"]["actionable_incidents"])

    def test_explicit_institutional_reacquisition_failure_is_actionable(self):
        url="https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=10"
        report=guard.build_report(
            sources_payload={"sources":[{"source_url":url,"source_publisher":"Câmara dos Deputados","discovery_status":"exact_content"}]},
            failures_payload={"failures":[{
                "candidate_id":"1","source_url":url,"source_id":"s1","stage":"reacquisition",
                "incident_type":"institutional_reacquisition_failure","error":"timeout acquiring institutional source",
            }]},
            drafts_payload={"drafts":[]},canonical_payload={"entries":[]},candidate_chamber_ids={},
        )
        self.assertEqual(1,report["metrics"]["actionable_incidents"])
        self.assertEqual("institutional_reacquisition_failure",report["incidents"][0]["type"])

    def test_noninstitutional_failure_does_not_page(self):
        report=guard.build_report(
            sources_payload={"sources":[{"source_url":"https://example.org/page","source_publisher":"Example","discovery_status":"exact_content"}]},
            failures_payload={"failures":[{
                "candidate_id":"1","source_url":"https://example.org/page","incident_type":"institutional_reacquisition_failure","error":"timeout",
            }]},
            drafts_payload={"drafts":[]},canonical_payload={"entries":[]},candidate_chamber_ids={},
        )
        self.assertEqual(0,report["metrics"]["actionable_incidents"])

    def test_anchor_mismatch_is_actionable(self):
        url="https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=10"
        report=guard.build_report(
            sources_payload={"sources":[]},failures_payload={"failures":[]},
            drafts_payload={"drafts":[{
                "candidate_id":"1","draft_id":"d1","source_url":url,
                "source_publisher":"Câmara dos Deputados","attribution_trust":"official_author_api",
                "source_origin":{"institution":"Câmara dos Deputados","chamber_id":999,"proposition_id":11},
            }]},
            canonical_payload={"entries":[]},candidate_chamber_ids={"1":"100"},
        )
        self.assertEqual(1,report["metrics"]["actionable_incidents"])
        problems=set(report["incidents"][0]["problems"])
        self.assertIn("proposition_id_url_mismatch",problems)
        self.assertIn("candidate_chamber_id_mismatch",problems)


if __name__=="__main__":
    unittest.main()
