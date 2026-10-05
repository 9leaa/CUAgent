"""Real task producer with a simulated Driver; no VM or model acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_lease import LeaseGate
from handoff_task import HandoffDesktopTask
from handoff_trace import verify_handoff_trace


class HandoffTraceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.run = 'p2-00000000-0000-4000-8000-000000000001'
        self.materials = json.dumps(dict(kind='project-handoff', project='项目', asOf='2026-10-05',
            notes=[dict(id='n', content='原文🙂')], tasksCsv='task_id,title,owner,status,due_date\n', previousReport=''),
            ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.expected = '独立期望正文🙂\n'.encode()
        self.body = ''; self.window = 20; self.serial = 0
        self.closing_waits = self.opening_waits = getattr(self, 'poll_delays', 0)
        self.was_closed = False
        lease = self.root / 'lease.json'
        lease.write_text(json.dumps(dict(version=1, runId=self.run, owner='worker', epoch=1, stopped=False, expiresAt=120000)))
        lease.chmod(0o600)
        gate = LeaseGate(lease, run_id=self.run, owner='worker', epoch=1, clock=lambda: 100.)
        self.task = HandoffDesktopTask(self.root / self.run, self.transport, lambda _: None, lease=gate,
            approved=True, environment=lambda: None, input_sha256=hashlib.sha256(self.materials).hexdigest(),
            document_opener=self.open_document)
        path = self.task.directory / 'handoff-input.json'; path.write_bytes(self.materials); path.chmod(0o600)
        for _ in range(getattr(self, 'extra_reads', 0)): self.task.read_materials()
        self.task.read_materials()
        state = self.task.observe()['state']
        self.task.type_text(dict(snapshot_id=state['snapshot_id'], element_index=2, element_token='body', text=self.expected.decode()))
        state = self.task.observe()['state']; self.task.save(dict(snapshot_id=state['snapshot_id']))
        state = self.task.observe()['state']; self.task.reopen(dict(snapshot_id=state['snapshot_id']))
        state = self.task.observe()['state']; self.task.write_result(dict(snapshot_id=state['snapshot_id'], value=self.expected.decode()))
        self.task.read_result(); self.task.stop()
        self.rows = [json.loads(line) for line in self.task.ledger.read_text().splitlines()]

    def open_document(self, pid, path):
        self.assertEqual(pid, 10); self.assertEqual(path, self.task.document)
        self.window = 21
        return True

    def transport(self, tool, args):
        if tool == 'launch_app': return dict(pid=10, bundle_id='com.apple.TextEdit')
        if tool == 'list_windows':
            if self.was_closed and self.window is None and self.closing_waits:
                self.closing_waits -= 1
                return dict(windows=[dict(pid=10, window_id=20, title=self.task.case.title,
                    app_name='TextEdit', is_on_screen=False)])
            if self.window == 21 and self.opening_waits:
                self.opening_waits -= 1
                return dict(windows=[])
            return dict(windows=[] if self.window is None else [dict(pid=10, window_id=self.window,
                title=self.task.case.title, app_name='TextEdit', is_on_screen=True)])
        if tool == 'get_window_state':
            self.serial += 1
            Path(args['screenshot_out_file']).write_bytes(b'\x89PNG\r\n\x1a\nSIMULATED')
            return dict(pid=10, window_id=self.window, snapshot_id=str(self.serial), app_name='TextEdit',
                window_title=self.task.case.title, screenshot_frame_valid=True,
                elements=[dict(element_index=1, role='AXWindow', label=self.task.case.title),
                          dict(element_index=2, parent_index=1, role='AXTextArea', element_token='body', value=self.body)])
        if tool == 'type_text': self.body = args['text']
        elif tool == 'hotkey':
            if args['keys'] == ['cmd', 's']: self.task.document.write_text(self.body)
            else: self.window = None; self.was_closed = True
        return dict(ok=True)

    def verify(self):
        return verify_handoff_trace(self.rows, run_id=self.run, materials=self.materials, expected=self.expected)

    def event(self, name):
        return next(r for r in self.rows if r['event'] == name)

    def result(self, tool):
        return next(r for r in self.rows if r['event'] == 'result' and r.get('tool') == tool)

    def test_producer_trace_no_file_session_or_semantic_claim(self):
        original = copy.deepcopy(self.rows)
        result = self.verify()
        self.assertEqual(result['status'], 'TRACE_VERIFIED')
        self.assertEqual(result['rawCalls'], self.task.used)
        self.assertEqual(result['finalSnapshotId'], '4')
        self.assertFalse(any(result[k] for k in ('filesVerified', 'sessionVerified', 'semanticVerified')))
        self.assertEqual(original, self.rows)

    def test_full_thirty_calls_includes_bounded_internal_polling(self):
        self.extra_reads = 11; self.poll_delays = 2
        self.setUp()
        self.assertEqual(self.verify()['rawCalls'], 30)
        # Failed read remains in the original trace; never filter it for a pass.
        self.result('read_materials')['event'] = 'error'
        with self.assertRaises(ValueError): self.verify()

    def test_noncanonical_material_and_unbound_expectation_denied(self):
        self.materials += b' '
        with self.assertRaises(ValueError): self.verify()
        self.materials = self.materials[:-1]
        self.expected += b'changed'
        with self.assertRaises(ValueError): self.verify()

    def test_intervening_material_read_invalidates_each_action_snapshot(self):
        original = copy.deepcopy(self.rows)
        for target in ('type_text', 'hotkey', 'handoff_reopen_intent', 'write_result'):
            self.rows = copy.deepcopy(original)
            index = next(i for i, r in enumerate(self.rows) if
                (r['event'] == 'dispatch' and r.get('tool') == target) or r['event'] == target)
            at = self.rows[index]['at']
            self.rows[index:index] = [
                dict(event='dispatch', run_id=self.run, call_id='intervening', tool='read_materials', used=0, at=at),
                dict(event='result', run_id=self.run, call_id='intervening', tool='read_materials', at=at,
                     value=json.loads(self.materials), inputSha256=hashlib.sha256(self.materials).hexdigest())]
            count = 0
            for row in self.rows:
                if row['event'] == 'dispatch': count += 1; row['used'] = count
                if row['event'] in ('observation_evidence', 'handoff_window_reopened'): row['used'] = count
            with self.subTest(target=target), self.assertRaises(ValueError): self.verify()

    def test_budget_stop_pairing_unknown_and_time_tampering(self):
        original = copy.deepcopy(self.rows)
        for fault in ('gap', 'bool', 'stop', 'unknown', 'pair', 'duplicate', 'nan', 'other-run', 'unapproved'):
            self.rows = copy.deepcopy(original)
            if fault == 'gap': self.event('dispatch')['used'] = 30
            elif fault == 'bool': self.event('dispatch')['used'] = True
            elif fault == 'stop': self.rows.insert(2, dict(event='stop', run_id=self.run, at=self.rows[2]['at']))
            elif fault == 'unknown': self.result('reopen_document')['event'] = 'UNKNOWN'
            elif fault == 'pair': self.result('read_result')['call_id'] = 'absent'
            elif fault == 'duplicate': self.rows.insert(3, copy.deepcopy(self.rows[2]))
            elif fault == 'nan': self.rows[0]['at'] = float('nan')
            elif fault == 'other-run': self.rows[0]['run_id'] = 'other'
            else: self.event('approval')['allowed_app'] = 'other'
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.verify()

    def test_material_body_and_readback_binding(self):
        original = copy.deepcopy(self.rows)
        for fault in ('source', 'sha', 'input', 'bytes', 'write', 'read', 'native', 'final-display'):
            self.rows = copy.deepcopy(original)
            if fault == 'source': self.result('read_materials')['value']['project'] = '改'
            elif fault == 'sha': self.result('read_materials')['inputSha256'] = '0' * 64
            elif fault == 'input': self.event('attempted_input')['sha256'] = '0' * 64
            elif fault == 'bytes': self.event('attempted_input')['bytes'] = 999
            elif fault == 'write': self.result('write_result')['value'] = 'wrong'
            elif fault == 'read': self.result('read_result')['value'] = 'wrong'
            elif fault == 'native': self.result('reopen_document')['value']['documentSha256'] = '0' * 64
            else:
                states = [r for r in self.rows if r['event'] == 'result' and r.get('tool') == 'get_window_state']
                states[-1]['value']['elements'][1]['value'] = 'wrong'
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.verify()

    def test_reopen_marker_and_inventory_tampering(self):
        original = copy.deepcopy(self.rows)
        for fault in ('missing', 'closed-pid', 'old-window', 'new-window', 'digest', 'count', 'still-open', 'ambiguous', 'no-window', 'close-refused'):
            self.rows = copy.deepcopy(original)
            if fault == 'missing': self.rows.remove(self.event('handoff_window_closed'))
            elif fault == 'closed-pid': self.event('handoff_window_closed')['pid'] = 99
            elif fault == 'old-window': self.event('handoff_window_reopened')['old_window_id'] = 99
            elif fault == 'new-window': self.event('handoff_window_reopened')['window_id'] = 99
            elif fault == 'digest': self.event('handoff_reopen_intent')['sha256'] = '0' * 64
            elif fault == 'count': self.event('handoff_window_reopened')['used'] = 1
            elif fault == 'close-refused':
                [r for r in self.rows if r['event'] == 'result' and r.get('tool') == 'hotkey'][-1]['value'] = {'status': 'refused'}
            else:
                inventories = [r['value']['windows'] for r in self.rows if r['event'] == 'result' and r.get('tool') == 'list_windows']
                if fault == 'still-open': inventories[1].extend(copy.deepcopy(inventories[0]))
                elif fault == 'ambiguous': inventories[-1].append(copy.deepcopy(inventories[-1][0]))
                else: inventories[-1].clear()
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.verify()

    def test_stale_consumed_and_missing_observations(self):
        original = copy.deepcopy(self.rows)
        for fault in ('input-stale', 'save-reuse', 'reopen-reuse', 'missing', 'screenshot', 'different-pid', 'after-reopen-old-window'):
            self.rows = copy.deepcopy(original)
            if fault == 'input-stale':
                start = self.rows.index(self.event('attempted_input')) - 2
                for row in self.rows[start:]: row['at'] += 31
            elif fault == 'save-reuse': self.event('attempted_save')['snapshot_id'] = '1'
            elif fault == 'reopen-reuse': self.event('handoff_reopen_intent')['snapshot_id'] = '2'
            elif fault == 'missing': self.rows.remove(self.event('observation_evidence'))
            elif fault == 'screenshot': self.result('get_window_state')['value']['screenshot_frame_valid'] = False
            elif fault == 'different-pid': self.result('get_window_state')['value']['pid'] = 99
            else:
                [r for r in self.rows if r['event'] == 'result' and r.get('tool') == 'get_window_state'][-1]['value']['window_id'] = 20
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.verify()


if __name__ == '__main__': unittest.main()
