"""Synthetic metric tests, never real P4 success evidence."""
import copy
import unittest
from agent.efficiency import MODEL, compare


def fixture():
    trials, results = [], []
    for i in range(1, 21):
        for arm in (('baseline', 'candidate') if i % 2 else ('candidate', 'baseline')):
            row = dict(index=i, arm=arm, taskId=f't-{i}-{arm}', sessionId=f's-{i}-{arm}',
                       model=dict(MODEL), inputs={'note.md': f'{i:064x}'}, oracleSha256=f'{i:064x}',
                       sourceSha256='a'*64, promptSha256='b'*64, toolsSha256='c'*64)
            trials.append(row)
            count = 100 if arm == 'baseline' else 80
            results.append(dict(copy.deepcopy(row), status='SUCCEEDED', verified=True, safetyPassed=True,
                                attempts=[dict(attemptId=row['taskId']+'-1', calls=8, rawCalls=9,
                                               elapsedMs=10, wallMs=20, interventions=0,
                                               usage=dict(inputTokens=count, outputTokens=0,
                                                          cacheReadTokens=0, cacheWriteTokens=0, totalTokens=count))]))
    return {'version': 1, 'trials': trials}, results


class EfficiencyTests(unittest.TestCase):
    def test_complete_paired_metrics(self):
        manifest, results = fixture()
        result = compare(manifest, results)
        self.assertEqual(result['status'], 'ELIGIBLE')
        self.assertEqual(result['totalsIncludingFailuresAndRework']['candidate']['totalTokens'], 1600)
        self.assertIsNone(result['monetaryCost'])

    def test_missing_trials_or_metrics_never_pass(self):
        for field in ('usage', 'interventions', 'wallMs'):
            manifest, results = fixture()
            del results[0]['attempts'][0][field]
            self.assertEqual(compare(manifest, results)['status'], 'INCOMPLETE')
        self.assertEqual(compare(*[fixture()[0], fixture()[1][:-1]])['status'], 'INCOMPLETE')

    def test_failed_attempts_and_rework_cost_are_counted(self):
        manifest, results = fixture()
        row = results[1]
        row['status'] = 'FAILED'; row['verified'] = False
        extra = copy.deepcopy(row['attempts'][0]); extra['attemptId'] += '-retry'
        row['attempts'].append(extra)
        result = compare(manifest, results)
        total = result['totalsIncludingFailuresAndRework']['candidate']
        self.assertEqual((total['totalTokens'], total['attempts'], total['failures']), (1680, 21, 1))
        self.assertFalse(result['eligible'])

    def test_false_success_or_safety_violation_rejected(self):
        for field in ('verified', 'safetyPassed'):
            manifest, results = fixture(); results[1][field] = False
            self.assertEqual(compare(manifest, results)['status'], 'REJECTED')

    def test_no_changed_identity_model_input_or_configuration(self):
        for field, value in [('sessionId', 'foreign'), ('model', {}), ('inputs', {}), ('promptSha256', 'd'*64)]:
            manifest, results = fixture(); results[1][field] = value
            with self.assertRaises(ValueError): compare(manifest, results)

    def test_manifest_not_shrunk_duplicated_reordered_or_unpaired(self):
        for kind in ('short', 'duplicate', 'order', 'oracle', 'arm'):
            manifest, results = fixture()
            if kind == 'short': manifest['trials'].pop()
            if kind == 'duplicate': manifest['trials'][1] = manifest['trials'][0]
            if kind == 'order': manifest['trials'].reverse()
            if kind == 'oracle': manifest['trials'][1]['oracleSha256'] = 'f'*64
            if kind == 'arm': manifest['trials'][3]['toolsSha256'] = 'f'*64
            with self.assertRaises(ValueError): compare(manifest, results)

    def test_duplicate_results_attempts_and_reset_budget_rejected(self):
        for kind in ('result', 'attempt', 'budget', 'total', 'nan'):
            manifest, results = fixture()
            if kind == 'result': results.append(results[0])
            if kind == 'attempt': results[1]['attempts'][0]['attemptId'] = results[0]['attempts'][0]['attemptId']
            if kind == 'budget': results[0]['attempts'][0]['rawCalls'] = 31
            if kind == 'total': results[0]['attempts'][0]['usage']['totalTokens'] = 99
            if kind == 'nan':
                results[0]['attempts'][0]['wallMs'] = float('nan')
                self.assertEqual(compare(manifest, results)['status'], 'INCOMPLETE'); continue
            with self.assertRaises(ValueError): compare(manifest, results)

    def test_thresholds_and_interventions_not_relaxed(self):
        for kind in ('tokens', 'wall', 'interventions'):
            manifest, results = fixture()
            for row in results:
                if row['arm'] != 'candidate': continue
                a = row['attempts'][0]
                if kind == 'tokens': a['usage']['inputTokens'] = a['usage']['totalTokens'] = 91
                if kind == 'wall': a['wallMs'] = 23
                if kind == 'interventions': a['interventions'] = 1
            self.assertEqual(compare(manifest, results)['status'], 'REJECTED')


if __name__ == '__main__':
    unittest.main()
