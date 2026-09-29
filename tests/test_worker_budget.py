import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkerBudgetTests(unittest.TestCase):
    def run_drain(self, queued, progressed, recovery_source_ids=''):
        workflow = (ROOT / '.github/workflows/evidence-industrial.yml').read_text()
        body = workflow.split('      - name: Drain exact-content backlog continuously\n', 1)[1].split('      - name:', 1)[0]
        script = textwrap.dedent(body.split('        run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            fake = '''import json,os,sys
from pathlib import Path
args=sys.argv
recovery_count=args.count('--reprocess-source-id')
queued=QUEUED
progressed=PROGRESSED
if os.environ.get('RECOVERY_SOURCE_IDS') and recovery_count == 0:
    queued=0
    progressed=0
metrics={'queued':queued,'eligible_before_fair_batch':1000 if queued else 0,'collected':progressed,'failed':0,'quarantined':0,'rejected':0}
if os.environ.get('RECOVERY_SOURCE_IDS'):
    print(f'recovery_id_arguments={recovery_count}')
Path(args[args.index('--metrics')+1]).write_text(json.dumps(metrics))
'''.replace('QUEUED', str(queued)).replace('PROGRESSED', str(progressed))
            (root / 'scripts/process_evidence_batch.py').write_text(fake)
            script = script.replace('${{ steps.ws.outputs.out }}', directory).replace('${{ steps.ws.outputs.state }}', directory)
            result = subprocess.run(['bash', '-c', script], cwd=root, capture_output=True, text=True, env={
                **os.environ,
                'GITHUB_SHA':'base',
                'GITHUB_RUN_ID':'123',
                'GITHUB_RUN_ATTEMPT':'1',
                'RECOVERY_SOURCE_IDS':recovery_source_ids,
            })
            checkpoint = root / 'drain-status.json'
            return result, json.loads(checkpoint.read_text()) if checkpoint.exists() else None

    def test_budget_exhaustion_exports_partial_checkpoint(self):
        result, status = self.run_drain(24, 24)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('budget_exhausted', status['stop_reason'])
        self.assertFalse(status['backlog_drained'])
        self.assertEqual(100, status['cycles'])

    def test_empty_queue_exports_drained_checkpoint(self):
        result, status = self.run_drain(0, 0)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(status['backlog_drained'])

    def test_no_progress_remains_failure(self):
        result, _ = self.run_drain(24, 0)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('made no progress', result.stdout)

    def test_recovery_ids_are_forced_only_once_before_backlog_drains(self):
        result, status = self.run_drain(
            2,
            2,
            recovery_source_ids='0123456789abcdefabcd,fedcba98765432100123',
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(status['backlog_drained'])
        self.assertEqual('drained', status['stop_reason'])
        self.assertEqual(2, status['cycles'])
        self.assertEqual(1, result.stdout.count('recovery_id_arguments=2'))
        self.assertEqual(1, result.stdout.count('recovery_id_arguments=0'))
