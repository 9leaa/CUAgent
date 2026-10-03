"""Synthetic evidence only; no real inference or account access."""
import json
from pathlib import Path
import tempfile
import unittest
from agent.daily_report import MODEL, sha
from agent.efficiency_evidence import extract


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.approval = dict(runId='run', sessionId='session', allowedTools=['workspace_read'],
                             ledgerPath=str(self.root / 'calls.jsonl'))
        self.rows = [dict(type='turn/start', time=100),
                     dict(type='request/header', data={'header': {'config': dict(MODEL),
                          'tools': [{'name': 'workspace_read'}]}}),
                     dict(type='tool/call', data={'callId': 'one'}),
                     dict(type='assistant/message', data={'usage': dict(inputTokens=1, outputTokens=2,
                          cacheReadTokens=3, cacheWriteTokens=0, totalTokens=6)}),
                     dict(type='turn/end', time=200, data={'reason': {'kind': 'completed'}})]
        self.audit = [dict(event='dispatch', runId='run', sessionId='session', used=1,
                           callId='one', name='workspace_read')]
        self.life = dict(version=1, complete=True, runId='run', sessionId='session',
                         boundary='before-activate-through-after-restore', startedMonotonicNs=1,
                         endedMonotonicNs=200000001, interventions=[])

    def save(self):
        (self.root / 'approval.json').write_text(json.dumps(self.approval))
        for name, rows in [('session.jsonl', self.rows), ('calls.jsonl', self.audit)]:
            (self.root / name).write_text('\n'.join(json.dumps(r) for r in rows))
        self.life.update(sessionSha256=sha((self.root / 'session.jsonl').read_bytes()),
                         auditSha256=sha((self.root / 'calls.jsonl').read_bytes()))
        (self.root / 'lifecycle.json').write_text(json.dumps(self.life))

    def test_failed_and_aborted_turns_keep_all_cost(self):
        for reason in ('completed', 'error', 'aborted'):
            self.rows[-1]['data']['reason']['kind'] = reason
            self.life['interventions'] = [{'kind': 'cancel', 'monotonicNs': 100}]
            self.save()
            result = extract(self.root)
            self.assertEqual(result['attempt']['usage']['totalTokens'], 6)
            self.assertEqual(result['attempt']['interventions'], 1)
            self.assertEqual(result['attempt']['wallMs'], 200)
            self.assertEqual(result['safetyIssues'], [])
            self.assertNotIn('verified', result)

    def test_missing_usage_or_interventions_not_zero(self):
        self.rows[3]['data']['usage'].pop('cacheReadTokens')
        self.save()
        with self.assertRaisesRegex(ValueError, 'usage incomplete'): extract(self.root)
        self.rows[3]['data']['usage']['cacheReadTokens'] = 3
        self.life.pop('interventions')
        self.save()
        with self.assertRaisesRegex(ValueError, 'intervention'): extract(self.root)

    def test_source_changes_and_extra_turns_rejected(self):
        self.save()
        with (self.root / 'session.jsonl').open('a') as file: file.write('\n{}')
        with self.assertRaisesRegex(ValueError, 'evidence changed'): extract(self.root)
        self.rows.append(self.rows[-1])
        self.save()
        with self.assertRaisesRegex(ValueError, 'one original terminal'): extract(self.root)

    def test_bad_model_and_budget_reported_without_hiding_cost(self):
        self.rows[1]['data']['header']['config']['reasoningEffort'] = 'high'
        self.audit[0]['used'] = 31
        self.save()
        result = extract(self.root)
        self.assertEqual(len(result['safetyIssues']), 2)
        self.assertEqual(result['attempt']['usage']['totalTokens'], 6)

    def test_incomplete_lifecycle_and_short_wall_rejected(self):
        self.life['complete'] = False
        self.save()
        with self.assertRaisesRegex(ValueError, 'complete lifecycle'): extract(self.root)
        self.life['complete'] = True
        self.life['endedMonotonicNs'] = 2
        self.save()
        with self.assertRaisesRegex(ValueError, 'inconsistent wall'): extract(self.root)
