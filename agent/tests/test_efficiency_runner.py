"""Lifecycle mocks; not evidence of real Desktop runs."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent.efficiency_runner import execute_trial
from agent.daily_report import sha


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'run'
        self.run.mkdir(mode=0o700)
        self.approval = dict(runId='run', sessionId='session', controlEpoch=1,
                             controlPath=str(self.run / 'control.json'), ledgerPath=str(self.run / 'calls.jsonl'))
        (self.run / 'approval.json').write_text(json.dumps(self.approval))
        self.base = self.root / 'base.json'
        self.base.write_text('{"tasks":[]}')
        self.trial = dict(runDir=str(self.run), arm='candidate', sessionId='session', promptSha256=sha('test'))
        self.calls = []

    def rpc(self, mode, *paths):
        self.calls.append(mode)
        if mode == 'start':
            (self.run / 'prompt-request.json').write_text(json.dumps({'request': {'sessionId': 'session',
                'requestId': 'request', 'content': [{'type': 'text', 'text': 'test'}]}}))
            return {'accepted': True}
        if mode == 'poll':
            (self.run / 'session.jsonl').write_text(json.dumps({'type': 'user/message', 'data': {
                'source': {'rpcId': 'request'}, 'content': [{'type': 'text', 'text': 'test'}]}}))
            (self.run / 'calls.jsonl').write_text('original ledger')
            return {'terminal': True}
        return {}

    @patch('agent.efficiency_runner.extract', return_value={'safetyIssues': [], 'attempt': {}})
    @patch('agent.efficiency_runner.verify', return_value={'status': 'SUCCEEDED'})
    def test_normal_restores_then_records_closed_lifecycle_and_cannot_replay(self, verify, extract):
        result = execute_trial(self.trial, self.base, self.rpc)
        self.assertEqual(self.calls, ['activate', 'start', 'poll', 'restore'])
        self.assertEqual(result['status'], 'SUCCEEDED')
        life = json.loads((self.run / 'lifecycle.json').read_text())
        self.assertTrue(life['complete'])
        self.assertGreater(life['endedMonotonicNs'], life['startedMonotonicNs'])
        self.assertTrue(json.loads((self.run / 'control.json').read_text())['stopped'])
        with self.assertRaisesRegex(ValueError, 'already attempted'):
            execute_trial(self.trial, self.base, self.rpc)
        self.assertEqual(self.calls.count('start'), 1)

    def test_lost_start_ack_revokes_observes_cancels_never_replays(self):
        def rpc(mode, *paths):
            self.calls.append(mode)
            if mode == 'start': raise RuntimeError('lost ACK')
            if mode == 'inspect':
                self.assertTrue(json.loads((self.run / 'control.json').read_text())['stopped'])
                return {'exists': True, 'terminal': False}
            if mode == 'poll': raise RuntimeError('observation unavailable')
            return {}
        with self.assertRaisesRegex(ValueError, 'incomplete lifecycle'):
            execute_trial(self.trial, self.base, rpc)
        self.assertEqual(self.calls, ['activate', 'start', 'inspect', 'cancel', 'poll', 'restore'])
        self.assertFalse(json.loads((self.run / 'lifecycle.json').read_text())['complete'])
        self.assertFalse((self.run / 'efficiency-result.json').exists())

    @patch('agent.efficiency_runner.verify', return_value={'status': 'SUCCEEDED'})
    def test_restore_failure_stops_result_publication(self, verify):
        def rpc(mode, *paths):
            if mode == 'restore': raise RuntimeError('restore failed')
            return self.rpc(mode, *paths)
        with self.assertRaisesRegex(ValueError, 'incomplete lifecycle'):
            execute_trial(self.trial, self.base, rpc)
        self.assertFalse((self.run / 'efficiency-result.json').exists())

    @patch('agent.efficiency_runner.extract', return_value={'safetyIssues': [], 'attempt': {'usage': {'totalTokens': 42}}})
    @patch('agent.efficiency_runner.verify', side_effect=ValueError('wrong output'))
    def test_business_failure_preserves_cost_not_assumed_safety_pass(self, verify, extract):
        result = execute_trial(self.trial, self.base, self.rpc)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertIsNone(result['safetyPassed'])
        self.assertEqual(result['attempts'][0]['usage']['totalTokens'], 42)
