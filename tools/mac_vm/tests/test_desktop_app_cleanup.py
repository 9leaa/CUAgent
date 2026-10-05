import dataclasses
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_app_cleanup import ApplicationCleanup, ApplicationIdentity, CleanupState


class ApplicationCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root / 'p2-12345678-1234-1234-1234-123456789abc'
        self.run.mkdir(mode=0o700)
        self.owner = '87654321-1234-1234-1234-123456789abc'
        self.app = ApplicationIdentity(123, 1_790_000_000_123456)
        self.current = self.app
        self.state = CleanupState(self.run.name, self.owner, 1, True, True, True, 0, False, 30)
        self.hashes = dict(document='a' * 64, result='b' * 64, trace='c' * 64)
        self.sent = []
        self.now = 0

    def terminate(self, identity):
        self.sent.append(identity)
        self.current = None
        return True

    def sleep(self, duration):
        self.now += duration

    def cleaner(self, **overrides):
        kwargs = dict(run_id=self.run.name, owner=self.owner, epoch=1, application=self.app,
                      verified_hashes=self.hashes, read_state=lambda: self.state,
                      read_identity=lambda pid: self.current,
                      read_hashes=lambda: self.hashes.copy(), request_terminate=self.terminate,
                      clock=lambda: self.now, sleep=self.sleep)
        kwargs.update(overrides)
        return ApplicationCleanup(self.run, **kwargs)

    def test_exit_once_at_exhausted_budget_files_and_state_unchanged(self):
        before = dataclasses.asdict(self.state)
        result = self.cleaner().run()
        self.assertEqual(result['status'], 'EXITED')
        self.assertEqual(self.sent, [self.app])
        self.assertFalse(result['forced'])
        self.assertEqual(dataclasses.asdict(self.state), before)
        for name in ('app-cleanup-intent.json', 'app-cleanup-receipt.json'):
            self.assertEqual((self.run / name).stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads((self.run / 'app-cleanup-receipt.json').read_text()), result)
        with self.assertRaises(FileExistsError):
            self.cleaner().run()
        self.assertEqual(len(self.sent), 1)

    def test_already_absent_does_not_send(self):
        self.current = None
        result = self.cleaner().run()
        self.assertEqual((result['status'], result['reason']), ('EXITED', 'ALREADY_ABSENT'))
        self.assertFalse(result['terminationRequested'])
        self.assertEqual(self.sent, [])

    def test_reused_pid_or_wrong_identity_never_terminates(self):
        self.current = ApplicationIdentity(self.app.pid, self.app.started_us + 1)
        result = self.cleaner().run()
        self.assertEqual(result['reason'], 'PROCESS_IDENTITY_CHANGED')
        self.assertEqual(result['status'], 'REFUSED')
        self.assertEqual(self.sent, [])

    def test_unsafe_state_fields_refuse_without_dispatch(self):
        cases = dict(terminal=False, stopped=False, verified=False, pending=1,
                     uncertain=True, raw_calls=31, epoch=True, owner='other', run_id='other')
        for field, value in cases.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                original = self.run
                self.run = Path(directory).resolve() / original.name
                self.run.mkdir(mode=0o700)
                original_state = self.state
                try:
                    self.state = dataclasses.replace(self.state, **{field: value})
                    self.assertEqual(self.cleaner().run()['status'], 'REFUSED')
                    self.assertEqual(self.sent, [])
                finally:
                    self.state, self.run = original_state, original

    def test_boolean_counters_and_truthy_flags_rejected(self):
        for field, value in [('pending', False), ('raw_calls', True), ('terminal', 1),
                             ('verified', 1), ('stopped', 1), ('uncertain', 0)]:
            with self.subTest(field=field):
                cleaner = self.cleaner(read_state=lambda: dataclasses.replace(self.state, **{field: value}))
                with self.assertRaises(ValueError):
                    cleaner._state()

    def test_changed_artifact_refuses(self):
        cleaner = self.cleaner()
        self.hashes['document'] = 'd' * 64
        self.assertEqual(cleaner.run()['status'], 'REFUSED')
        self.assertEqual(self.sent, [])

    def test_state_changes_between_checks_refuse(self):
        reads = iter([self.state, dataclasses.replace(self.state, pending=1)])
        self.assertEqual(self.cleaner(read_state=lambda: next(reads)).run()['status'], 'REFUSED')
        self.assertEqual(self.sent, [])

    def test_unknown_request_never_retried_and_error_redacted(self):
        def fail(identity):
            self.sent.append(identity)
            raise TimeoutError('private-secret-not-for-receipt')
        result = self.cleaner(request_terminate=fail).run()
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertNotIn('private-secret', json.dumps(result))
        with self.assertRaises(FileExistsError):
            self.cleaner().run()
        self.assertEqual(len(self.sent), 1)

    def test_exit_ack_without_disappearance_is_unknown_bounded(self):
        def accept(identity):
            self.sent.append(identity)
            return True
        result = self.cleaner(request_terminate=accept).run()
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(result['reason'], 'EXIT_NOT_CONFIRMED')
        self.assertLessEqual(self.now, 3)
        self.assertEqual(len(self.sent), 1)

    def test_save_prompt_or_refused_termination_does_not_force(self):
        result = self.cleaner(request_terminate=lambda _: False).run()
        self.assertEqual(result['reason'], 'TERMINATION_NOT_ACCEPTED')
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(self.current, self.app)

    def test_changed_identity_during_exit_is_unknown(self):
        def replace(identity):
            self.current = ApplicationIdentity(identity.pid, identity.started_us + 1)
            return True
        result = self.cleaner(request_terminate=replace).run()
        self.assertEqual(result['reason'], 'PROCESS_IDENTITY_CHANGED')
        self.assertEqual(result['status'], 'UNKNOWN')

    def test_post_exit_artifact_change_not_success(self):
        def changed(identity):
            self.current = None
            self.hashes['document'] = 'd' * 64
            return True
        result = self.cleaner(request_terminate=changed).run()
        self.assertEqual(result['reason'], 'POSTCONDITION_CHANGED')
        self.assertEqual(result['status'], 'UNKNOWN')

    def test_post_exit_raw_count_change_not_success(self):
        def changed(identity):
            self.current = None
            self.state = dataclasses.replace(self.state, raw_calls=29)
            return True
        self.assertEqual(self.cleaner(request_terminate=changed).run()['reason'], 'POSTCONDITION_CHANGED')

    def test_identity_query_failure_is_not_absent(self):
        def unreadable(_):
            raise OSError('unavailable')
        self.assertEqual(self.cleaner(read_identity=unreadable).run()['status'], 'REFUSED')
        self.assertEqual(self.sent, [])

    def test_intent_write_failure_prevents_request(self):
        with patch('desktop_app_cleanup.os.fsync', side_effect=OSError('disk')):
            with self.assertRaises(OSError):
                self.cleaner().run()
        self.assertEqual(self.sent, [])
        with self.assertRaises(FileExistsError):
            self.cleaner().run()

    def test_receipt_write_failure_propagates_without_replay(self):
        cleaner = self.cleaner()
        save = cleaner._save
        def fail_receipt(name, value):
            if name == 'app-cleanup-receipt.json':
                raise OSError('disk')
            save(name, value)
        with patch.object(cleaner, '_save', side_effect=fail_receipt):
            with self.assertRaises(OSError):
                cleaner.run()
        with self.assertRaises(FileExistsError):
            self.cleaner().run()
        self.assertEqual(len(self.sent), 1)

    def test_existing_intent_link_is_not_followed(self):
        other = self.root / 'preserve.txt'
        other.write_text('preserve')
        (self.run / 'app-cleanup-intent.json').symlink_to(other)
        with self.assertRaises(FileExistsError):
            self.cleaner().run()
        self.assertEqual(other.read_text(), 'preserve')
        self.assertEqual(self.sent, [])

    def test_public_directory_denied(self):
        os.chmod(self.run, 0o755)
        with self.assertRaises(ValueError):
            self.cleaner()

    def test_invalid_identity_and_hash_contract_denied(self):
        for pid, start in [(True, 1), (0, 1), (1, False), (1, -1)]:
            with self.assertRaises(ValueError):
                ApplicationIdentity(pid, start)
        with self.assertRaises(ValueError):
            ApplicationIdentity(1, 1, '/some/other/TextEdit')
        for hashes in [{}, {**self.hashes, 'extra': 'd' * 64}, {**self.hashes, 'trace': 'bad'}]:
            with self.assertRaises(ValueError):
                self.cleaner(verified_hashes=hashes)

    def test_invalid_binding_denied(self):
        for fields in [{'owner': '-' * 36}, {'epoch': True}, {'run_id': 'other'}, {'epoch': 0}]:
            with self.assertRaises(ValueError):
                self.cleaner(**fields)

    def test_partial_intent_refuses_rebuild(self):
        (self.run / 'app-cleanup-intent.json').write_text('{')
        with self.assertRaises(FileExistsError):
            self.cleaner().run()
        self.assertEqual(self.sent, [])


if __name__ == '__main__':
    unittest.main()
