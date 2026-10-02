import copy
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from real_app_verifier import verify_evidence


class VerifyRealApp(unittest.TestCase):
    def evidence(self):
        expected = b'new task\n'
        def state(snapshot):
            return {'pid': 1, 'window_id': 2, 'snapshot_id': snapshot, 'screenshot_frame_valid': True,
                    'window_title': 'handoff.txt', 'tree_markdown': '- AXWindow\n  - AXTextArea = "new task"'}
        rows = []
        def call(tool, at, value):
            identity = str(len([r for r in rows if r['event'] == 'dispatch']) + 1)
            rows.append({'event': 'dispatch', 'tool': tool, 'call_id': identity, 'used': int(identity), 'at': at})
            rows.append({'event': 'result', 'tool': tool, 'call_id': identity, 'value': value, 'at': at + .1})
        call('get_window_state', 1, state('a')); call('type_text', 2, {})
        rows.append({'event': 'attempted_input', 'snapshot_id': 'a', 'sha256': hashlib.sha256(expected).hexdigest(), 'at': 2.2})
        for snapshot, at in [('b', 3), ('c', 5)]:
            call('get_window_state', at, state(snapshot)); call('hotkey', at + 1, {})
            rows.append({'event': 'attempted_save', 'snapshot_id': snapshot, 'at': at + 1.2})
        call('rejected_write_result', 7, {'error': 'Result observation stale'})
        call('get_window_state', 8, state('final')); call('write_result', 9, 'new task\n')
        call('read_result', 10, 'new task\n\n')
        return rows, expected, expected, expected + b'\n', state('final')
    def test_grounded_save_retry_and_refusal_preserved(self):
        report = verify_evidence(*self.evidence())
        self.assertEqual(report['status'], 'SUCCEEDED')
        self.assertEqual(report['saves'], 2); self.assertEqual(report['rejected_calls'], 1)
    def test_wrong_file_or_result_never_passes(self):
        for index in (2, 3):
            data = list(self.evidence()); data[index] += b'bad'
            self.assertEqual(verify_evidence(*data)['status'], 'UNVERIFIED')
    def test_stale_replayed_save_never_passes(self):
        data = list(self.evidence()); data[0] = copy.deepcopy(data[0])
        saves = [r for r in data[0] if r['event'] == 'attempted_save']; saves[1]['snapshot_id'] = saves[0]['snapshot_id']
        self.assertEqual(verify_evidence(*data)['status'], 'UNVERIFIED')
    def test_unknown_incomplete_and_duplicate_dispatch_never_pass(self):
        for mutation in ('UNKNOWN', 'incomplete', 'duplicate'):
            data = list(self.evidence()); data[0] = copy.deepcopy(data[0])
            if mutation == 'UNKNOWN': data[0].append({'event': 'UNKNOWN'})
            elif mutation == 'incomplete': data[0].pop()
            else: data[0].append(copy.deepcopy(data[0][0]))
            self.assertEqual(verify_evidence(*data)['status'], 'UNVERIFIED')
    def test_late_readonly_observation_failure_does_not_hide_completed_business(self):
        data = list(self.evidence())
        count = len([r for r in data[0] if r['event'] == 'dispatch']) + 1
        data[0] += [{'event': 'dispatch', 'tool': 'get_window_state', 'call_id': str(count), 'used': count, 'at': 12},
                    {'event': 'error', 'tool': 'get_window_state', 'call_id': str(count), 'at': 12.1}]
        self.assertEqual(verify_evidence(*data)['status'], 'SUCCEEDED')
        data[0][-1]['tool'] = data[0][-2]['tool'] = 'type_text'
        self.assertEqual(verify_evidence(*data)['status'], 'UNVERIFIED')
