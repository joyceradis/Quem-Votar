import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkerBudgetTests(unittest.TestCase):
    def run_drain(self, queued, progressed):
        workflow = (ROOT / '.github/workflows/evidence-industrial.yml').read_text()
        body = workflow.split('      - name: Drain exact-content backlog continuously\n', 1)[1].split('      - name:', 1)[0]
        script = textwrap.dedent(body.split('        run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            fake = '''import json,sys
from pathlib import Path
args=sys.argv
metrics={'queued':QUEUED,'eligible_before_fair_batch':1000,'collected':PROGRESSED,'failed':0,'quarantined':0,'rejected':0}
Path(args[args.index('--metrics')+1]).write_text(json.dumps(metrics))
'''.replace('QUEUED', str(queued)).replace('PROGRESSED', str(progressed))
            (root / 'scripts/process_evidence_batch.py').write_text(fake)
            script = script.replace('${{ steps.ws.outputs.out }}', directory).replace('${{ steps.ws.outputs.state }}', directory)
            result = subprocess.run(['bash', '-c', script], cwd=root, capture_output=True, text=True, env={**os.environ, 'GITHUB_SHA':'base', 'GITHUB_RUN_ID':'123', 'GITHUB_RUN_ATTEMPT':'1'})
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
