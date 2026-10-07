import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_lease import LeaseGate
from handoff_task import HandoffDesktopTask
from driver_smoke import StopRun


class HandoffReopenTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        control = self.root / 'lease.json'
        control.write_text(json.dumps(dict(version=1, runId='task', owner='owner', epoch=1, stopped=False, expiresAt=120000)))
        control.chmod(0o600)
        self.gate = LeaseGate(control, run_id='task', owner='owner', epoch=1, clock=lambda: 100.)
        self.calls = []
        self.inventory = [[], None]
        self.opener = Mock(return_value=True)
        self.task = HandoffDesktopTask(self.root / 'task', self.transport, lambda _: None, lease=self.gate,
            approved=True, environment=lambda: None, input_sha256='a' * 64, document_opener=self.opener)
        self.task.document.write_text('正文\n')
        self.task.pid, self.task.window = 10, 20
        self.snapshot()
        self.task.save({'snapshot_id': 'fresh'})
        self.snapshot()

    def window(self, identity):
        return dict(pid=10, window_id=identity, title=self.task.case.title, app_name='TextEdit', is_on_screen=True)

    def snapshot(self, body='正文\n'):
        self.task.snapshot = dict(snapshot_id='fresh', pid=10, window_id=self.task.window,
            window_title=self.task.case.title, app_name='TextEdit', tree_markdown='- AXWindow\n  - AXTextArea = ' + json.dumps(body),
            screenshot_frame_valid=True, window_bounds=dict(x=70, y=48),
            elements=[dict(role='AXWindow', label=self.task.case.title, element_index=0),
                      dict(role='AXButton', element_index=6, element_token='fresh:6', parent_index=0,
                           enabled=True, actions=['AXPress'], frame=dict(x=76, y=54, w=16, h=16))])
        self.task.observed_at = time.monotonic()

    def transport(self, tool, args):
        self.calls.append((tool, args))
        if tool == 'list_windows':
            value = self.inventory.pop(0)
            return {'windows': [self.window(21)] if value is None else value}
        return {'ok': True}

    def test_close_same_pid_open_observe_required_and_no_more_edits(self):
        before = self.task.document.read_bytes()
        result = self.task.reopen({'snapshot_id': 'fresh'})
        self.assertEqual(result, {'requires_new_observation': True, 'used': 5})
        self.assertEqual(self.calls[1], ('click', dict(pid=10, window_id=20, session='task', element_index=6, element_token='fresh:6')))
        self.opener.assert_called_once_with(10, self.task.document)
        self.assertEqual(self.task.window, 21)
        self.assertIsNone(self.task.snapshot)
        self.assertEqual(self.task.document.read_bytes(), before)
        with self.assertRaises(StopRun): self.task.write_result({'snapshot_id': 'fresh', 'value': '正文\n'})
        self.snapshot()
        with self.assertRaises(StopRun): self.task.type_text({})
        with self.assertRaises(StopRun): self.task.save({'snapshot_id': 'fresh'})
        self.task.write_result({'snapshot_id': 'fresh', 'value': '正文\n'})
        self.assertEqual(self.task.read_result()['content'], '正文\n\n')
        with self.assertRaises(StopRun): self.task.reopen({'snapshot_id': 'fresh'})
        rows = [json.loads(line) for line in self.task.ledger.read_text().splitlines()]
        events = [r['event'] for r in rows]
        self.assertLess(events.index('handoff_window_closed'), events.index('handoff_window_reopened'))
        self.assertEqual(len([r for r in rows if r.get('tool') == 'reopen_document' and r['event'] == 'dispatch']), 1)

    def test_not_saved_stale_wrong_identity_or_bad_args_never_closes(self):
        for change in ('unsaved', 'stale', 'wrong_pid', 'args'):
            with self.subTest(change=change):
                self.snapshot(); self.task.saved_once = True
                args = {'snapshot_id': 'fresh'}
                if change == 'unsaved': self.task.saved_once = False
                if change == 'stale': self.task.observed_at -= 31
                if change == 'wrong_pid': self.task.snapshot['pid'] = 99
                if change == 'args': args['path'] = '/other'
                with self.assertRaises(StopRun): self.task.reopen(args)
        self.assertEqual(len(self.calls), 1)
        self.opener.assert_not_called()

    def test_unclosed_window_stops_without_open_or_discard(self):
        self.inventory = [[self.window(20)]] * 3
        with patch('handoff_task.time.sleep'):
            with self.assertRaises(StopRun): self.task.reopen({'snapshot_id': 'fresh'})
        self.assertTrue(self.task.stopped.is_set())
        self.assertEqual(self.task.used, 5)
        self.opener.assert_not_called()
        self.assertEqual(len([c for c in self.calls if c[0] == 'click']), 1)

    def test_invalid_close_targets_never_dispatch(self):
        for fault in ('missing', 'duplicate', 'disabled', 'token', 'minimize', 'nan', 'bool', 'dialog', 'stale_frame'):
            with self.subTest(fault=fault):
                self.snapshot()
                state = self.task.snapshot
                button = state['elements'][1]
                if fault == 'missing': state['elements'].pop()
                elif fault == 'duplicate': state['elements'].append(dict(button))
                elif fault == 'disabled': button['enabled'] = False
                elif fault == 'token': button['element_token'] = 'old:6'
                elif fault == 'minimize': button['frame']['x'] = 96
                elif fault == 'nan': button['frame']['x'] = float('nan')
                elif fault == 'bool': button['frame']['w'] = True
                elif fault == 'dialog': state['elements'].append(dict(role='AXSheet', element_index=9))
                else: state['screenshot_frame_valid'] = False
                with self.assertRaises(StopRun): self.task.reopen({'snapshot_id': 'fresh'})
                self.assertEqual(len(self.calls), 1)
                self.assertFalse((self.task.directory / 'handoff-reopen-intent.json').exists())

    def test_generic_click_and_close_shortcut_denied(self):
        with self.assertRaises(StopRun): self.task.raw('click', dict(pid=10, window_id=20))
        with self.assertRaises(StopRun): self.task.raw('hotkey', dict(pid=10, window_id=20, session='task', keys=['cmd', 'w'], delivery_mode='foreground'))
        self.assertEqual(len(self.calls), 1)

    def test_open_ack_without_new_window_is_not_success(self):
        self.inventory = [[], [], [], []]
        with patch('handoff_task.time.sleep'):
            with self.assertRaises(StopRun): self.task.reopen({'snapshot_id': 'fresh'})
        self.assertTrue(self.task.stopped.is_set()); self.assertFalse(self.task.reopened)
        self.opener.assert_called_once()

    def test_open_unknown_stops_no_retry_or_result(self):
        self.opener.side_effect = TimeoutError('unknown')
        with self.assertRaises(TimeoutError): self.task.reopen({'snapshot_id': 'fresh'})
        self.assertTrue(self.task.uncertain); self.assertTrue(self.task.stopped.is_set())
        self.assertEqual(self.task.inflight, set())
        with self.assertRaises(StopRun): self.task.reopen({'snapshot_id': 'fresh'})
        with self.assertRaises(StopRun): self.task.write_result({})
        self.opener.assert_called_once()

    def test_original_budget_reserves_all_eleven_calls(self):
        for _ in range(19):
            self.task.charge_rejection('test', self.task.used, 'test')
        self.snapshot()
        with self.assertRaises(StopRun): self.task.reopen({'snapshot_id': 'fresh'})
        self.assertEqual(self.task.used, 20)
        self.opener.assert_not_called()

    def test_prior_intent_and_changed_document_never_overwritten(self):
        path = self.task.directory / 'handoff-reopen-intent.json'; path.write_text('prior')
        with self.assertRaises(FileExistsError): self.task.reopen({'snapshot_id': 'fresh'})
        self.assertEqual(path.read_text(), 'prior')
        self.assertEqual(len(self.calls), 1)

    def test_document_changed_by_open_stops(self):
        def changed(*_): self.task.document.write_text('changed'); return True
        self.opener.side_effect = changed
        with self.assertRaises(StopRun): self.task.reopen({'snapshot_id': 'fresh'})
        self.assertFalse(self.task.reopened); self.assertTrue(self.task.stopped.is_set())

    def test_stop_during_native_open_blocks_following_window_request(self):
        def stop(*_): self.task.stop(); return True
        self.opener.side_effect = stop
        with self.assertRaises(StopRun): self.task.reopen({'snapshot_id': 'fresh'})
        self.assertEqual(self.task.used, 4)
        self.assertEqual(len([c for c in self.calls if c[0] == 'list_windows']), 1)
        self.assertFalse(self.task.reopened)


if __name__ == '__main__': unittest.main()
