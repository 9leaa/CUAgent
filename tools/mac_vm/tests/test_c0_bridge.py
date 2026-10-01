"""No VM, model, network or desktop actions: C0 execution-policy regression."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from c0_bridge import Task, StopRun, BUNDLE


class BridgePolicy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / 'run'
        self.sent = []
        self.task = Task(self.root, self.transport, lambda _: None, approved=True)

    def tearDown(self):
        self.tmp.cleanup()

    def transport(self, tool, args):
        self.sent.append(tool)
        return {'bundle_id': BUNDLE, 'pid': 99}

    def snapshot(self, label='1'):
        self.task.pid, self.task.window = 99, 50
        self.task.snapshot = {
            'snapshot_id': 'fresh', 'tree_markdown': '- AXWindow\n  - AXStaticText = "408"',
            'elements': [
                {'element_index': 0, 'role': 'AXWindow', 'label': 'Calculator'},
                {'element_index': 1, 'parent_index': 0, 'role': 'AXButton',
                 'label': label, 'element_token': 'token', 'enabled': True, 'actions': ['AXPress']}],
        }
        self.task.observed_at = time.monotonic()
        return {'snapshot_id': 'fresh', 'element_index': 1, 'element_token': 'token'}

    def rows(self):
        return [json.loads(line) for line in self.task.ledger.read_text().splitlines()]

    def test_explicit_approval_required(self):
        with self.assertRaises(StopRun):
            Task(self.root.parent / 'unapproved')

    def test_other_app_shell_wrong_pid_window_denied(self):
        self.snapshot()
        for tool, args in [('shell', {}), ('launch_app', {'bundle_id': 'com.apple.Terminal'}),
                           ('list_windows', {'pid': 100}), ('click', {'pid': 99, 'window_id': 51})]:
            with self.assertRaises(StopRun): self.task.raw(tool, args)
        self.assertEqual(self.sent, [])

    def test_budget_and_restart_never_reset(self):
        for _ in range(30): self.task.raw('launch_app', {'bundle_id': BUNDLE})
        with self.assertRaises(StopRun): self.task.raw('launch_app', {'bundle_id': BUNDLE})
        restarted = Task(self.root, self.transport, lambda _: None, approved=True)
        self.assertEqual(restarted.used, 30)
        with self.assertRaises(StopRun): restarted.raw('launch_app', {'bundle_id': BUNDLE})
        self.assertEqual(len(self.sent), 30)

    def test_stop_blocks_even_first_dispatch_and_survives_restart(self):
        self.task.stop()
        with self.assertRaises(StopRun): self.task.raw('launch_app', {'bundle_id': BUNDLE})
        restarted = Task(self.root, self.transport, lambda _: None, approved=True)
        with self.assertRaises(StopRun): restarted.raw('launch_app', {'bundle_id': BUNDLE})
        self.assertEqual(self.sent, [])

    def test_stop_during_identity_check_prevents_dispatch(self):
        args = self.snapshot()
        self.task.identity = lambda _: self.task.stop()
        with self.assertRaises(StopRun): self.task.click(args)
        self.assertEqual(self.sent, [])

    def test_inflight_stop_does_not_wait_or_dispatch_next(self):
        entered, release = threading.Event(), threading.Event()
        def slow(*_):
            entered.set()
            self.assertTrue(release.wait(2))
            return {'bundle_id': BUNDLE, 'pid': 99}
        self.task.transport = slow
        errors = []
        def run():
            try: self.task.raw('launch_app', {'bundle_id': BUNDLE})
            except Exception as exc: errors.append(exc)
        worker = threading.Thread(target=run)
        worker.start()
        self.assertTrue(entered.wait(2))
        try:
            self.task.stop()
            self.assertEqual(len(self.rows()[-1]['inflight']), 1)
            with self.assertRaises(StopRun): self.task.raw('launch_app', {'bundle_id': BUNDLE})
        finally:
            release.set(); worker.join(2)
        self.assertEqual(errors, [])

    def test_stale_menu_and_wrong_token_denied(self):
        args = self.snapshot()
        self.task.observed_at -= 31
        with self.assertRaises(StopRun): self.task.click(args)
        args = self.snapshot('Quit')
        with self.assertRaises(StopRun): self.task.click(args)
        args = self.snapshot(); args['element_token'] = 'wrong'
        with self.assertRaises(StopRun): self.task.click(args)
        self.assertEqual(self.sent, [])

    def test_click_invalidates_observation(self):
        args = self.snapshot()
        self.task.click(args)
        with self.assertRaises(StopRun): self.task.click(args)
        self.assertEqual(self.sent, ['click'])

    def test_timeout_not_completed_and_no_blind_retry(self):
        args = self.snapshot()
        def timeout(*_): raise subprocess.TimeoutExpired('click', 35)
        self.task.transport = timeout
        with self.assertRaises(subprocess.TimeoutExpired): self.task.click(args)
        self.assertTrue(self.task.uncertain)
        self.assertFalse(any(row['event']=='completed_action' for row in self.rows()))
        self.task.transport = self.transport
        with self.assertRaises(StopRun): self.task.click(self.snapshot())
        self.assertEqual(self.sent, [])

    def test_driver_refusal_never_completed(self):
        self.task.transport = lambda *_: {'status': 'refused'}
        with self.assertRaises(StopRun): self.task.click(self.snapshot())
        self.assertFalse(any(row['event']=='completed_action' for row in self.rows()))

    def test_audit_write_failure_prevents_all_future_dispatch(self):
        with patch('c0_bridge.os.fsync', side_effect=OSError('audit unavailable')):
            with self.assertRaises(OSError): self.task.raw('launch_app', {'bundle_id': BUNDLE})
        with self.assertRaises(StopRun): self.task.raw('launch_app', {'bundle_id': BUNDLE})
        self.assertEqual(self.sent, [])

    def test_corrupt_or_foreign_ledger_refuses_restart(self):
        self.task.ledger.write_text('not json\n')
        with self.assertRaises(ValueError): Task(self.root, approved=True)
        self.task.ledger.write_text(json.dumps({'event':'dispatch','used':2,'run_id':'run'})+'\n')
        with self.assertRaises(StopRun): Task(self.root, approved=True)

    def test_file_must_match_fresh_display_no_overwrite_or_symlink(self):
        self.snapshot()
        with self.assertRaises(StopRun): self.task.write_result({'snapshot_id':'fresh','value':'999'})
        self.task.write_result({'snapshot_id':'fresh','value':'408'})
        self.assertEqual(self.task.read_result()['content'], '408\n')
        with self.assertRaises(FileExistsError): self.task.write_result({'snapshot_id':'fresh','value':'408'})
        self.assertTrue(self.task.stopped.is_set())

    def test_failed_observe_invalidates_previous_snapshot(self):
        args = self.snapshot()
        self.task.transport = lambda *_: {'status':'refused'}
        with self.assertRaises(StopRun): self.task.observe()
        self.assertIsNone(self.task.snapshot)
        with self.assertRaises(StopRun): self.task.click(args)

    def test_result_and_ledger_symlinks_refused(self):
        target = self.root.parent/'external.txt'
        target.write_text('private')
        (self.root/'result.txt').symlink_to(target)
        with self.assertRaises(StopRun): self.task.read_result()
        other = self.root.parent/'linked-run'
        other.mkdir()
        (other/'trace.jsonl').symlink_to(target)
        with self.assertRaises(StopRun): Task(other, approved=True)
        self.assertEqual(target.read_text(), 'private')

    def test_verifier_requires_actual_readback_and_complete_calls(self):
        self.snapshot()
        (self.root/'result.txt').write_text('408\n')
        for label in ['All Clear','1','2','Multiply','3','4','Equals']:
            self.task.record({'event':'completed_action','label':label})
        with patch.object(self.task, 'observe'):
            self.assertEqual(self.task.verify()['status'], 'UNVERIFIED')
            self.task.read_result()
            self.assertEqual(self.task.verify()['status'], 'SUCCEEDED')
            self.task.record({'event':'dispatch','tool':'click','used':2,'call_id':'pending'})
            self.assertEqual(self.task.verify()['status'], 'UNVERIFIED')


if __name__ == '__main__': unittest.main()
