import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_lease import DesktopTask, LeaseGate
from driver_smoke import StopRun


class DesktopLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / 'control.json'
        self.now = 100.0
        self.value = dict(version=1, runId='task', owner='worker', epoch=1, stopped=False, expiresAt=120000)
        self.write()

    def write(self, **changes):
        self.path.write_text(json.dumps({**self.value, **changes}))
        self.path.chmod(0o600)

    def gate(self):
        return LeaseGate(self.path, run_id='task', owner='worker', epoch=1, clock=lambda: self.now)

    def task(self):
        self.sent = []
        return DesktopTask(self.root / 'task', lambda tool, args: self.sent.append(tool) or {'ok': True},
                           lambda _: None, lease=self.gate(), approved=True, environment=lambda: None)

    def test_every_raw_request_rechecks_and_stop_survives_restart(self):
        task = self.task()
        task.raw('launch_app', task.launch_args)
        self.assertEqual(task.used, 1)
        self.write(stopped=True)
        with self.assertRaises(StopRun): task.raw('launch_app', task.launch_args)
        self.assertEqual(task.used, 1)
        self.assertEqual(self.sent, ['launch_app'])
        self.write()
        restarted = self.task()
        with self.assertRaises(StopRun): restarted.admit('read_result')
        self.assertEqual(restarted.used, 1)

    def test_zero_call_denial_cannot_be_reset_by_restart(self):
        task = self.task()
        self.path.unlink()
        with self.assertRaises(StopRun): task.admit('write_result')
        self.write()
        restarted = self.task()
        with self.assertRaises(StopRun): restarted.admit('write_result')
        self.assertEqual(restarted.used, 0)

    def test_invalid_fields_and_expiry_fail_closed(self):
        cases = [dict(version=True), dict(epoch=True), dict(epoch=2), dict(owner='old'),
                 dict(runId='other'), dict(stopped=0), dict(stopped=True),
                 dict(expiresAt=100000), dict(expiresAt=130001), dict(expiresAt=True)]
        for change in cases:
            with self.subTest(change=change):
                self.write(**change)
                gate = self.gate()
                with self.assertRaises(StopRun): gate.check()
                self.write()
                with self.assertRaises(StopRun): gate.check()

    def test_clock_backwards_and_natural_expiry_latch(self):
        gate = self.gate(); gate.check()
        self.now = 99
        with self.assertRaises(StopRun): gate.check()
        self.now = 120
        with self.assertRaises(StopRun): self.gate().check()

    def test_symlink_public_fifo_and_oversize_rejected(self):
        self.path.chmod(0o644)
        with self.assertRaises(StopRun): self.gate().check()
        self.path.unlink()
        self.path.symlink_to(self.root / 'missing')
        with self.assertRaises(StopRun): self.gate().check()
        self.path.unlink(); os.mkfifo(self.path, 0o600)
        with self.assertRaises(StopRun): self.gate().check()
        self.path.unlink(); self.path.write_bytes(b'x' * 4097); self.path.chmod(0o600)
        with self.assertRaises(StopRun): self.gate().check()

    def test_constructor_requires_binding_before_creating_run(self):
        with self.assertRaises(StopRun):
            DesktopTask(self.root / 'other', lease=self.gate(), approved=True, environment=lambda: None)
        self.assertFalse((self.root / 'other').exists())


if __name__ == '__main__':
    unittest.main()
