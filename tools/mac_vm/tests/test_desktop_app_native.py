import json
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_app_cleanup import ApplicationIdentity
import desktop_app_native as native


class NativeAppTests(unittest.TestCase):
    def setUp(self):
        self.vm = patch.object(native, 'require_vm').start()
        self.process = patch.object(native.subprocess, 'run').start()
        self.signal = patch.object(native.os, 'kill').start()
        self.addCleanup(patch.stopall)
        self.identity = ApplicationIdentity(123, 1790000000123456)
        self.response(dict(pid=123, startedUs=self.identity.started_us, executable=native.EXECUTABLE))

    def response(self, value):
        self.process.return_value = subprocess.CompletedProcess([], 0, json.dumps(value).encode())

    def test_native_identity_fixed_script_and_timeout(self):
        self.assertEqual(native.read_identity(123), self.identity)
        self.vm.assert_called_once()
        args, kwargs = self.process.call_args
        self.assertEqual(args[0][:4], ['/usr/bin/osascript', '-l', 'JavaScript', '-e'])
        self.assertIn('const pid = 123;', args[0][4])
        self.assertIn('const expected = null;', args[0][4])
        self.assertEqual(kwargs['timeout'], 3)
        self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
        self.assertNotIn('shell', kwargs)
        self.signal.assert_not_called()

    def test_host_denial_precedes_any_process_access(self):
        self.vm.side_effect = RuntimeError('host')
        with self.assertRaises(RuntimeError):
            native.read_identity(123)
        with self.assertRaises(RuntimeError):
            native.request_terminate(self.identity)
        self.process.assert_not_called()
        self.signal.assert_not_called()

    def test_same_pid_document_open_uses_noninteractive_event_not_app_lookup(self):
        run = 'p2-11111111-1111-1111-1111-111111111111'
        path = Path('/Users/mvpagent/C0Evidence') / run / 'artifacts' / ('handoff-' + run + '.txt')
        self.response({'accepted': True})
        info = SimpleNamespace(st_mode=0o100600, st_uid=native.os.getuid(), st_nlink=1, st_size=20)
        with patch.object(Path, 'resolve', autospec=True, side_effect=lambda value, **_: value), patch.object(Path, 'stat', return_value=info):
            self.assertTrue(native.request_open_document(self.identity, path))
        script = self.process.call_args.args[0][4]
        self.assertIn('descriptorWithProcessIdentifier(pid)', script)
        self.assertIn('NSAppleEventSendNeverInteract', script)
        self.assertIn('const expected = ' + str(self.identity.started_us), script)
        self.assertIn(str(path), script)
        self.assertNotIn('app.terminate', script)
        self.assertNotIn('Application(', script)
        self.assertNotIn('creates_new_application', script)

    def test_native_open_wrong_path_or_host_never_dispatches(self):
        with self.assertRaises(ValueError): native.request_open_document(self.identity, '/tmp/arbitrary.txt')
        self.vm.side_effect = RuntimeError('host denied')
        with self.assertRaises(RuntimeError): native.request_open_document(self.identity, '/tmp/arbitrary.txt')
        self.process.assert_not_called()
        self.signal.assert_not_called()

    def test_missing_app_is_not_missing_process(self):
        self.response({'absent': True})
        with self.assertRaisesRegex(RuntimeError, 'IDENTITY_UNAVAILABLE'):
            native.read_identity(123)
        self.signal.assert_called_once_with(123, 0)

    def test_confirmed_process_absent(self):
        self.response({'absent': True})
        self.signal.side_effect = ProcessLookupError()
        self.assertIsNone(native.read_identity(123))

    def test_permission_error_does_not_mean_absent(self):
        self.response({'absent': True})
        self.signal.side_effect = PermissionError('private')
        with self.assertRaisesRegex(RuntimeError, '^NATIVE_PROCESS_PRESENCE_UNKNOWN$'):
            native.read_identity(123)

    def test_termination_checks_birth_in_same_script_and_only_normal_quit(self):
        self.response({'accepted': True})
        self.assertTrue(native.request_terminate(self.identity))
        script = self.process.call_args.args[0][4]
        self.assertIn('const expected = 1790000000123456;', script)
        self.assertLess(script.index('started !== expected'), script.index('app.terminate'))
        self.assertNotIn('forceTerminate', script)
        self.assertNotIn('System Events', script)
        self.process.assert_called_once()

    def test_quit_refusal_returned_without_force(self):
        self.response({'accepted': False})
        self.assertFalse(native.request_terminate(self.identity))
        self.process.assert_called_once()

    def test_timeout_is_unknown_without_retry_or_stderr(self):
        self.process.side_effect = subprocess.TimeoutExpired('private command', 3)
        with self.assertRaisesRegex(RuntimeError, '^NATIVE_APP_RESPONSE_UNCONFIRMED$'):
            native.request_terminate(self.identity)
        self.process.assert_called_once()

    def test_malformed_query_identity_rejected(self):
        for value in [None, {}, {'absent': 1}, {'absent': True, 'extra': 1},
                      {'pid': True, 'startedUs': 1, 'executable': native.EXECUTABLE},
                      {'pid': 124, 'startedUs': 1, 'executable': native.EXECUTABLE},
                      {'pid': 123, 'startedUs': 1.5, 'executable': native.EXECUTABLE},
                      {'pid': 123, 'startedUs': 1, 'executable': '/other'}]:
            with self.subTest(value=value):
                self.response(value)
                with self.assertRaises((RuntimeError, ValueError)):
                    native.read_identity(123)

    def test_bad_quit_response_is_unknown(self):
        for value in [{'absent': True}, {'accepted': 1}, {'accepted': True, 'extra': 1}, None]:
            self.response(value)
            with self.assertRaises(RuntimeError):
                native.request_terminate(self.identity)

    def test_duplicate_json_nonzero_and_large_output_rejected(self):
        for status, data in [(0, b'{"accepted":false,"accepted":true}'), (1, b'private'),
                             (0, b' ' * 4097), (0, b'not json')]:
            self.process.return_value = subprocess.CompletedProcess([], status, data)
            with self.assertRaisesRegex(RuntimeError, '^NATIVE_APP_RESPONSE_UNCONFIRMED$'):
                native.request_terminate(self.identity)

    def test_invalid_pid_never_reaches_system(self):
        for pid in [True, 0, -1, 2**31, '123; injected']:
            with self.assertRaises(ValueError):
                native.read_identity(pid)
        self.process.assert_not_called()

    def test_failure_envelope_is_bounded_and_not_a_success(self):
        for phase in ('identity', 'build', 'send', 'reply'):
            for code in (None, -1743, -1708, -(2**31), 2**31-1):
                self.response({'nativeFailure': {'phase': phase, 'code': code}})
                with self.assertRaises(native.NativeRequestError) as caught:
                    native.read_identity(123)
                self.assertEqual(caught.exception.diagnostic, {'phase': phase, 'code': code})
                self.assertEqual(str(caught.exception), 'NATIVE_APP_RESPONSE_UNCONFIRMED')

    def test_failure_envelope_rejects_private_text_and_wrong_types(self):
        for failure in ({'phase':'send','code':True}, {'phase':'send','code':2**31},
                        {'phase':'send','code':-2**31-1}, {'phase':'send','code':'secret'},
                        {'phase':'send','code':0,'message':'secret'},
                        {'phase':'secret','code':None}, {'phase':[],'code':None}, None):
            self.response({'nativeFailure': failure})
            with self.assertRaises(native.NativeRequestError) as caught:
                native.read_identity(123)
            self.assertEqual(caught.exception.diagnostic, {'phase':'protocol','code':None})
            self.assertNotIn('secret', str(caught.exception))

    def test_process_failures_preserve_safe_phase_without_retry(self):
        for failure, phase in ((OSError('secret'), 'spawn'),
                               (subprocess.TimeoutExpired('secret',3), 'timeout')):
            self.process.reset_mock(); self.process.side_effect=failure
            with self.assertRaises(native.NativeRequestError) as caught:
                native.read_identity(123)
            self.assertEqual(caught.exception.diagnostic, {'phase':phase,'code':None})
            self.process.assert_called_once()


if __name__ == '__main__':
    unittest.main()
