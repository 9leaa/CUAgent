"""Bounded P6 readiness using synthetic Driver responses, not VM acceptance."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_lease import DesktopTask, LeaseGate
from driver_smoke import StopRun


class WindowReadinessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.lease = self.root / 'lease.json'
        self.lease.write_text(json.dumps(dict(version=1, runId='task', owner='owner', epoch=1,
                                             stopped=False, expiresAt=120000)))
        self.lease.chmod(0o600)
        self.sent = []
        self.clock = 0
        self.polls = 0
        self.visible_after = 1
        self.mutation = None
        self.task = DesktopTask(self.root / 'task', self.transport, lambda _: None,
            lease=LeaseGate(self.lease, run_id='task', owner='owner', epoch=1, clock=lambda: 100),
            approved=True, environment=lambda: None)
        self.patchers = [patch('desktop_lease.time.monotonic', side_effect=lambda: self.clock),
                         patch('desktop_lease.time.sleep', side_effect=self.wait)]
        for p in self.patchers:
            p.start(); self.addCleanup(p.stop)

    def wait(self, seconds):
        self.clock += seconds
        if self.mutation == 'stop': self.task.stop()
        if self.mutation == 'revoke':
            data = json.loads(self.lease.read_text()); data['stopped'] = True
            self.lease.write_text(json.dumps(data))
        if self.mutation == 'identity-loss':
            def changed(_): raise StopRun('BLOCKED', 'identity changed')
            self.task.identity = changed

    def transport(self, tool, args):
        self.sent.append((tool, dict(args)))
        if tool == 'launch_app':
            return {'bundle_id': 'wrong' if self.mutation == 'launch-identity' else 'com.apple.TextEdit', 'pid': 10}
        if tool == 'list_windows':
            self.polls += 1
            window = dict(pid=10, window_id=20, title=self.task.case.title,
                          app_name='TextEdit', is_on_screen=True)
            if self.mutation == 'malformed': return {'windows': [None]}
            if self.mutation == 'other-pid': window['pid'] = 99
            if self.mutation == 'other-title': window['title'] = 'old.txt'
            if self.mutation == 'other-app': window['app_name'] = 'Other'
            if self.mutation == 'hidden': window['is_on_screen'] = False
            if self.mutation == 'late': self.clock += 6
            if self.mutation == 'ambiguous': return {'windows': [window, dict(window, window_id=21)]}
            return {'windows': [window] if self.polls >= self.visible_after else []}
        if tool == 'get_window_state':
            Path(args['screenshot_out_file']).write_bytes(b'\x89PNG\r\n\x1a\nSYNTHETIC')
            return dict(pid=10, window_id=20, app_name='TextEdit', window_title=self.task.case.title,
                        screenshot_frame_valid=True, snapshot_id='fresh', tree_markdown='AXWindow')
        raise AssertionError('unexpected action')

    def test_delayed_window_uses_original_pid_one_launch_and_counts_all_queries(self):
        self.visible_after = 3
        result = self.task.observe()
        self.assertEqual(self.task.used, 5)
        self.assertEqual(result['state']['window_id'], 20)
        self.assertEqual([t for t, _ in self.sent], ['launch_app', *(['list_windows'] * 3), 'get_window_state'])
        self.assertTrue(all(a.get('pid') == 10 for t, a in self.sent if t != 'launch_app'))
        self.task.observe()
        self.assertEqual([t for t, _ in self.sent].count('launch_app'), 1)
        self.assertEqual([t for t, _ in self.sent].count('list_windows'), 3)

    def test_absent_window_stops_after_three_queries_and_cannot_relaunch(self):
        self.visible_after = 4
        with self.assertRaises(StopRun): self.task.observe()
        self.assertEqual(self.task.used, 4)
        self.assertTrue(self.task.stopped.is_set())
        before = list(self.sent)
        with self.assertRaises(StopRun): self.task.observe()
        self.assertEqual(self.sent, before)

    def test_wrong_or_invisible_windows_are_never_bound(self):
        for mutation in ('other-pid', 'other-title', 'other-app', 'hidden'):
            # Separate fresh instances required; stopped tasks cannot be reused.
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                old = self.task
                self.task = DesktopTask(Path(tmp) / 'task', self.transport, lambda _: None,
                    lease=LeaseGate(self.lease, run_id='task', owner='owner', epoch=1, clock=lambda: 100),
                    approved=True, environment=lambda: None)
                self.mutation = mutation
                with self.assertRaises(StopRun): self.task.observe()
                self.assertIsNone(self.task.window)
                self.assertEqual(self.task.used, 4)
                self.task = old

    def test_malformed_ambiguous_late_or_wrong_launch_never_retries_action(self):
        for mutation in ('malformed', 'ambiguous', 'late', 'launch-identity'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                self.task = DesktopTask(Path(tmp) / 'task', self.transport, lambda _: None,
                    lease=LeaseGate(self.lease, run_id='task', owner='owner', epoch=1, clock=lambda: 100),
                    approved=True, environment=lambda: None)
                self.mutation = mutation
                with self.assertRaises(StopRun): self.task.observe()
                self.assertIsNone(self.task.window)
                self.assertEqual(self.task.used, 1 if mutation == 'launch-identity' else 2)

    def test_stop_lease_and_identity_checked_before_each_query(self):
        for mutation in ('stop', 'revoke', 'identity-loss'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                data = json.loads(self.lease.read_text()); data['stopped'] = False
                self.lease.write_text(json.dumps(data))
                self.task = DesktopTask(Path(tmp) / 'task', self.transport, lambda _: None,
                    lease=LeaseGate(self.lease, run_id='task', owner='owner', epoch=1, clock=lambda: 100),
                    approved=True, environment=lambda: None)
                self.mutation, self.visible_after, self.polls = mutation, 3, 0
                with self.assertRaises(StopRun): self.task.observe()
                self.assertEqual(self.task.used, 2)
                self.assertTrue(self.task.stopped.is_set())

    def test_queries_cannot_exceed_original_budget(self):
        # Real admissions consume the first 28 calls, not a fabricated used counter.
        for _ in range(28): self.task.raw('launch_app', self.task.launch_args)
        self.visible_after = 3
        with self.assertRaises(StopRun): self.task.observe()
        self.assertEqual(self.task.used, 30)
        self.assertEqual(self.polls, 1)


if __name__ == '__main__': unittest.main()
