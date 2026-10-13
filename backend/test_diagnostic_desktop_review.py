import copy
import hashlib
import unittest
from datetime import datetime, timezone, timedelta

from backend.diagnostic_admission import (
    DIAGNOSTIC_BUNDLE, DIAGNOSTIC_EXECUTABLE, DIAGNOSTIC_SHA256,
    require_business_capture_admission,
)


class DesktopReviewTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 13, 6, 0, 5, tzinfo=timezone.utc)
        report = dict(accessibility=True, screen_recording=True,
                      screen_recording_capturable=True, direct_capture_status='ready',
                      direct_capture_error=None,
                      source=dict(attribution='driver-daemon', bundle_id=DIAGNOSTIC_BUNDLE,
                                  executable=DIAGNOSTIC_EXECUTABLE, pid=42),
                      direct_capture_verification=dict(bundle_id=DIAGNOSTIC_BUNDLE,
                          source='permissions_grant', verified_at='2026-10-13T06:00:01Z'))
        self.receipt = dict(runId='run-012', sessionId='session-012', setupPid=42,
                            daemonPid=99, sha256=DIAGNOSTIC_SHA256, setupReport=report,
                            startedAt='2026-10-13T06:00:00Z', checkedAt='2026-10-13T06:00:02Z')
        self.daemon = copy.deepcopy(report)
        self.daemon['source']['pid'] = 99
        self.daemon.update(direct_capture_status='not_checked', screen_recording_capturable=None)
        # Deliberately only a signature fixture: this gate does not decode or judge pixels.
        self.png = b'\x89PNG\r\n\x1a\nfixture'
        self.review = dict(version=1, source='trusted-operator', scope='full-vm-desktop',
                           runId='run-012', sessionId='session-012', daemonPid=99,
                           sha256=DIAGNOSTIC_SHA256, observedAt='2026-10-13T06:00:03Z',
                           reviewedAt='2026-10-13T06:00:04Z', blockingPromptAbsent=True,
                           pngSha256=hashlib.sha256(self.png).hexdigest())

    def check(self, **changes):
        args = dict(desktop_review=self.review, desktop_png=self.png, run_id='run-012',
                    session_id='session-012', daemon_pid=99,
                    executable_sha256=DIAGNOSTIC_SHA256, now=self.now)
        args.update(changes)
        return require_business_capture_admission(self.receipt, self.daemon, **args)

    def test_bound_review_is_nonmutating(self):
        before = copy.deepcopy((self.review, self.receipt, self.daemon))
        self.assertIsNone(self.check())
        self.assertEqual(before, (self.review, self.receipt, self.daemon))

    def test_rejects_absent_malformed_and_extra_review_fields(self):
        for value in (None, [], {}, {**self.review, 'extra': True}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(desktop_review=value)
        for key in self.review:
            altered = dict(self.review); del altered[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                self.check(desktop_review=altered)

    def test_rejects_scope_identity_prompt_and_time_mismatch(self):
        for key, value in [('version', True), ('source', 'model'), ('scope', 'calc-window'),
                           ('runId', 'old'), ('sessionId', 'old'), ('daemonPid', True),
                           ('daemonPid', 42), ('sha256', 'old'), ('pngSha256', 'bad'),
                           ('blockingPromptAbsent', False), ('blockingPromptAbsent', 1),
                           ('observedAt', '2026-10-13T06:00:01Z'),
                           ('observedAt', '2026-10-13T06:00:05Z'),
                           ('reviewedAt', '2026-10-13T06:00:06Z'),
                           ('observedAt', '2026-10-13T06:00:03'), ('observedAt', 'bad')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.check(desktop_review={**self.review, key: value})

    def test_rejects_stale_or_changed_bytes_and_capture_failure(self):
        for value in (None, b'', b'not-png', self.png + b'changed', bytearray(self.png)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(desktop_png=value)
        with self.assertRaises(ValueError):
            self.check(now=self.now + timedelta(seconds=29))
        self.daemon['screen_recording'] = False
        with self.assertRaises(ValueError):
            self.check()

    def test_rejects_jpeg_even_when_digest_matches(self):
        # 012: screenshot APIs may return JPEG despite a caller's .png filename.
        jpeg = b'\xff\xd8\xff\xe0JFIF\x00fixture\xff\xd9'
        review = {**self.review, 'pngSha256': hashlib.sha256(jpeg).hexdigest()}
        with self.assertRaisesRegex(ValueError, 'DIAGNOSTIC_DESKTOP_REVIEW_UNCONFIRMED'):
            self.check(desktop_review=review, desktop_png=jpeg)


if __name__ == '__main__':
    unittest.main()
