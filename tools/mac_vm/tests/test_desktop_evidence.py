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

    def add_missing_read(self):
        position = next(i for i, row in enumerate(self.rows) if row.get('tool') == 'get_window_state'
                        and row['event'] == 'dispatch' and row['at'] == 8)
        self.rows[position:position] = [
            dict(event='dispatch', run_id='task', call_id='missing-read', tool='read_result', used=8, at=7.3),
            dict(event='error', run_id='task', call_id='missing-read', tool='read_result', error='FileNotFoundError', at=7.4)]
        self.reindex_observations()
        self.save_trace()

    def reindex_observations(self):
        used = 0
        for row in self.rows:
            if row['event'] == 'dispatch':
                used += 1
                row['used'] = used
            if row['event'] == 'result' and row['tool'] == 'get_window_state':
                state = row['value']
            if row['event'] == 'observation_evidence':
                row['used'] = used
                for extension, data in [('json', json.dumps(state).encode()), ('png', self.png)]:
                    (self.root / ('state-%02d.' % used + extension)).write_bytes(data)

    def test_missing_read_before_fresh_observation_is_retained_and_counted(self):
        self.add_missing_read()
        before = (self.root / 'trace.jsonl').read_bytes()
        result = self.inspect()
        self.assertEqual(result['rawCalls'], 11)
        self.assertEqual(result['business']['recovered_missing_reads'], 1)
        self.assertEqual((self.root / 'trace.jsonl').read_bytes(), before)
        from real_app_verifier import verify_evidence
        final = json.loads((self.root / 'final_state.json').read_text())
        legacy = verify_evidence(self.rows, self.expected, self.expected, self.expected+b'\n', final)
        self.assertEqual(legacy['status'], 'UNVERIFIED')

    def test_other_errors_stale_observation_or_missing_final_read_still_rejected(self):
        self.add_missing_read()
        original = copy.deepcopy(self.rows)
        for fault in ('permission', 'successful-early', 'unknown', 'duplicate', 'no-final', 'no-fresh', 'late-error'):
            self.rows = copy.deepcopy(original)
            bad = next(row for row in self.rows if row['event'] == 'error')
            if fault == 'permission': bad['error'] = 'PermissionError'
            if fault == 'successful-early': bad.update(event='result', value=(self.expected+b'\n').decode())
            if fault == 'unknown': bad['event'] = 'UNKNOWN'
            if fault == 'duplicate': self.rows.insert(self.rows.index(bad)+1, dict(bad))
            if fault == 'no-final': self.rows = self.rows[:-2]
            if fault == 'no-fresh':
                pair = [row for row in self.rows if row.get('call_id') == 'missing-read']
                self.rows = [row for row in self.rows if row not in pair]
                pos = next(i for i, row in enumerate(self.rows) if row.get('tool') == 'write_result')
                pair[0]['at'], pair[1]['at'] = 8.3, 8.4
                self.rows[pos:pos] = pair
                self.reindex_observations()
            if fault == 'late-error': self.rows[-1].update(event='error', error='FileNotFoundError')
            self.save_trace()
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.inspect()

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

    def append_observation(self, **changes):
        state = json.loads((self.root / 'final_state.json').read_text())
        state.update(snapshot_id='tail', **changes)
        count = sum(row['event'] == 'dispatch' for row in self.rows) + 1
        at = self.rows[-1]['at'] + 1
        self.rows.extend([
            dict(event='dispatch', run_id='task', call_id=str(count), tool='get_window_state', used=count, at=at),
            dict(event='result', run_id='task', call_id=str(count), tool='get_window_state', value=state, at=at+.1)])
        files = {}
        for extension, data in [('json', json.dumps(state).encode()), ('png', self.png)]:
            (self.root / ('state-%02d.' % count + extension)).write_bytes(data)
            files[extension] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        self.rows.append(dict(event='observation_evidence', run_id='task', at=at+.2,
                              snapshot_id='tail', used=count, files=files))
        self.save_trace()

    def test_readonly_tail_retains_result_snapshot_and_all_files(self):
        final = (self.root / 'final_state.json').read_bytes()
        self.append_observation()
        verdict = self.inspect()
        self.assertEqual(verdict['rawCalls'], 11)
        self.assertIn('state-11.png', verdict['files'])
        self.assertEqual((self.root / 'final_state.json').read_bytes(), final)

    def test_tail_changed_body_window_or_pid_rejected(self):
        for changes in [{'tree_markdown': '- AXTextArea = "changed"'}, {'pid': 99}, {'window_id': 99}]:
            with self.subTest(changes=changes):
                original = copy.deepcopy(self.rows)
                self.append_observation(**changes)
                with self.assertRaises(ValueError): self.inspect()
                self.rows = original

    def test_successful_tail_without_evidence_rejected(self):
        self.append_observation()
        self.rows.pop()
        self.save_trace()
        with self.assertRaises(ValueError): self.inspect()

    def test_observation_between_write_and_read_is_also_readonly(self):
        self.append_observation()
        read_rows, tail = self.rows[-5:-3], self.rows[-3:]
        for index, row in enumerate(tail):
            row['at'] = 9.2 + index * .1
            if 'call_id' in row: row['call_id'] = '10'
            if 'used' in row: row['used'] = 10
        for row in read_rows:
            row['call_id'] = '11'
            if 'used' in row: row['used'] = 11
        for ext in ('json', 'png'):
            (self.root / ('state-11.'+ext)).rename(self.root / ('state-10.'+ext))
        self.rows[-5:] = tail + read_rows
        self.save_trace()
        self.assertEqual(self.inspect()['vmStatus'], 'VERIFIED')

    def test_tail_corrupt_image_rejected(self):
        self.append_observation()
        (self.root / 'state-11.png').write_bytes(self.png+b'tampered')
        with self.assertRaises(ValueError): self.inspect()

    def test_tail_mutation_or_failed_observation_rejected(self):
        original = copy.deepcopy(self.rows)
        for tool, event in [('hotkey','result'), ('type_text','result'), ('write_result','result'), ('get_window_state','error')]:
            self.rows = copy.deepcopy(original)
            self.rows.extend([
                dict(event='dispatch', run_id='task', call_id='11', used=11, tool=tool, at=12),
                dict(event=event, run_id='task', call_id='11', tool=tool, value={}, at=12.1)])
            self.save_trace()
            with self.subTest(tool=tool,event=event), self.assertRaises(ValueError): self.inspect()

    def test_result_snapshot_must_precede_write_and_be_fresh(self):
        self.append_observation()
        old = (self.root / 'final_state.json').read_bytes()
        (self.root / 'final_state.json').write_bytes((self.root / 'state-11.json').read_bytes())
        with self.assertRaises(ValueError): self.inspect()
        (self.root / 'final_state.json').write_bytes(old)
        for row in self.rows:
            if row['at'] >= 9: row['at'] += 31
        self.save_trace()
        with self.assertRaises(ValueError): self.inspect()
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
