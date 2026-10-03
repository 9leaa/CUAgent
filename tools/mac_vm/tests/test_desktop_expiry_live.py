import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop_expiry_live as live
from driver_smoke import StopRun


class ExpiryDiagnosticTests(unittest.TestCase):
    def exercise(self, *, accepted=False, advanced=False):
        with tempfile.TemporaryDirectory() as directory:
            runtime, server = Mock(), Mock()
            runtime.directory = Path(directory)
            runtime.closed = True
            runtime.controller.renew.side_effect = [None, {'expiresAt': 1}, ValueError('expired')]
            runtime.controller.existing.return_value = {'stopped': True}
            runtime.task.observe.side_effect = [
                {'state': {'snapshot_id': 'observed'}},
                {} if accepted else StopRun('BLOCKED', 'expired'),
            ]
            before = {'stopped': False, 'rawCalls': 3, 'pendingCalls': 0}
            after = {'stopped': True, 'rawCalls': 4 if advanced else 3, 'pendingCalls': 0}
            runtime.status.side_effect = [before, after, after] if not accepted else [before, after]
            reopened = Mock()
            reopened.renew.side_effect = ValueError('stopped')
            with patch.object(live, 'prepare_guest', return_value=(runtime, server)), \
                    patch.object(live, 'LeaseController', return_value=reopened):
                if accepted or advanced:
                    with self.assertRaises(ValueError):
                        live.diagnose('run', 'owner', approved=True)
                else:
                    self.assertTrue(live.diagnose('run', 'owner', approved=True)['verified'])
            runtime.close.assert_called_once()
            server.server_close.assert_called_once()
            evidence = json.loads((runtime.directory / 'expiry-diagnostic.json').read_text())
            self.assertEqual(evidence['verified'], not (accepted or advanced))
            self.assertEqual(evidence['businessStatus'], 'UNVERIFIED')

    def test_summary_and_cleanup(self):
        self.exercise()

    def test_accepted_expired_request_is_not_success(self):
        self.exercise(accepted=True)

    def test_changed_budget_is_not_success(self):
        self.exercise(advanced=True)

    def test_host_refusal_is_before_preparation(self):
        with patch('desktop_guest.require_vm', side_effect=RuntimeError('not VM')):
            with self.assertRaises(RuntimeError):
                live.diagnose('run', 'owner', approved=True)


if __name__ == '__main__':
    unittest.main()
