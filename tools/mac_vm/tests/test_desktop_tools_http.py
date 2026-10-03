import http.client
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_control import LeaseController
from desktop_lease import DesktopTask
from desktop_tools_http import tools_server


class DesktopToolsHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.controller = LeaseController(self.root / 'lease.json', run_id='task',
                                          owner='worker', epoch=1, clock=lambda: 100)
        self.controller.renew(1)
        self.sent = []
        self.task = DesktopTask(self.root / 'task',
            lambda tool, args: self.sent.append(tool) or {}, lambda _: None,
            lease=self.controller.gate, approved=True, environment=lambda: None)
        self.token, self.control_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.server = tools_server(self.task, self.token, control_token=self.control_token,
                                   port=0, loopback_test=True)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01})
        self.thread.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.temp.cleanup()

    def request(self, body, *, token=None, path='/', headers=None, raw=False):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        try:
            auth = {'Authorization': 'Bearer ' + (self.token if token is None else token)}
            auth.update(headers or {})
            connection.request('POST', path, body if raw else json.dumps(body), auth)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_result_read_uses_original_admission_and_revocation(self):
        (self.task.directory / 'result.txt').write_text('synthetic\n')
        self.assertEqual(self.request({'op': 'read_result', 'args': {}}),
                         (200, {'content': 'synthetic\n', 'used': 1}))
        self.controller.revoke()
        self.assertEqual(self.request({'op': 'read_result', 'args': {}})[0], 409)
        self.assertEqual(self.task.used, 1)
        self.assertTrue(self.task.stopped.is_set())
        self.assertEqual(self.sent, [])

    def test_wrong_credentials_do_not_consume_budget(self):
        for token in ('', self.control_token, secrets.token_urlsafe(32)):
            self.assertEqual(self.request({'op': 'stop', 'args': {}}, token=token)[0], 403)
        self.assertFalse(self.task.stopped.is_set())
        self.assertEqual(self.task.used, 0)

    def test_rejected_tools_count_once_and_cannot_exceed_budget(self):
        for number in range(30):
            op = ('verify', 'renew', 'launch_app', 'type_text', 'save', 'write_result')[number % 6]
            self.assertEqual(self.request({'op': op, 'args': {}})[0], 409)
            self.assertEqual(self.task.used, number + 1)
        self.assertEqual(self.request({'op': 'read_result', 'args': {}})[0], 409)
        self.assertEqual(self.task.used, 30)
        self.assertEqual(self.sent, [])
        rows = [json.loads(row) for row in self.task.ledger.read_text().splitlines()]
        self.assertEqual(len([row for row in rows if row['event'] == 'dispatch']), 30)

    def test_malformed_envelopes_are_bounded_and_audited(self):
        requests = [([], {}), ({'op': 'stop', 'args': {}, 'owner': 'other'}, {}),
                    ({'op': 'stop', 'args': {'path': '/other'}}, {}),
                    ('{"op":"stop","op":"observe","args":{}}', {'raw': True}),
                    ({'op': 'stop', 'args': {}}, {'path': '/renew'}),
                    ({'op': 'stop', 'args': {}}, {'headers': {'Transfer-Encoding': 'chunked'}}),
                    ('x' * 32769, {'raw': True})]
        for body, options in requests:
            self.assertEqual(self.request(body, **options)[0], 409)
        self.assertEqual(self.task.used, len(requests))
        self.assertFalse(self.task.stopped.is_set())
        self.assertEqual(self.sent, [])

    def test_missing_result_failure_is_counted_only_once(self):
        self.assertEqual(self.request({'op': 'read_result', 'args': {}})[0], 409)
        self.assertEqual(self.task.used, 1)
        self.assertEqual(self.sent, [])

    def test_stop_does_not_wait_for_inflight_driver_and_blocks_next_request(self):
        entered, release = threading.Event(), threading.Event()
        result = []
        def transport(tool, args):
            self.sent.append(tool)
            entered.set()
            if not release.wait(3):
                raise TimeoutError('test transport stalled')
            return {'ok': True}
        # Only this test replaces observe's UI parsing, not final raw admission.
        self.task.transport = transport
        with patch.object(self.task, 'observe', side_effect=lambda: self.task.raw('launch_app', self.task.launch_args)):
            caller = threading.Thread(target=lambda: result.append(self.request({'op': 'observe', 'args': {}})))
            caller.start()
            try:
                self.assertTrue(entered.wait(2))
                self.assertEqual(self.request({'op': 'stop', 'args': {}}), (200, {'stopped': True}))
                self.assertTrue(self.task.inflight)
            finally:
                release.set()
                caller.join(3)
            self.assertEqual(result[0][0], 200)
            self.assertEqual(self.request({'op': 'observe', 'args': {}})[0], 409)
        self.assertEqual(self.sent, ['launch_app'])
        self.assertEqual(self.task.used, 1)

    def test_factory_rejects_unguarded_task_and_shared_credentials(self):
        with self.assertRaises(ValueError):
            tools_server(object(), self.token, control_token=self.control_token)
        with self.assertRaises(ValueError):
            tools_server(self.task, self.token, control_token=self.token)
        with self.assertRaises(ValueError):
            tools_server(self.task, self.token, control_token=self.control_token, loopback_test='yes')

    def test_duplicate_http_headers_are_rejected(self):
        for header, value, status in [('Authorization', 'Bearer ' + self.token, 403),
                                      ('Content-Length', '27', 409)]:
            connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
            try:
                body = b'{"op":"stop","args":{}}'
                connection.putrequest('POST', '/')
                connection.putheader('Authorization', 'Bearer ' + self.token)
                connection.putheader('Content-Length', str(len(body)))
                connection.putheader(header, value)
                connection.endheaders(body)
                response = connection.getresponse()
                self.assertEqual(response.status, status)
                response.read()
            finally:
                connection.close()
        self.assertFalse(self.task.stopped.is_set())
        self.assertEqual(self.task.used, 1)

    def test_revoke_between_internal_calls_prevents_second_dispatch(self):
        def transport(tool, args):
            self.sent.append(tool)
            self.controller.revoke()
            return {'ok': True}
        def observe():
            self.task.raw('launch_app', self.task.launch_args)
            return self.task.raw('launch_app', self.task.launch_args)
        self.task.transport = transport
        with patch.object(self.task, 'observe', side_effect=observe):
            self.assertEqual(self.request({'op': 'observe', 'args': {}})[0], 409)
        self.assertEqual(self.sent, ['launch_app'])
        self.assertEqual(self.task.used, 1)
        self.assertTrue(self.task.stopped.is_set())

    def test_reviewed_payloads_are_forwarded_without_mutation(self):
        for op, args in [('type_text', {'text': '汉' * 1365 + '\n', 'snapshot_id': 'fresh',
                                      'element_index': 1, 'element_token': 'body'}),
                         ('save', {'snapshot_id': 'fresh'}),
                         ('write_result', {'snapshot_id': 'fresh', 'value': '汉\n'})]:
            with patch.object(self.task, op, return_value={'ok': True}) as method:
                self.assertEqual(self.request({'op': op, 'args': args}), (200, {'ok': True}))
                method.assert_called_once_with(args)


if __name__ == '__main__':
    unittest.main()
