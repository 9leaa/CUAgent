"""Real P7 trace/files and cleanup code; simulated Driver and native exit."""
import hashlib
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_handoff_evidence
from desktop_runtime import DesktopGuestRuntime
from desktop_app_cleanup import ApplicationIdentity


class HandoffCleanupTests(unittest.TestCase):
    def setUp(self):
        self.evidence = test_handoff_evidence.HandoffEvidenceTests()
        self.evidence.owner = '22222222-2222-4222-8222-222222222222'
        self.evidence.setUp()
        self.addCleanup(self.evidence.doCleanups)
        self.fixture = self.evidence.fixture
        self.runtime = DesktopGuestRuntime.__new__(DesktopGuestRuntime)
        self.runtime.lock = threading.RLock(); self.runtime.closed = False
        self.runtime.directory = self.evidence.root
        self.runtime.task = self.fixture.task
        self.runtime.controller = SimpleNamespace(gate=self.fixture.task.lease,
            existing=lambda: {'stopped': True})
        self.identity = ApplicationIdentity(10, 1790000000123456)
        self.runtime.application = self.identity; self.current = self.identity
        names = {'document': 'artifacts/handoff-' + self.fixture.run + '.txt', 'result': 'result.txt', 'trace': 'trace.jsonl'}
        self.hashes = {k: hashlib.sha256((self.evidence.root / v).read_bytes()).hexdigest() for k, v in names.items()}
        self.body = dict(sessionTerminal=True, sessionVerified=True, hashes=self.hashes)
        def terminate(identity):
            self.assertEqual(identity, self.identity); self.current = None; return True
        self.patches = [patch('desktop_runtime.read_identity', side_effect=lambda _: self.current),
            patch('desktop_runtime.request_terminate', side_effect=terminate),
            patch('desktop_runtime.inspect_guest_evidence', side_effect=AssertionError('P6 fallback forbidden'))]
        self.native_read, self.native_quit, self.p6 = [p.start() for p in self.patches]
        for p in self.patches: self.addCleanup(p.stop)

    def test_original_saved_p7_task_exits_once_without_budget_or_file_changes(self):
        before = {p: p.read_bytes() for p in self.evidence.root.rglob('*') if p.is_file()}
        used = self.fixture.task.used
        result = self.runtime.cleanup_application(self.body)
        self.assertEqual(result['status'], 'EXITED'); self.assertFalse(result['forced'])
        self.native_quit.assert_called_once(); self.p6.assert_not_called()
        self.assertEqual(used, self.fixture.task.used)
        self.assertTrue(all(p.read_bytes() == raw for p, raw in before.items()))
        with self.assertRaises(FileExistsError): self.runtime.cleanup_application(self.body)
        self.native_quit.assert_called_once()

    def test_changed_original_material_refuses_exit(self):
        (self.evidence.root / 'handoff-input.json').write_bytes(b'{}')
        result = self.runtime.cleanup_application(self.body)
        self.assertEqual(result['status'], 'REFUSED'); self.native_quit.assert_not_called()

    def test_changed_original_result_refuses_exit(self):
        (self.evidence.root / 'result.txt').write_bytes(b'changed')
        result = self.runtime.cleanup_application(self.body)
        self.assertEqual(result['status'], 'REFUSED'); self.native_quit.assert_not_called()

    def test_reused_pid_refuses_exit(self):
        self.current = ApplicationIdentity(10, self.identity.started_us + 1)
        result = self.runtime.cleanup_application(self.body)
        self.assertEqual(result['status'], 'REFUSED'); self.native_quit.assert_not_called()

    def test_pending_action_refuses_exit(self):
        self.fixture.task.inflight.add('synthetic-inflight')
        result = self.runtime.cleanup_application(self.body)
        self.assertEqual(result['status'], 'REFUSED'); self.native_quit.assert_not_called()

    def test_unknown_action_refuses_exit(self):
        self.fixture.task.uncertain = True
        result = self.runtime.cleanup_application(self.body)
        self.assertEqual(result['status'], 'REFUSED'); self.native_quit.assert_not_called()

    def test_wrong_host_verified_hash_refuses_exit(self):
        self.body['hashes'] = dict(self.hashes, document='0'*64)
        result = self.runtime.cleanup_application(self.body)
        self.assertEqual(result['status'], 'REFUSED'); self.native_quit.assert_not_called()
