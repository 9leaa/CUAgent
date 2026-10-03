import http.client
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_control import LeaseController
from desktop_control_http import control_server
from driver_smoke import StopRun


class ControlHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = 100.0
        self.controller = LeaseController(Path(self.temp.name).resolve() / 'lease.json',
            run_id='task', owner='worker', epoch=1, clock=lambda: self.now)
        self.token = secrets.token_urlsafe(32)
        self.server = control_server(self.controller, self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01})
        self.thread.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3)
        self.temp.cleanup()

    def request(self, method, path, body=None, token=None, extra=None):
        if path == '/renew' and isinstance(body, dict):
            body = {'notAfterMs': 120000, **body}
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        try:
            headers = {'Authorization': 'Bearer ' + (self.token if token is None else token)}
            headers.update(extra or {})
            connection.request(method, path, None if body is None else json.dumps(body), headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_real_http_grant_inspect_duplicate_revoke_and_gate(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        binding = dict(version=1, runId='task', owner='worker', epoch=1)
        self.assertEqual(self.request('GET', '/lease'), (200, {'lease': None, 'clockMs': 100000, 'binding': binding}))
        status, first = self.request('POST', '/renew', {'sequence': 1, 'ttlMs': 20000})
        self.assertEqual(status, 200)
        self.controller.gate.check()
        self.now = 105
        self.assertEqual(self.request('POST', '/renew', {'sequence': 1, 'ttlMs': 20000}), (200, first))
        self.assertEqual(self.request('GET', '/lease'), (200, {**first, 'clockMs': 105000, 'binding': binding}))
        status, stopped = self.request('POST', '/revoke', {})
        self.assertEqual(status, 200); self.assertTrue(stopped['lease']['stopped'])
        self.assertEqual(self.request('POST', '/revoke', {}), (200, stopped))
        with self.assertRaises(StopRun): self.controller.gate.check()
        self.assertEqual(self.request('POST', '/renew', {'sequence': 2, 'ttlMs': 20000})[0], 409)

    def test_model_or_missing_credentials_cannot_control(self):
        for token in ('', 'model-token', 'verifier-token'):
            self.assertEqual(self.request('POST', '/renew', {'sequence': 1, 'ttlMs': 20000}, token)[0], 403)
            self.assertEqual(self.request('POST', '/revoke', {}, token)[0], 403)
            self.assertEqual(self.request('GET', '/lease', token=token)[0], 403)
        self.assertFalse(self.controller.path.exists())

    def test_tools_paths_and_authority_overrides_rejected(self):
        for path in ('/observe', '/type_text', '/verify', '/lease?path=other'):
            self.assertEqual(self.request('POST', path, {})[0], 404)
        for body in ([], {'sequence': 1, 'ttlMs': 20000, 'owner': 'other'},
                     {'sequence': True, 'ttlMs': 20000}, {'sequence': 1, 'ttlMs': 30001}):
            self.assertEqual(self.request('POST', '/renew', body)[0], 409)
        self.assertEqual(self.request('POST', '/revoke', {'path': '/other'})[0], 409)
        self.assertFalse(self.controller.path.exists())

    def test_oversize_and_chunked_bodies_rejected_without_write(self):
        self.assertEqual(self.request('POST', '/renew', {'data': 'x' * 4097})[0], 409)
        self.assertEqual(self.request('POST', '/renew', {}, extra={'Transfer-Encoding': 'chunked'})[0], 409)
        self.assertFalse(self.controller.path.exists())

    def test_expired_permission_cannot_be_extended_over_http(self):
        self.request('POST', '/renew', {'sequence': 1, 'ttlMs': 20000})
        self.now = 120
        self.assertEqual(self.request('POST', '/renew', {'sequence': 2, 'ttlMs': 20000})[0], 409)
        self.assertTrue(self.request('GET', '/lease')[1]['lease']['stopped'])

    def test_delayed_initial_request_is_not_granted_from_arrival_time(self):
        self.now = 120
        self.assertEqual(self.request('POST', '/renew', {'sequence': 1, 'ttlMs': 20000})[0], 409)
        self.assertFalse(self.controller.path.exists())


if __name__ == '__main__':
    unittest.main()
