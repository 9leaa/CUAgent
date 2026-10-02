import json
import pytest
from backend.checkpoint import EvidenceChanged, snapshot


def fixture_run(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    ledger = tmp_path / 'calls.jsonl'
    approval = {'runId': 'original-run', 'sessionId': 'original-session',
                'ledgerPath': str(ledger), 'workspaceRoot': str(workspace)}
    (tmp_path / 'approval.json').write_text(json.dumps(approval))
    return ledger, workspace, {k: approval[k] for k in ('runId', 'sessionId')}


def test_checkpoint_preserves_prefix_budget_and_unknown_effect(tmp_path):
    ledger, workspace, identity = fixture_run(tmp_path)
    empty = snapshot(tmp_path)
    dispatch = {**identity, 'event': 'dispatch', 'callId': 'one', 'name': 'workspace_write', 'used': 1}
    ledger.write_text(json.dumps(dispatch) + '\n')
    pending = snapshot(tmp_path, empty)
    assert pending['used'] == 1 and pending['remaining'] == 29
    assert pending['pending'] == {'one': 'workspace_write'}
    # A file existing does not resolve a missing execution result.
    (workspace / 'report.json').write_text('{}')
    assert snapshot(tmp_path, pending)['pending'] == pending['pending']
    with ledger.open('a') as output:
        output.write(json.dumps({**identity, 'event': 'result', 'callId': 'one', 'name': 'workspace_write'}) + '\n')
    complete = snapshot(tmp_path, pending)
    assert complete['used'] == 1 and complete['pending'] == {}
    (workspace / 'report.json').write_text('{"changed":true}')
    with pytest.raises(EvidenceChanged, match='ARTIFACT_CHANGED'):
        snapshot(tmp_path, complete)
    ledger.write_bytes(b'')
    with pytest.raises(EvidenceChanged, match='PREFIX_CHANGED'):
        snapshot(tmp_path, pending)


@pytest.mark.parametrize('kind', ['foreign', 'partial', 'duplicate', 'unmatched', 'symlink'])
def test_checkpoint_rejects_invalid_evidence(tmp_path, kind):
    ledger, workspace, identity = fixture_run(tmp_path)
    row = {**identity, 'event': 'dispatch', 'callId': 'one', 'name': 'workspace_read', 'used': 1}
    if kind == 'foreign':
        row['sessionId'] = 'other'
    if kind == 'unmatched':
        row['event'] = 'result'
    text = json.dumps(row) + ('\n' if kind != 'partial' else '')
    ledger.write_text(text * (2 if kind == 'duplicate' else 1))
    if kind == 'symlink':
        (workspace / 'report.json').symlink_to(ledger)
    with pytest.raises(EvidenceChanged):
        snapshot(tmp_path)
