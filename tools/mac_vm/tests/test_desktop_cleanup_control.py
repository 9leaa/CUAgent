"""Real local control HTTP and files; GUI/native evidence is simulated."""
import hashlib
import http.client
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_app_cleanup import ApplicationIdentity
from desktop_control import LeaseController
from desktop_control_http import control_server
from desktop_runtime import DesktopGuestRuntime


class CleanupControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.run = self.root / 'p2-11111111-1111-1111-1111-111111111111'
        self.run.mkdir(mode=0o700)
        self.controller = LeaseController(self.run / 'lease.json', run_id=self.run.name,
            owner='22222222-2222-2222-2222-222222222222', epoch=1, clock=lambda: 100)
        self.controller.revoke()
        self.model, self.control = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.runtime = DesktopGuestRuntime(self.run, self.controller, model_token=self.model,
            control_token=self.control, shared_lock=self.root / 'bridge.lock', loopback_test=True)
        stopped = threading.Event(); stopped.set()
        self.runtime.task = SimpleNamespace(dispatch_lock=threading.RLock(), stopped=stopped,
            inflight=set(), uncertain=False, used=10, stop=stopped.set)
        self.identity = ApplicationIdentity(123, 1790000000123456)
        self.runtime.application = self.identity
        self.current = self.identity
        self.document_name = 'artifacts/handoff-' + self.run.name + '.txt'
        (self.run / 'artifacts').mkdir(mode=0o700)
        (self.run / self.document_name).write_bytes(b'approved\n')
        (self.run / 'result.txt').write_bytes(b'approved\n\n')
        (self.run / 'trace.jsonl').write_bytes(b'synthetic evidence\n')
        self.names = {'document': self.document_name, 'result': 'result.txt', 'trace': 'trace.jsonl'}
        self.hashes = {key: hashlib.sha256((self.run / name).read_bytes()).hexdigest()
                       for key, name in self.names.items()}
        self.body = dict(sessionTerminal=True, sessionVerified=True, hashes=self.hashes)
        def evidence(directory, *, run_id, expected):
            self.assertEqual(directory, self.run)
            self.assertEqual(run_id, self.run.name)
            self.assertEqual(expected, b'approved\n')
            return {'vmStatus': 'VERIFIED', 'rawCalls': 10, 'files': {
                name: {'sha256': hashlib.sha256((self.run / name).read_bytes()).hexdigest()}
                for name in self.names.values()}}
        self.patches = [patch('desktop_runtime.inspect_guest_evidence', side_effect=evidence),
                        patch('desktop_runtime.read_identity', side_effect=lambda _: self.current),
                        patch('desktop_runtime.request_terminate', side_effect=self.terminate)]
        self.verify, self.native_read, self.native_quit = [p.start() for p in self.patches]
        self.server = control_server(self.controller, self.control, runtime=self.runtime)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01})
        self.thread.start()
        self.addCleanup(self.cleanup)

    def terminate(self, identity):
        self.assertEqual(identity, self.identity)
        self.current = None
        return True

    def cleanup(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3)
        self.runtime.task.inflight.clear()
        self.runtime.close()
        for p in self.patches: p.stop()
        self.temp.cleanup()

    def request(self, body=None, token=None, raw=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            connection.request('POST', '/cleanup-app', raw if raw is not None else json.dumps(body or self.body),
                               {'Authorization': 'Bearer ' + (token or self.control)})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_verified_control_quits_once_without_changing_trace_or_budget(self):
        before = (self.run / 'trace.jsonl').read_bytes()
        code, result = self.request()
        self.assertEqual((code, result['status']), (200, 'EXITED'))
        self.native_quit.assert_called_once_with(self.identity)
        self.assertEqual(self.runtime.task.used, 10)
        self.assertEqual((self.run / 'trace.jsonl').read_bytes(), before)
        self.assertFalse(self.runtime.closed)
        self.assertGreaterEqual(self.verify.call_count, 3)
        self.assertEqual(self.request()[0], 409)
        self.native_quit.assert_called_once()

    def test_model_credential_refused_before_reads_or_native_actions(self):
        self.assertEqual(self.request(token=self.model)[0], 403)
        self.verify.assert_not_called(); self.native_read.assert_not_called(); self.native_quit.assert_not_called()

    def test_unverified_host_claims_and_extra_fields_refused(self):
        for body in [dict(self.body, sessionVerified=False), dict(self.body, sessionTerminal=1),
                     dict(self.body, extra='permission')]:
            self.assertEqual(self.request(body)[0], 409)
        self.native_quit.assert_not_called()

    def test_duplicate_claims_refused(self):
        self.assertEqual(self.request(raw='{"sessionVerified":false,"sessionVerified":true}')[0], 409)
        self.native_quit.assert_not_called()

    def test_active_or_inflight_runtime_cannot_quit(self):
        self.runtime.task.inflight.add('pending')
        code, result = self.request()
        self.assertEqual((code, result['status']), (200, 'REFUSED'))
        self.native_quit.assert_not_called()

    def test_failed_independent_guest_verification_refuses(self):
        self.verify.side_effect = ValueError('bad GUI evidence')
        self.assertEqual(self.request()[1]['status'], 'REFUSED')
        self.native_quit.assert_not_called()

    def test_changed_host_hash_refuses(self):
        self.body['hashes'] = dict(self.hashes, document='f' * 64)
        self.assertEqual(self.request()[1]['status'], 'REFUSED')
        self.native_quit.assert_not_called()

    def test_missing_owned_identity_refuses(self):
        self.runtime.application = None
        self.assertEqual(self.request()[0], 409)
        self.native_quit.assert_not_called()

    def test_guest_budget_mismatch_refuses(self):
        self.runtime.task.used = 11
        self.assertEqual(self.request()[1]['status'], 'REFUSED')
        self.native_quit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
