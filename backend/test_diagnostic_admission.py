import copy
import unittest
from datetime import datetime, timezone, timedelta

from backend.diagnostic_admission import (
    DIAGNOSTIC_BUNDLE, DIAGNOSTIC_EXECUTABLE, require_direct_capture_ready,
    require_direct_capture_admission,
    require_current_capture_admission, DIAGNOSTIC_SHA256,
)


class DiagnosticAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.report = dict(
            accessibility=True, screen_recording=True, screen_recording_capturable=True,
            direct_capture_status='ready', direct_capture_error=None,
            source=dict(attribution='driver-daemon', bundle_id=DIAGNOSTIC_BUNDLE,
                        executable=DIAGNOSTIC_EXECUTABLE, pid=42),
            direct_capture_verification=dict(bundle_id=DIAGNOSTIC_BUNDLE,
                                            source='permissions_grant',
                                            verified_at='2026-10-13T04:00:00Z'),
        )

    def test_ready_is_non_mutating_and_grants_nothing(self):
        before = copy.deepcopy(self.report)
        self.assertIsNone(require_direct_capture_ready(self.report, expected_pid=42))
        self.assertEqual(self.report, before)

    def test_old_diagnostic_identity_is_not_current_candidate(self):
        self.assertEqual(DIAGNOSTIC_BUNDLE, 'com.trycua.driver.pointguard')
        self.assertEqual(DIAGNOSTIC_EXECUTABLE,
            '/Users/mvpagent/CUAgentDriverDiagnostic-b4bc8ca2962687387b178fb98833dea0f81e0a7ca86152238333feb290bbde9e/CuaDriverPointGuard.app/Contents/MacOS/cua-driver-pointguard')
        self.assertEqual(DIAGNOSTIC_SHA256,
            '81d219ae81deb214d2b85dda567a2b2c6d962dd1b9afc80154bcb25c597a40ad')
        same_bundle_old_path = copy.deepcopy(self.report)
        same_bundle_old_path['source']['executable'] = '/Users/mvpagent/Applications/CuaDriverPointGuard.app/Contents/MacOS/cua-driver-pointguard'
        with self.assertRaisesRegex(ValueError, 'DIAGNOSTIC_DIRECT_CAPTURE_UNCONFIRMED'):
            require_direct_capture_ready(same_bundle_old_path, expected_pid=42)
        same_bundle_old_path['source']['executable'] = '/Users/mvpagent/CUAgentDriverDiagnostic-67d334cd04207faff101955e0b2b1b5fd1cc4f25251d9a0a75a4708f063b6beb/CuaDriverPointGuard.app/Contents/MacOS/cua-driver-pointguard'
        with self.assertRaisesRegex(ValueError, 'DIAGNOSTIC_DIRECT_CAPTURE_UNCONFIRMED'):
            require_direct_capture_ready(same_bundle_old_path, expected_pid=42)
        old = copy.deepcopy(self.report)
        old['source'].update(bundle_id='com.trycua.driver.local',
            executable='/Users/mvpagent/Applications/CuaDriverLocal.app/Contents/MacOS/cua-driver-local')
        old['direct_capture_verification']['bundle_id'] = 'com.trycua.driver.local'
        with self.assertRaisesRegex(ValueError, 'DIAGNOSTIC_DIRECT_CAPTURE_UNCONFIRMED'):
            require_direct_capture_ready(old, expected_pid=42)

    def test_missing_and_invalid_fields(self):
        changes = [((key,), None) for key in self.report if key != 'direct_capture_error']
        changes += [((key,), value) for key in ('accessibility', 'screen_recording',
                                               'screen_recording_capturable')
                    for value in (False, 1, 'true')]
        changes += [(('direct_capture_status',), value)
                    for value in ('not_checked', 'timed_out', 'unavailable', 'probe_failed')]
        changes += [(('source', key), value) for key, value in (
            ('pid', True), ('pid', 43), ('bundle_id', 'com.trycua.driver'),
            ('executable', '/tmp/cua-driver'), ('attribution', 'terminal'))]
        changes += [(('direct_capture_verification', key), value) for key, value in (
            ('bundle_id', 'com.trycua.driver'), ('source', 'cached'),
            ('verified_at', 'invalid'), ('verified_at', '2026-10-13T04:00:00'))]
        changes += [(('direct_capture_error',), {}),
                    (('direct_capture_verification_error',), None)]
        for path, value in changes:
            with self.subTest(path=path, value=value):
                report = copy.deepcopy(self.report)
                target = report
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(ValueError):
                    require_direct_capture_ready(report, expected_pid=42)

    def test_expected_pid_is_strict(self):
        for pid in (None, True, 1, '42', 43):
            with self.subTest(pid=pid), self.assertRaises(ValueError):
                require_direct_capture_ready(self.report, expected_pid=pid)

    def test_missing_required_fields(self):
        for key in self.report.keys() - {'direct_capture_error'}:
            with self.subTest(key=key):
                report = copy.deepcopy(self.report)
                del report[key]
                with self.assertRaises(ValueError):
                    require_direct_capture_ready(report, expected_pid=42)

    def test_helper_and_daemon_are_separate(self):
        daemon = copy.deepcopy(self.report)
        daemon['source']['pid'] = 99
        daemon['direct_capture_status'] = 'not_checked'
        daemon['screen_recording_capturable'] = None
        before = copy.deepcopy(daemon)
        self.assertIsNone(require_direct_capture_admission(
            self.report, daemon, setup_pid=42, daemon_pid=99))
        self.assertEqual(daemon, before)
        for mutate in (
            lambda d: d['source'].update(pid=42),
            lambda d: d['source'].update(bundle_id='com.trycua.driver'),
            lambda d: d.update(screen_recording=False),
            lambda d: d.update(direct_capture_status='ready'),
            lambda d: d.update(direct_capture_verification_error=None),
            lambda d: d['direct_capture_verification'].update(verified_at='2026-10-12T04:00:00Z'),
        ):
            altered = copy.deepcopy(daemon)
            mutate(altered)
            with self.assertRaises(ValueError):
                require_direct_capture_admission(self.report, altered, setup_pid=42, daemon_pid=99)
        with self.assertRaises(ValueError):
            require_direct_capture_admission(self.report, daemon, setup_pid=42, daemon_pid=42)

    def test_current_lifecycle_binding(self):
        daemon = copy.deepcopy(self.report)
        daemon.update(direct_capture_status='not_checked', screen_recording_capturable=None)
        daemon['source']['pid'] = 99
        receipt = dict(runId='run-008', sessionId='session-008', setupPid=42,
                       daemonPid=99, sha256=DIAGNOSTIC_SHA256, setupReport=self.report,
                       startedAt='2026-10-13T04:00:00.100000Z',
                       checkedAt='2026-10-13T04:00:02Z')
        now = datetime(2026, 10, 13, 4, 0, 3, tzinfo=timezone.utc)
        args = dict(run_id='run-008', session_id='session-008', daemon_pid=99,
                    executable_sha256=DIAGNOSTIC_SHA256, now=now)
        before = copy.deepcopy(receipt)
        self.assertIsNone(require_current_capture_admission(receipt, daemon, **args))
        self.assertEqual(receipt, before)
        old_sha = '01c3db9176267741a1608c971f2233e0371611d13f2346fecbf97c648f2d2c16'
        old_receipt = copy.deepcopy(receipt)
        old_receipt['sha256'] = old_sha
        with self.assertRaisesRegex(ValueError, 'DIAGNOSTIC_CURRENT_CAPTURE_UNCONFIRMED'):
            require_current_capture_admission(old_receipt, daemon,
                **{**args, 'executable_sha256': old_sha})
        old_010_sha = '2c02cca541043809e13a082e25168aeb9bea4bed67eaaa5ad70fa375f79792a5'
        old_receipt['sha256'] = old_010_sha
        with self.assertRaisesRegex(ValueError, 'DIAGNOSTIC_CURRENT_CAPTURE_UNCONFIRMED'):
            require_current_capture_admission(old_receipt, daemon,
                **{**args, 'executable_sha256': old_010_sha})
        for key, value in (
            ('runId', 'run-007'), ('sessionId', 'session-007'), ('sha256', 'bad'),
            ('setupPid', True), ('daemonPid', True), ('daemonPid', 100),
            ('startedAt', '2026-10-13T03:00:00Z'),
            ('startedAt', '2026-10-13T04:00:01Z'),
            ('checkedAt', '2026-10-13T04:00:04Z'),
            ('checkedAt', '2026-10-13T03:59:59Z'),
            ('checkedAt', 'invalid'), ('startedAt', '2026-10-13T04:00:00'),
            ('setupReport', None),
        ):
            with self.subTest(key=key, value=value):
                bad = copy.deepcopy(receipt); bad[key] = value
                with self.assertRaises(ValueError):
                    require_current_capture_admission(bad, daemon, **args)
        for key in receipt:
            bad = copy.deepcopy(receipt); del bad[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                require_current_capture_admission(bad, daemon, **args)
        for key, value in (('now', now + timedelta(seconds=301)),
                           ('now', now.replace(tzinfo=None)), ('now', None),
                           ('run_id', ''), ('session_id', None),
                           ('executable_sha256', 'bad'), ('daemon_pid', True)):
            with self.subTest(argument=key), self.assertRaises(ValueError):
                require_current_capture_admission(receipt, daemon, **{**args, key:value})
        daemon['source']['pid'] = 100
        with self.assertRaises(ValueError):
            require_current_capture_admission(receipt, daemon, **args)


if __name__ == '__main__':
    unittest.main()
