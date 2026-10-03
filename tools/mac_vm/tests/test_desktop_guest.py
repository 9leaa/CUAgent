import json
from pathlib import Path
import signal
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop_guest
from desktop_runtime import DesktopGuestRuntime

RUN = 'p2-11111111-1111-1111-1111-111111111111'
OWNER = '22222222-2222-2222-2222-222222222222'


class GuestLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        home = patch.object(Path, 'home', return_value=self.home)
        home.start()
        self.addCleanup(home.stop)

    def test_vm_identity_failure_precedes_all_writes(self):
        with patch.object(desktop_guest, 'require_vm', side_effect=RuntimeError('not VM')):
            with self.assertRaises(RuntimeError):
                desktop_guest.prepare_guest(RUN, OWNER, 1, approved=True)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_approval_and_identity_input_fail_before_writes(self):
        with patch.object(desktop_guest, 'require_vm'):
            for run, owner, epoch, approved in [(RUN, OWNER, 1, False), ('../other', OWNER, 1, True),
                                               (RUN, '../owner', 1, True), (RUN, OWNER, True, True)]:
                with self.assertRaises(ValueError):
                    desktop_guest.prepare_guest(run, owner, epoch, approved=approved)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_ready_private_tokens_no_lease_no_task_and_no_reuse(self):
        with patch.object(desktop_guest, 'require_vm'):
            runtime, server = desktop_guest.prepare_guest(RUN, OWNER, 1, approved=True)
            try:
                self.assertIsNone(runtime.task)
                self.assertIsNone(runtime.controller.existing())
                directory = self.home / 'C0Evidence' / RUN
                ready_raw = (directory / 'guest-ready.json').read_text()
                ready = json.loads(ready_raw)
                self.assertEqual(ready['controlHost'], '127.0.0.1')
                self.assertFalse(ready['activated'])
                tokens = [(directory / name).read_text() for name in ('bridge-token', 'control-token')]
                self.assertNotEqual(*tokens)
                for token in tokens:
                    self.assertNotIn(token, ready_raw)
                for name in ('bridge-token', 'control-token', 'guest-ready.json'):
                    self.assertEqual((directory / name).stat().st_mode & 0o077, 0)
                with self.assertRaises(FileExistsError):
                    desktop_guest.prepare_guest(RUN, OWNER, 1, approved=True)
                stopping = threading.Event()
                stopping.set()
                desktop_guest.serve_guest(runtime, server, stopping)
                self.assertTrue(runtime.closed)
                self.assertTrue(runtime.controller.existing()['stopped'])
            finally:
                server.server_close()
                runtime.close()

    def test_time_limit_and_cleanup_on_loop_failure(self):
        runtime, server = Mock(), Mock()
        desktop_guest.serve_guest(runtime, server, threading.Event(), clock=Mock(side_effect=[0, 3600]))
        server.handle_request.assert_not_called()
        runtime.close.assert_called_once()
        server.server_close.assert_called_once()
        runtime, server = Mock(), Mock()
        server.handle_request.side_effect = OSError('listener failed')
        with self.assertRaises(OSError):
            desktop_guest.serve_guest(runtime, server, threading.Event(), clock=lambda: 0)
        runtime.close.assert_called_once()
        server.server_close.assert_called_once()

    def test_main_signal_requests_graceful_shutdown_and_restores_handlers(self):
        previous = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
        runtime, server = Mock(), Mock()
        def serve(runtime_arg, server_arg, stopping):
            self.assertIs(runtime_arg, runtime)
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            self.assertTrue(stopping.is_set())
        with patch.object(desktop_guest, 'prepare_guest', return_value=(runtime, server)), \
                patch.object(desktop_guest, 'serve_guest', side_effect=serve), patch('builtins.print'):
            self.assertEqual(desktop_guest.main(['--run', RUN, '--owner', OWNER, '--epoch', '1', '--approve-task']), 0)
        for number, handler in previous.items():
            self.assertEqual(signal.getsignal(number), handler)


if __name__ == '__main__':
    unittest.main()
