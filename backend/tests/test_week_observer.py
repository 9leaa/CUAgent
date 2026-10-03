"""Synthetic acceptance-gate tests, never a claim of elapsed real-week evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import Mock
import httpx
import pytest
from backend.week_observer import assess, notices, observe, reconstruct_sources, verify_api_evidence
from backend.workflow_preview import preview
from backend.workflow_sources import operations_snapshot

START = datetime(2026, 10, 3, tzinfo=timezone.utc)


def fixture():
    items = [dict(id=str(i), due_at=(START + timedelta(days=i)).isoformat()) for i in range(7)]
    plan = dict(config=dict(startAt=START.isoformat(), runs=7, baselineCommit='base'), occurrences=7, items=items)
    receipts = [dict(id=str(i), status='VERIFIED', tasks=[dict(id=f't{i}-{j}', session_id=f's{i}-{j}')
                                                      for j in range(2)], projectRange=dict(
        fromExclusive='base' if i == 0 else f'commit{i-1}', toInclusive=f'commit{i}')) for i in range(7)]
    return plan, receipts


def test_short_runs_never_replace_168_hours():
    plan, receipts = fixture()
    assert assess(plan, receipts, START + timedelta(days=7))['status'] == 'PASS'
    assert assess(plan, receipts, START + timedelta(days=7, seconds=-1))['status'] == 'INCOMPLETE'
    assert assess(plan, receipts, START)['userAdoption'] == 'NOT_ASSESSED'


@pytest.mark.parametrize('broken', ['missing', 'missed', 'repeat_day', 'repeat_task', 'repeat_session', 'wrong_receipt', 'one_run', 'git_gap'])
def test_missing_failed_or_duplicate_never_passes(broken):
    plan, receipts = fixture()
    if broken == 'missing': receipts.pop()
    if broken == 'missed': receipts[1]['status'] = 'MISSED'
    if broken == 'repeat_day': plan['items'][1]['due_at'] = plan['items'][0]['due_at']
    if broken == 'repeat_task': receipts[1]['tasks'][0]['id'] = receipts[0]['tasks'][0]['id']
    if broken == 'repeat_session': receipts[1]['tasks'][0]['session_id'] = receipts[0]['tasks'][0]['session_id']
    if broken == 'wrong_receipt': receipts[1]['id'] = 'foreign'
    if broken == 'one_run': plan['config']['runs'] = 1
    if broken == 'git_gap': receipts[1]['projectRange']['fromExclusive'] = 'other'
    assert assess(plan, receipts, START + timedelta(days=8))['status'] == 'INCOMPLETE'


def test_frozen_unknown_usage_reconstructs_without_querying_later_database(monkeypatch):
    project = {'workflow': 'project-changes', 'source': {'fromExclusive': 'a'*40, 'toInclusive': 'b'*40},
               'payload': {'date': '2026-10-03'}}
    original = deepcopy(project)
    monkeypatch.setattr('backend.week_observer.project_snapshot', Mock(return_value=original))
    operations = operations_snapshot([dict(id='a'*36, status='FAILED', calls=2, updatedAt=START.isoformat(), usage=None)],
                                    START, START+timedelta(days=1), '2026-10-03')
    reconstruct_sources([project, operations])
    operations['payload']['notes'][0]['content'] = 'fabricated'
    with pytest.raises(ValueError): reconstruct_sources([project, operations])


def test_inbox_paginates_read_only():
    seen = []
    def handler(request):
        seen.append((request.method, request.url.params['after']))
        if request.url.params['after'] == '0':
            return httpx.Response(200, json={'items': [{'id': i} for i in range(1,101)], 'next_cursor': 100})
        return httpx.Response(200, json={'items': [{'id': 101}], 'next_cursor': 101})
    with httpx.Client(base_url='http://test', transport=httpx.MockTransport(handler)) as client:
        assert len(notices(client)) == 101
    assert seen == [('GET', '0'), ('GET', '100')]


def test_unavailable_api_leaves_failure_receipt_and_never_overwrites(tmp_path):
    output = tmp_path / 'receipt'
    with httpx.Client(base_url='http://test', transport=httpx.MockTransport(lambda r: httpx.Response(503))) as client:
        record = observe(client, None, 'plan', output)
        assert record['assessment']['status'] == 'INCOMPLETE'
        assert json.loads((output / 'receipt.json').read_text()) == record
        assert output.stat().st_mode & 0o077 == 0
        assert (output / 'receipt.json').stat().st_mode & 0o077 == 0
        with pytest.raises(FileExistsError): observe(client, None, 'plan', output)


def test_preview_never_submits_and_refuses_overwrite(tmp_path, payload, monkeypatch):
    sources = [{'workflow': name, 'payload': payload} for name in ['project-changes', 'task-operations']]
    collector = Mock(return_value=sources)
    monkeypatch.setattr('backend.workflow_preview.WorkflowCollector', Mock(return_value=collector))
    output = tmp_path / 'preview'
    args = dict(branch='p5-personal-workflows', baseline='a'*40, due=START, timezone='UTC', output=output)
    result = preview(None, **args)
    assert result['submitted'] is False
    body = json.loads((output / 'batch.json').read_text())
    assert len(body['tasks']) == 2 and all(t['inputMode'] == 'aggregate' for t in body['tasks'])
    with pytest.raises(FileExistsError): preview(None, **args)
    with pytest.raises(ValueError): preview(None, **dict(args, due=START.replace(tzinfo=None)))


def test_api_usage_metadata_does_not_mask_token_or_model_mismatch():
    model = dict(provider='deepseek-account', model='deepseek-flash', reasoningEffort='off')
    usage = dict(available=True, inputTokens=1, outputTokens=2, cacheReadTokens=3, cacheWriteTokens=0, totalTokens=6)
    verdict = dict(sessionId='session', rawCalls=9, usage=usage, model=model)
    state = dict(session_id='session', budget=dict(used=9, limit=30), usage=dict(usage, models=[model], monetaryCost=None))
    verify_api_evidence(state, verdict)
    for changed in [dict(totalTokens=7), dict(models=[]), dict(available=False)]:
        with pytest.raises(ValueError): verify_api_evidence(dict(state, usage=dict(state['usage'], **changed)), verdict)
