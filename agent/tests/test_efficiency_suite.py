import json
from pathlib import Path
import tempfile
import unittest
from agent.efficiency_suite import freeze, check


class SuiteTests(unittest.TestCase):
    def test_freeze_all_pairs_without_model_outputs_and_reject_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'suite'
            self.assertEqual(freeze(root)['trials'], 40)
            self.assertEqual(check(root)['status'], 'FROZEN')
            manifest = json.loads((root / 'manifest.json').read_text())
            self.assertEqual(len({t['sessionId'] for t in manifest['trials']}), 40)
            for trial in manifest['trials']:
                run = Path(trial['runDir'])
                self.assertFalse((run / 'session.jsonl').exists())
                self.assertFalse((run / 'workspace/report.json').exists())
            with self.assertRaises(ValueError): freeze(root)
            file = Path(manifest['trials'][0]['runDir']) / 'workspace/task.json'
            file.chmod(0o600); file.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'input changed'): check(root)

    def test_changed_approval_or_oracle_never_accepted(self):
        for name in ('approval.json', 'oracle.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / 'suite'
                freeze(root)
                manifest = json.loads((root / 'manifest.json').read_text())
                file = Path(manifest['trials'][0]['runDir']) / name
                file.write_text('{}')
                with self.assertRaises(ValueError): check(root)
