import ctypes
import json
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.windowserver_probe import Native, Point, isolated, query


class ProbeTests(unittest.TestCase):
    def native(self, *, connection=3, found=(0, 123, 8), owner=(0, 468)):
        return SimpleNamespace(main=Mock(return_value=connection),
                               find=Mock(return_value=found), pid=Mock(return_value=owner))

    def test_point_layout(self):
        self.assertEqual(ctypes.sizeof(Point), 16)
        self.assertEqual(Point.y.offset, 8)

    def test_native_missing_symbol_fails_closed(self):
        with patch("backend.windowserver_probe.sys.platform", "darwin"), patch(
            "backend.windowserver_probe.ctypes.CDLL", return_value=SimpleNamespace()
        ), self.assertRaises(AttributeError):
            Native()

    def test_native_signature_and_single_unfiltered_query(self):
        library = SimpleNamespace(SLSMainConnectionID=Mock(return_value=3),
                                  SLSFindWindowAndOwner=Mock(return_value=1),
                                  SLSConnectionGetPID=Mock(return_value=1))
        with patch("backend.windowserver_probe.sys.platform", "darwin"), patch(
            "backend.windowserver_probe.ctypes.CDLL", return_value=library
        ):
            native = Native()
            self.assertEqual(native.find(3, 1, 2), (1, 0, 0))
        self.assertEqual(library.SLSFindWindowAndOwner.call_args.args[:4], (3, 0, 1, 0))
        self.assertEqual(len(library.SLSFindWindowAndOwner.argtypes), 8)
        self.assertEqual(library.SLSFindWindowAndOwner.restype, ctypes.c_int32)

    def test_real_subprocess_timeout_is_reaped(self):
        def runner(command, **kwargs):
            return subprocess.run([sys.executable, "-c", "import time; time.sleep(10)"], **kwargs)
        result = isolated(1, 2, 468, 123, runner=runner)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "NATIVE_TIMEOUT")

    def test_invalid_arguments_have_no_native_calls(self):
        for args in [(float("nan"), 2, 468, 123), (1, float("inf"), 468, 123),
                     (True, 2, 468, 123), (1, 2, 0, 123), (1, 2, True, 123),
                     (1, 2, 468, 0), (1, 2, 468, 2**32), (1, 2, 2**31, 123)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                query(None, *args)

    def test_observation_not_authorization(self):
        native = self.native()
        result = query(native, 346, 176.5, 468, 123)
        self.assertEqual(result["status"], "OBSERVED")
        self.assertTrue(result["matchesExpected"])
        self.assertTrue(result["diagnosticOnly"])
        native.find.assert_called_once_with(3, 346, 176.5)
        native.pid.assert_called_once_with(8)

    def test_different_owner_or_window_never_matches(self):
        for found, owner in [((0, 124, 8), (0, 468)), ((0, 123, 9), (0, 999)),
                             ((0, 124, 3), (0, 468))]:
            native = self.native(found=found, owner=owner)
            self.assertFalse(query(native, 1, 2, 468, 123)["matchesExpected"])
            self.assertEqual(native.find.call_count, 1)

    def test_failed_connection_does_not_query(self):
        for value in [0, -1]:
            native = self.native(connection=value)
            self.assertEqual(query(native, 1, 2, 468, 123)["status"], "UNAVAILABLE")
            native.find.assert_not_called()

    def test_find_errors_do_not_query_owner(self):
        for found in [(1, 123, 8), (0, 0, 8), (0, 123, 0), (0, 123, -1)]:
            native = self.native(found=found)
            self.assertFalse(query(native, 1, 2, 468, 123)["matchesExpected"])
            native.pid.assert_not_called()

    def test_owner_failure_never_matches(self):
        for owner in [(1, 468), (0, 0), (0, -1)]:
            result = query(self.native(owner=owner), 1, 2, 468, 123)
            self.assertEqual(result["status"], "UNAVAILABLE")
            self.assertFalse(result["matchesExpected"])

    def test_isolation_timeout_no_retry(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired("probe", 3))
        self.assertEqual(isolated(1, 2, 468, 123, runner=runner)["reason"], "NATIVE_TIMEOUT")
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(runner.call_args.kwargs["timeout"], 3)

    def test_child_crash_or_bad_result(self):
        for code, output in [(-11, b""), (0, b"x"), (0, b"[]"),
                             (0, b"{}"), (0, b"x" * 8193)]:
            runner = Mock(return_value=SimpleNamespace(returncode=code, stdout=output))
            self.assertEqual(isolated(1, 2, 468, 123, runner=runner)["status"], "UNKNOWN")
            self.assertEqual(runner.call_count, 1)

    def test_child_binding_and_match_are_checked(self):
        valid = query(self.native(), 1, 2, 468, 123)
        for changes in [{"expectedPid": 999}, {"point": [9, 9]}, {"pid": 999},
                        {"window": 0}, {"findStatus": 1}, {"status": "SUCCEEDED"},
                        {"status": "UNAVAILABLE"}]:
            with self.subTest(changes=changes):
                payload = {**valid, **changes}
                runner = Mock(return_value=SimpleNamespace(returncode=0, stdout=json.dumps(payload).encode()))
                self.assertEqual(isolated(1, 2, 468, 123, runner=runner)["status"], "UNKNOWN")
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout=json.dumps(valid).encode()))
        self.assertEqual(isolated(1, 2, 468, 123, runner=runner), valid)


if __name__ == "__main__":
    unittest.main()
