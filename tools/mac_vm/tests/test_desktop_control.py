from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_control import LeaseController
from desktop_lease import LeaseGate
from driver_smoke import StopRun


class DesktopControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / 'lease.json'
        self.now = 100.0

    def controller(self, **changes):
        args = dict(run_id='task', owner='owner', epoch=1, clock=lambda: self.now)
        args.update(changes)
        return LeaseController(self.path, **args)

    def test_grant_is_consumed_by_final_gate_and_ack_retry_does_not_extend(self):
        control = self.controller()
        first = control.renew(1)
        control.gate.check()
        self.assertEqual(self.path.stat().st_mode & 0o077, 0)
        self.now = 105
        self.assertEqual(self.controller().renew(1), first)
        with self.assertRaises(ValueError): self.controller().renew(1, ttl_ms=15000)
        renewed = self.controller().renew(2)
        self.assertEqual(renewed['expiresAt'], 125000)
        with self.assertRaises(ValueError): self.controller().renew(1)

    def test_revoke_persists_and_gate_refuses_new_dispatch(self):
        control = self.controller(); control.renew(1)
        control.gate.check()
        stopped = control.revoke()
        self.assertEqual(self.controller().revoke(), stopped)
        with self.assertRaises(ValueError): self.controller().renew(2)
        with self.assertRaises(StopRun): control.gate.check()

    def test_revoke_before_initial_grant_blocks_delayed_grant(self):
        self.controller().revoke()
        with self.assertRaises(ValueError): self.controller().renew(1)

    def test_expiry_and_backwards_clock_persist_stop(self):
        for second in (99, 120):
            with self.subTest(second=second):
                if self.path.exists(): self.path.unlink()
                self.now = 100
                self.controller().renew(1)
                self.now = second
                with self.assertRaises(ValueError): self.controller().renew(2)
                self.assertTrue(json.loads(self.path.read_text())['stopped'])
                self.now = 110
                with self.assertRaises(ValueError): self.controller().renew(3)

    def test_foreign_identity_cannot_renew_or_revoke(self):
        self.controller().renew(1)
        before = self.path.read_bytes()
        for change in (dict(owner='other'), dict(epoch=2), dict(run_id='other')):
            with self.subTest(change=change):
                with self.assertRaises(ValueError): self.controller(**change).renew(2)
                with self.assertRaises(ValueError): self.controller(**change).revoke()
        self.assertEqual(self.path.read_bytes(), before)

    def test_concurrent_same_sequence_returns_one_expiry(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            values = list(pool.map(lambda _: self.controller().renew(1), range(8)))
        self.assertTrue(all(value == values[0] for value in values))
        self.controller().gate.check()

    def test_invalid_arguments_cannot_create_lease(self):
        for seq, ttl in ((True, 1000), (0, 1000), (1, True), (1, 0), (1, 30001)):
            with self.assertRaises(ValueError): self.controller().renew(seq, ttl)
        self.assertFalse(self.path.exists())

    def test_symlink_and_malformed_existing_record_never_replaced(self):
        self.path.symlink_to(self.path.parent / 'missing')
        with self.assertRaises((ValueError, OSError)): self.controller().renew(1)
        self.assertTrue(self.path.is_symlink())
        self.path.unlink(); self.path.write_text('{}'); self.path.chmod(0o600)
        with self.assertRaises(ValueError): self.controller().renew(1)
        with self.assertRaises(ValueError): self.controller().revoke()
        self.assertEqual(self.path.read_text(), '{}')


if __name__ == '__main__':
    unittest.main()
