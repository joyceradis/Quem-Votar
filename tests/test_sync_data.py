#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync-data.py"
SPEC = importlib.util.spec_from_file_location("sync_data", MODULE_PATH)
sync = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync
assert SPEC.loader is not None
SPEC.loader.exec_module(sync)

class SyncGovernanceTests(unittest.TestCase):
    def test_total_chamber_failure_preserves_previous_verified_links(self) -> None:
        candidates=[{"tse_id":"123","ballot_name":"MARIA SILVA","full_name":"MARIA SILVA","social_name":None,"current_mandate":None,"institutional_history":None}]
        mandate={"institution":"Câmara dos Deputados","type":"federal","chamber_id":99,"status":"Exercício"}
        history={"chamber_id":99,"status":"Exercício"}
        previous_candidate={"tse_id":"123","current_mandate":mandate,"institutional_history":history}
        previous_chamber=[{"chamber_id":99,"status":"Exercício"}]
        def fake_existing(name,default):
            if name=="federal-chamber.json": return previous_chamber
            if name=="candidates-federal.json": return [previous_candidate]
            return default
        with patch.object(sync,"read_existing_json",side_effect=fake_existing), patch.object(sync,"chamber_current_es",side_effect=RuntimeError("timeout")):
            url,exported=sync.enrich_federal(candidates)
        self.assertIn("dadosabertos.camara.leg.br",url)
        self.assertEqual(previous_chamber,exported)
        self.assertEqual(99,candidates[0]["current_mandate"]["chamber_id"])

    def test_total_chamber_failure_without_previous_state_fails_closed(self) -> None:
        candidates=[{"tse_id":"123","ballot_name":"MARIA SILVA","full_name":"MARIA SILVA","social_name":None,"current_mandate":None,"institutional_history":None}]
        with patch.object(sync,"read_existing_json",return_value=[]), patch.object(sync,"chamber_current_es",side_effect=RuntimeError("timeout")):
            with self.assertRaisesRegex(RuntimeError,"sync abortado"):
                sync.enrich_federal(candidates)

    def test_mirror_snapshot_pins_commit_blob_and_bytes(self) -> None:
        filename="deputado-federal.json"
        path=f"{sync.MIRROR_PATH_BASE}/{filename}"
        raw=json.dumps([{"SG_UF":"ES"}]).encode("utf-8")
        commit_sha="a"*40
        blob_sha="b"*40
        def fake_json(url,timeout=20):
            if "/commits?" in url: return [{"sha":commit_sha}]
            if "/contents/" in url: return {"sha":blob_sha}
            raise AssertionError(url)
        with patch.object(sync,"request_json",side_effect=fake_json), patch.object(sync,"request_bytes",return_value=raw) as bytes_mock:
            rows,meta=sync.mirror_snapshot(filename)
        self.assertEqual([{"SG_UF":"ES"}],rows)
        self.assertEqual(commit_sha,meta["commit_sha"])
        self.assertEqual(blob_sha,meta["blob_sha"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),meta["content_sha256"])
        self.assertIn(commit_sha,meta["raw_url"])
        self.assertIn(commit_sha,bytes_mock.call_args.args[0])

if __name__ == '__main__':
    unittest.main()
