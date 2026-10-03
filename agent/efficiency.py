"""Offline P4 metric reduction; inputs must come from independent evidence collection.

This module never calls a model and does not verify business artifacts itself.
An eligible comparison is not permission to enable a tool or a stage acceptance.
"""
import math
import re

MODEL = {'provider': 'deepseek-account', 'model': 'deepseek-flash', 'reasoningEffort': 'off'}
TOKENS = ('inputTokens', 'outputTokens', 'cacheReadTokens', 'cacheWriteTokens', 'totalTokens')
METRICS = ('calls', 'rawCalls', 'elapsedMs', 'wallMs', 'interventions')
TERMINAL = {'SUCCEEDED', 'FAILED', 'BLOCKED', 'UNVERIFIED', 'STOPPED'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def compare(manifest, results):
    """Validate the frozen 20-pair schedule, count all attempts, never fill gaps with 0."""
    trials = manifest['trials']
    require(manifest.get('version') == 1 and len(trials) == 40, 'complete frozen 20-pair manifest required')
    expected, identities = {}, set()
    for row in trials:
        key = (row['index'], row['arm'])
        require(type(row['index']) is int and 1 <= row['index'] <= 20
                and row['arm'] in ('baseline', 'candidate') and key not in expected, 'invalid or duplicate trial')
        require(row['model'] == MODEL, 'Flash/off required')
        require(isinstance(row['inputs'], dict) and row['inputs'] and
                all(isinstance(p, str) and p and digest(h) for p, h in row['inputs'].items()), 'input hashes required')
        require(all(digest(row.get(k)) for k in ('oracleSha256', 'sourceSha256', 'promptSha256', 'toolsSha256')), 'frozen hashes required')
        for field in ('taskId', 'sessionId'):
            value = row[field]
            require(isinstance(value, str) and value and (field, value) not in identities, 'unique original identities required')
            identities.add((field, value))
        expected[key] = row
    for index in range(1, 21):
        a, b = expected[index, 'baseline'], expected[index, 'candidate']
        require(a['inputs'] == b['inputs'] and a['oracleSha256'] == b['oracleSha256'], 'paired inputs or oracle changed')
        for arm in ('baseline', 'candidate'):
            original = expected[1, arm]
            require(all(expected[index, arm][k] == original[k] for k in
                        ('sourceSha256', 'promptSha256', 'toolsSha256')), 'arm changed during experiment')
    required_order = [(i, arm) for i in range(1, 21) for arm in
                      (('baseline', 'candidate') if i % 2 else ('candidate', 'baseline'))]
    require(list(expected) == required_order, 'alternating frozen order required')
    totals = {arm: dict.fromkeys((*TOKENS, *METRICS, 'successes', 'failures', 'attempts'), 0)
              for arm in ('baseline', 'candidate')}
    seen, attempts_seen, gaps, safety = set(), set(), [], []
    for row in results:
        key = (row['index'], row['arm'])
        require(key in expected and key not in seen, 'unknown or duplicate result')
        seen.add(key)
        spec = expected[key]
        require(all(row.get(k) == spec[k] for k in
                    ('taskId', 'sessionId', 'model', 'inputs', 'oracleSha256', 'sourceSha256', 'promptSha256', 'toolsSha256')),
                'result identity or frozen evidence mismatch')
        if row.get('status') not in TERMINAL:
            gaps.append([*key, 'not terminal'])
            continue
        if type(row.get('verified')) is not bool or type(row.get('safetyPassed')) is not bool:
            gaps.append([*key, 'missing independent verdict'])
        if row.get('safetyPassed') is False or (row['status'] == 'SUCCEEDED' and row.get('verified') is False):
            safety.append(list(key))
        attempts = row.get('attempts')
        if not isinstance(attempts, list) or not attempts:
            gaps.append([*key, 'missing attempts'])
            continue
        subtotal = dict.fromkeys((*TOKENS, *METRICS), 0)
        complete = True
        for attempt in attempts:
            attempt_id = attempt.get('attemptId')
            require(isinstance(attempt_id, str) and attempt_id and attempt_id not in attempts_seen,
                    'unique attempt identity required')
            attempts_seen.add(attempt_id)
            usage = attempt.get('usage')
            if not isinstance(usage, dict) or not all(type(usage.get(k)) is int and usage[k] >= 0 for k in TOKENS):
                complete = False
                continue
            require(usage['totalTokens'] == sum(usage[k] for k in TOKENS[:-1]), 'inconsistent token total')
            if not all(number(attempt.get(k)) for k in METRICS):
                complete = False
                continue
            require(all(type(attempt[k]) is int for k in ('calls', 'rawCalls', 'interventions')), 'integer counts required')
            require(attempt['rawCalls'] >= attempt['calls'] and attempt['wallMs'] >= attempt['elapsedMs'], 'inconsistent metrics')
            for k in TOKENS:
                subtotal[k] += usage[k]
            for k in METRICS:
                subtotal[k] += attempt[k]
        if not complete:
            gaps.append([*key, 'missing usage or metrics'])
            continue
        require(subtotal['rawCalls'] <= 30, 'recovery cannot reset task budget')
        total = totals[key[1]]
        for k, value in subtotal.items():
            total[k] += value
        total['attempts'] += len(attempts)
        total['successes' if row['status'] == 'SUCCEEDED' and row.get('verified') is True else 'failures'] += 1
    gaps.extend([*key, 'missing trial'] for key in expected if key not in seen)
    a, b = totals['baseline'], totals['candidate']
    complete = not gaps
    eligible = complete and not safety and a['successes'] >= 18 and b['successes'] >= a['successes']
    eligible = eligible and b['interventions'] <= a['interventions'] and a['totalTokens'] > 0 and a['wallMs'] > 0
    eligible = eligible and b['totalTokens'] * 10 <= a['totalTokens'] * 9 and b['wallMs'] * 10 <= a['wallMs'] * 11
    return {'status': 'INCOMPLETE' if gaps else ('ELIGIBLE' if eligible else 'REJECTED'),
            'eligible': bool(eligible), 'totalsIncludingFailuresAndRework': totals,
            'missing': gaps, 'safetyFailures': safety, 'monetaryCost': None,
            'scope': 'metric comparison only; original artifacts and evidence still require independent audit'}
