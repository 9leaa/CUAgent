import json
from pathlib import Path
import pytest
from agent.daily_report import markdown, prepare, sha
from backend.checkpoint import EvidenceChanged
from backend.recovery import partial_report_plan


def partial(tmp_path):
    run = tmp_path / 'partial'
    prepare(Path(__file__).resolve().parents[2] / 'agent/fixtures/daily-report/spec.json', run)
    approval = json.loads((run / 'approval.json').read_text())
    expected = json.loads((run / 'oracle.json').read_text())['expected']
    output = json.dumps(expected, ensure_ascii=False).encode()
    (run / 'workspace/report.json').write_bytes(output)
    identity = {k: approval[k] for k in ('runId', 'sessionId')}
    rows = [{**identity, 'event': 'dispatch', 'callId': 'write', 'name': 'workspace_write', 'used': 1},
            {**identity, 'event': 'result', 'callId': 'write', 'name': 'workspace_write', 'outcome': 'returned',
             'artifact': {'sha256': sha(output), 'bytes': len(output)}}]
    (run / 'audit/calls.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    return run, rows


def test_partial_plan_preserves_original_identity_and_only_missing_output(tmp_path):
    run, _ = partial(tmp_path)
    before = (run / 'workspace/report.json').read_bytes()
    plan = partial_report_plan(run)
    assert plan['missing'] == ['report.md'] and plan['minimumCalls'] == 4
    assert plan['evidence']['remaining'] == 29
    assert (run / 'workspace/report.json').read_bytes() == before
    assert not (run / 'workspace/report.md').exists()


@pytest.mark.parametrize('fault', ['unknown', 'wrong_json', 'missing_write', 'false_hash', 'changed_input'])
def test_partial_plan_does_not_trust_file_presence(tmp_path, fault):
    run, rows = partial(tmp_path)
    if fault == 'unknown':
        rows.pop()
    elif fault == 'wrong_json':
        (run / 'workspace/report.json').write_text('{}')
    elif fault == 'missing_write':
        rows.clear()
    elif fault == 'false_hash':
        rows[1]['artifact']['sha256'] = '0' * 64
    else:
        path = run / 'workspace/inputs/progress.md'
        path.chmod(0o600)
        path.write_text('changed input')
    (run / 'audit/calls.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    with pytest.raises((EvidenceChanged, ValueError)):
        partial_report_plan(run)


def test_continuation_cannot_overspend_original_budget(tmp_path):
    run, rows = partial(tmp_path)
    identity = {k: rows[0][k] for k in ('runId', 'sessionId')}
    for used in range(2, 28):
        call = {**identity, 'name': 'workspace_read', 'callId': str(used)}
        rows.extend([{**call, 'event': 'dispatch', 'used': used},
                     {**call, 'event': 'result', 'outcome': 'returned'}])
    (run / 'audit/calls.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    with pytest.raises(EvidenceChanged, match='INSUFFICIENT_CONTINUATION_BUDGET'):
        partial_report_plan(run)


def test_existing_correct_markdown_is_read_only_on_continuation(tmp_path):
    run, rows = partial(tmp_path)
    expected = json.loads((run / 'oracle.json').read_text())['expected']
    output = markdown(expected).encode()
    (run / 'workspace/report.md').write_bytes(output)
    identity = {k: rows[0][k] for k in ('runId', 'sessionId')}
    call = {**identity, 'name': 'workspace_daily_report', 'callId': 'render'}
    child = {**identity, 'name': 'workspace_read', 'callId': 'render:daily-source'}
    rows.extend([{**call, 'event': 'dispatch', 'used': 2},
                 {**child, 'event': 'dispatch', 'used': 3},
                 {**child, 'event': 'result', 'outcome': 'returned', 'artifact': rows[1]['artifact']},
                 {**call, 'event': 'result', 'outcome': 'returned',
                  'artifact': {'bytes': len(output), 'sha256': sha(output)}}])
    (run / 'audit/calls.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    plan = partial_report_plan(run)
    assert plan['missing'] == [] and plan['minimumCalls'] == 2
