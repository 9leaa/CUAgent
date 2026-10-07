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
from desktop_control_http import control_server
from desktop_lease import DesktopTask
from desktop_runtime import DesktopGuestRuntime
from desktop_app_cleanup import ApplicationIdentity
from desktop_tools_http import tools_server


class DesktopRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.run = self.root / 'task'
        self.run.mkdir(mode=0o700)
        self.controller = LeaseController(self.run / 'lease.json', run_id='task', owner='worker', epoch=1,
                                          clock=lambda: 100)
        self.model, self.control = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.constructed = 0
        self.sent = []
        def factory(directory, **kwargs):
            self.constructed += 1
            return DesktopTask(directory, lambda tool, args: self.sent.append(tool) or {},
                               lambda _: None, environment=lambda: None, **kwargs)
        self.kwargs = dict(model_token=self.model, control_token=self.control, shared_lock=self.root / 'bridge.lock',
                           port=0, loopback_test=True, task_factory=factory)
        self.runtime = DesktopGuestRuntime(self.run, self.controller, **self.kwargs)
        self.server = control_server(self.controller, self.control, runtime=self.runtime)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01})
        self.thread.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.runtime.close()
        self.temp.cleanup()

    def request(self, method, path, body=None, token=None, port=None):
        connection = http.client.HTTPConnection('127.0.0.1', port or self.server.server_port, timeout=3)
        try:
            connection.request(method, path, json.dumps(body) if body is not None else None,
                               {'Authorization': 'Bearer ' + (token or self.control)})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def grant(self):
        self.assertEqual(self.request('POST', '/renew', {'sequence': 1, 'ttlMs': 20000, 'notAfterMs': 120000})[0], 200)

    def test_grant_activate_original_tool_protocol_status_revoke(self):
        self.assertEqual(self.constructed, 0)
        self.assertFalse(self.request('GET', '/status')[1]['active'])
        self.grant()
        code, state = self.request('POST', '/activate', {})
        self.assertEqual(code, 200)
        self.assertTrue(state['active'])
        self.assertEqual(self.constructed, 1)
        (self.run / 'result.txt').write_text('synthetic\n')
        self.assertEqual(self.request('POST', '/', {'op': 'read_result', 'args': {}},
                                     token=self.model, port=state['modelPort'])[0], 200)
        self.assertEqual(self.request('GET', '/status')[1]['rawCalls'], 1)
        self.assertEqual(self.request('POST', '/revoke', {})[0], 200)
        self.assertTrue(self.request('GET', '/status')[1]['stopped'])
        self.assertEqual(self.request('POST', '/', {'op': 'read_result', 'args': {}},
                                     token=self.model, port=state['modelPort'])[0], 409)
        self.assertEqual(self.sent, [])

    def test_activation_without_permission_is_persistently_non_replayable(self):
        self.assertEqual(self.request('POST', '/activate', {})[0], 409)
        self.assertEqual(self.constructed, 0)
        self.assertTrue((self.run / 'guest-activation-intent.json').exists())
        self.assertTrue(self.controller.existing()['stopped'])
        self.runtime.close()
        self.runtime = DesktopGuestRuntime(self.run, self.controller, **self.kwargs)
        with self.assertRaises(FileExistsError):
            self.runtime.activate()
        self.assertEqual(self.constructed, 0)

    def test_model_token_cannot_activate_status_or_renew(self):
        for method, path, body in [('POST', '/activate', {}), ('GET', '/status', None),
                                    ('POST', '/renew', {}), ('POST', '/revoke', {})]:
            self.assertEqual(self.request(method, path, body, token=self.model)[0], 403)
        self.assertEqual(self.constructed, 0)
        self.assertFalse((self.run / 'guest-activation-intent.json').exists())

    def test_p6_does_not_gain_handoff_material_tool(self):
        self.grant()
        state = self.runtime.activate()
        for used, op in enumerate(('read_materials', 'reopen', 'locate_quote', 'check_draft'), 1):
            code, result = self.request('POST', '/', {'op': op, 'args': {}},
                                        token=self.model, port=state['modelPort'])
            self.assertEqual(code, 409)
            self.assertEqual(result['used'], used)
        self.assertEqual(self.sent, [])

    def test_exclusive_lock_and_single_activation(self):
        with self.assertRaises(BlockingIOError):
            DesktopGuestRuntime(self.run, self.controller, **self.kwargs)
        self.grant()
        self.assertEqual(self.request('POST', '/activate', {})[0], 200)
        self.assertEqual(self.request('POST', '/activate', {})[0], 409)
        self.assertEqual(self.constructed, 1)

    def test_bind_failure_revokes_without_retry(self):
        self.grant()
        with patch('desktop_runtime.tools_server', side_effect=OSError('bind failed')):
            self.assertEqual(self.request('POST', '/activate', {})[0], 409)
        self.assertTrue(self.controller.existing()['stopped'])
        self.assertTrue(self.runtime.task.stopped.is_set())
        self.assertFalse(self.runtime.status()['active'])
        self.assertEqual(self.request('POST', '/activate', {})[0], 409)
        self.assertEqual(self.constructed, 1)

    def test_pending_calls_retain_shared_lock_on_close(self):
        self.grant()
        self.runtime.activate()
        # Represent a held transport; final-admission/in-flight HTTP behavior is
        # separately exercised in test_desktop_tools_http with a real thread.
        self.runtime.task.inflight.add('held-test-call')
        self.assertEqual(self.runtime.status()['pendingCalls'], 1)
        with self.assertRaises(RuntimeError):
            self.runtime.close()
        with self.assertRaises(BlockingIOError):
            DesktopGuestRuntime(self.run, self.controller, **self.kwargs)
        self.assertFalse(self.runtime.status()['active'])
        self.runtime.task.inflight.clear()
        self.runtime.close()
        self.assertTrue(self.runtime.status()['stopped'])
        self.assertTrue((self.root / 'bridge.lock.quarantine').is_file())
        with self.assertRaisesRegex(ValueError, 'quarantined'):
            DesktopGuestRuntime(self.run, self.controller, **self.kwargs)

    def test_capture_new_application_private_bound_record(self):
        identity = ApplicationIdentity(123, 1001)
        with patch('desktop_runtime.read_identity', return_value=identity), \
                patch('desktop_runtime.time.time_ns', return_value=1002000):
            self.runtime.capture_application(123, 1000)
            self.assertEqual(self.runtime.application, identity)
            path = self.run / 'owned-application.json'
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            value = json.loads(path.read_text())
            self.assertEqual((value['runId'], value['owner'], value['epoch']), ('task', 'worker', 1))
            self.assertEqual((value['pid'], value['startedUs'], value['launchStartedUs']), (123, 1001, 1000))
            with self.assertRaises(ValueError):
                self.runtime.capture_application(123, 1000)

    def test_capture_old_future_or_absent_app_denied(self):
        for identity in (None, ApplicationIdentity(123, 999), ApplicationIdentity(123, 1003)):
            with patch('desktop_runtime.read_identity', return_value=identity), \
                    patch('desktop_runtime.time.time_ns', return_value=1002000):
                with self.assertRaises(ValueError):
                    self.runtime.capture_application(123, 1000)
                self.assertIsNone(self.runtime.application)
                self.assertFalse((self.run / 'owned-application.json').exists())

    def test_capture_partial_existing_record_not_overwritten(self):
        path = self.run / 'owned-application.json'
        path.write_text('{')
        with patch('desktop_runtime.read_identity', return_value=ApplicationIdentity(123, 1001)), \
                patch('desktop_runtime.time.time_ns', return_value=1002000):
            with self.assertRaises(FileExistsError):
                self.runtime.capture_application(123, 1000)
        self.assertEqual(path.read_text(), '{')
        self.assertIsNone(self.runtime.application)

    def test_production_factory_gets_observer_without_system_operation(self):
        self.grant()
        # Only construction is exercised; no native identity or GUI call occurs.
        self.runtime.loopback_test = False
        factory = self.runtime.task_factory
        def local_server(task, token, **kwargs):
            kwargs['loopback_test'] = True
            return tools_server(task, token, **kwargs)
        with patch.object(self.runtime, 'task_factory', wraps=factory) as create, \
                patch('desktop_runtime.tools_server', side_effect=local_server), \
                patch('desktop_runtime.read_identity') as native:
            self.runtime.activate()
            self.assertEqual(create.call_args.kwargs['launch_observer'], self.runtime.capture_application)
            native.assert_not_called()


if __name__ == '__main__':
    unittest.main()
