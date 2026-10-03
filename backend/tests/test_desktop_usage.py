import json
import pytest
from backend.desktop_usage import desktop_usage, FIELDS


@pytest.fixture
def evidence(tmp_path):
    binding = {'runId': tmp_path.name, 'sessionId': 'session-test', 'cwd': str(tmp_path / 'workspace')}
    p = tmp_path / 'desktop-session-binding.json'
    p.write_text(json.dumps(binding)); p.chmod(0o600)
    return tmp_path


def write(root, rows):
    path = root / 'session.jsonl'
    path.write_text('\n'.join(json.dumps(dict(seq=i, **r)) for i, r in enumerate(rows)))
    path.chmod(0o600)


def rows(reason='completed'):
    return [{'type': 'request/header', 'data': {'header': {'config': {
        'provider': 'deepseek-account', 'model': 'deepseek-flash', 'reasoningEffort': 'off'}}}},
        {'type': 'assistant/message', 'data': {'usage': dict(zip(FIELDS, [10, 3, 2, 1, 16]))}},
        {'type': 'assistant/message', 'data': {'usage': dict(zip(FIELDS, [4, 2, 0, 0, 6]))}},
        {'type': 'turn/end', 'data': {'reason': {'kind': reason}}}]


@pytest.mark.parametrize('reason', ['completed', 'cancelled', 'failed'])
def test_all_terminal_messages_count_even_failed(evidence, reason):
    write(evidence, rows(reason))
    value = desktop_usage(evidence, 'session-test')
    assert value['available'] and value['totalTokens'] == 22 and value['cacheReadTokens'] == 2
    assert value['monetaryCost'] is None and len(value['sessionSha256']) == 64


@pytest.mark.parametrize('fault', ['missing', 'wrong-session', 'partial', 'invalid-total', 'boolean', 'no-usage', 'public'])
def test_incomplete_or_invalid_evidence_is_unknown_not_zero(evidence, fault):
    data = rows()
    if fault == 'partial': data.pop()
    if fault == 'invalid-total': data[1]['data']['usage']['totalTokens'] += 1
    if fault == 'boolean': data[1]['data']['usage']['inputTokens'] = True
    if fault == 'no-usage': data[1]['data'].pop('usage')
    if fault != 'missing': write(evidence, data)
    if fault == 'public': (evidence / 'session.jsonl').chmod(0o644)
    value = desktop_usage(evidence, 'other' if fault == 'wrong-session' else 'session-test')
    assert not value['available']
    assert all(value[k] is None for k in FIELDS)
