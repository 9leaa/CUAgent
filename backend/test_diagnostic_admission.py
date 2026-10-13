import copy
import unittest

from backend.diagnostic_admission import (
    DIAGNOSTIC_BUNDLE, DIAGNOSTIC_EXECUTABLE, require_direct_capture_ready,
    require_direct_capture_admission,
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


if __name__ == '__main__':
    unittest.main()
