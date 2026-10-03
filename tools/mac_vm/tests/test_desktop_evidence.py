import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_control import LeaseController
from desktop_evidence import inspect_guest_evidence
from desktop_lease import DesktopTask
from real_app_bridge import RealAppTask
import test_real_app_verifier


class DesktopEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'task'
        self.root.mkdir(mode=0o700)
        rows, self.expected, document, result, final = test_real_app_verifier.VerifyRealApp().evidence()
        self.rows = []
        self.png = b'\x89PNG\r\n\x1a\nSYNTHETIC_TEST_NOT_VISUAL_PROOF'
        used = 0
        for row in rows:
            row['run_id'] = 'task'
            self.rows.append(row)
            if row['event'] == 'dispatch':
                used = row['used']
            if row['event'] == 'result' and row['tool'] == 'get_window_state':
                state = row['value']
                state.update(app_name='TextEdit', window_title='handoff-task.txt')
                files = {}
                for extension, data in [('json', json.dumps(state).encode()), ('png', self.png)]:
                    (self.root / ('state-%02d.' % used + extension)).write_bytes(data)
                    files[extension] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                self.rows.append(dict(event='observation_evidence', run_id='task', at=row['at'] + .01,
                                      snapshot_id=state['snapshot_id'], used=used, files=files))
        final.update(app_name='TextEdit', window_title='handoff-task.txt')
        (self.root / 'final_state.json').write_text(json.dumps(final))
        (self.root / 'artifacts').mkdir(mode=0o700)
        (self.root / 'artifacts/handoff-task.txt').write_bytes(document)
        (self.root / 'result.txt').write_bytes(result)
        self.save_trace()

    def save_trace(self):
        (self.root / 'trace.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in self.rows))

    def inspect(self):
        return inspect_guest_evidence(self.root, run_id='task', expected=self.expected)

    def test_synthetic_bundle_verified_readonly_without_session_claim(self):
        before = {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        result = self.inspect()
        self.assertEqual(result['vmStatus'], 'VERIFIED')
        self.assertFalse(result['sessionVerified'])
        self.assertEqual(result['rawCalls'], 10)
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()})

    def test_tampered_png_state_document_and_result_rejected(self):
        for name in ['state-01.png', 'state-01.json', 'final_state.json', 'artifacts/handoff-task.txt', 'result.txt']:
            path = self.root / name
            original = path.read_bytes()
            with self.subTest(name=name):
                path.write_bytes(original + b'x')
                with self.assertRaises((ValueError, KeyError)):
                    self.inspect()
                path.write_bytes(original)

    def test_missing_hash_wrong_binding_and_stopped_dispatch_rejected(self):
        original = copy.deepcopy(self.rows)
        for mutation in ['missing', 'binding', 'stop', 'tool', 'duplicate', 'time', 'late_observation']:
            self.rows = copy.deepcopy(original)
            if mutation == 'missing':
                self.rows = [row for row in self.rows if row['event'] != 'observation_evidence']
            elif mutation == 'binding':
                self.rows[0]['run_id'] = 'other'
            elif mutation == 'stop':
                self.rows.insert(0, dict(event='stop', run_id='task', at=0))
            elif mutation == 'tool':
                self.rows[1]['tool'] = 'hotkey'
            elif mutation == 'duplicate':
                self.rows.insert(2, copy.deepcopy(self.rows[1]))
            elif mutation == 'time':
                self.rows[0]['at'] = float('nan')
            else:
                for row in self.rows:
                    if row['event'] == 'attempted_input':
                        row['snapshot_id'] = 'final'
            self.save_trace()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.inspect()

    def test_symlink_and_oversize_refused(self):
        path = self.root / 'result.txt'
        original = path.read_bytes()
        target = self.root.parent / 'outside.txt'
        target.write_bytes(original)
        path.unlink()
        path.symlink_to(target)
        with self.assertRaises(ValueError):
            self.inspect()
        path.unlink()
        path.write_bytes(b'x' * 4098)
        with self.assertRaises(ValueError):
            self.inspect()


class DesktopObservationEvidenceTests(unittest.TestCase):
    def test_hashes_original_observation_before_return_and_stops_on_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            controller = LeaseController(root / 'lease.json', run_id='task', owner='worker', epoch=1,
                                         clock=lambda: 100)
            controller.renew(1)
            task = DesktopTask(root / 'task', lease=controller.gate, approved=True, environment=lambda: None)
            png = b'\x89PNG\r\n\x1a\nSYNTHETIC'
            state = {'snapshot_id': 'fresh'}
            (task.directory / 'state-00.json').write_text(json.dumps(state))
            (task.directory / 'state-00.png').write_bytes(png)
            response = {'state': state, 'png': base64.b64encode(png).decode(), 'used': 0}
            with patch.object(RealAppTask, 'observe', return_value=response):
                self.assertEqual(task.observe(), response)
                rows = [json.loads(line) for line in task.ledger.read_text().splitlines()]
                self.assertEqual(rows[-1]['event'], 'observation_evidence')
                self.assertEqual(rows[-1]['files']['png']['sha256'], hashlib.sha256(png).hexdigest())
                (task.directory / 'state-00.png').write_bytes(png + b'changed')
                with self.assertRaises(ValueError):
                    task.observe()
                self.assertTrue(task.stopped.is_set())


if __name__ == '__main__':
    unittest.main()
