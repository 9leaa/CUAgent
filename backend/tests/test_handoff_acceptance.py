import copy
import json
import pytest
import backend.handoff_acceptance as acceptance
from backend.handoff_contract import HandoffSubmission


@pytest.mark.parametrize('name', acceptance.CASES)
def test_frozen_case_consistency_and_original_source_positions(name):
    value, checked = acceptance.load_acceptance_case(name)
    assert checked['status'] == 'ACCEPTANCE_FIXTURE_CONSISTENT'
    assert checked['semanticVerified'] is checked['realExecutionVerified'] is False
    source = HandoffSubmission.model_validate(value['input'])
    sources = {f'notes/{n.id}': n.content for n in source.notes}
    sources.update(tasksCsv=source.tasksCsv, previousReport=source.previousReport)
    expected = {(r['id'], e['sourceId']): e['quote'] for r in value['rubric']['requirements'] for e in r['evidence']}
    for ref in checked['references']:
        assert sources[ref['sourceId']][ref['start']:ref['end']] == expected[ref['requirementId'], ref['sourceId']]
        assert ref['sourceSha256'] == source.source_hashes()[ref['sourceId']]


def test_distinct_business_edges_are_frozen_not_reports():
    normal, _ = acceptance.load_acceptance_case('normal')
    conflict, _ = acceptance.load_acceptance_case('conflict')
    dependencies, _ = acceptance.load_acceptance_case('dependencies')
    assert normal['rubric']['conflictTasks'] == []
    assert conflict['rubric']['conflictTasks'] == ['C1']
    assert conflict['rubric']['overdue'] == ['C3']
    assert dependencies['rubric']['overdue'] == ['D1', 'D2']
    assert dependencies['rubric']['unknownOwners'] == ['D4']
    for case in (normal, conflict, dependencies):
        assert set(case) == {'input', 'rubric'}
        # Only this typed input may be submitted; no reviewer expected prose.
        assert 'rubric' not in HandoffSubmission.model_validate(case['input']).model_dump()
        with pytest.raises(ValueError): HandoffSubmission.model_validate(case)


@pytest.mark.parametrize('fault', ['counts', 'bool', 'overdue', 'unknown', 'quote', 'source', 'uncovered', 'duplicate', 'task', 'empty', 'conflict-evidence', 'extra'])
def test_bad_rubric_is_not_consistent(fault):
    value, _ = acceptance.load_acceptance_case('conflict'); value = copy.deepcopy(value)
    rubric = value['rubric']; row = rubric['requirements'][0]
    if fault == 'counts': rubric['counts']['done'] = 1
    elif fault == 'bool': rubric['counts']['todo'] = True
    elif fault == 'overdue': rubric['overdue'] = []
    elif fault == 'unknown': rubric['unknownOwners'] = []
    elif fault == 'quote': row['evidence'][0]['quote'] = 'not original'
    elif fault == 'source': row['evidence'][0]['sourceId'] = 'unknown'
    elif fault == 'uncovered': rubric['requirements'].pop()
    elif fault == 'duplicate': rubric['requirements'].append(copy.deepcopy(row))
    elif fault == 'task': row['taskIds'] = ['invented']
    elif fault == 'empty': row['mustNotExpress'] = ''
    elif fault == 'conflict-evidence': row['evidence'].pop()
    else: value['extra'] = True
    with pytest.raises(ValueError): acceptance.inspect_acceptance_case(value)


def test_frozen_hash_rejects_later_edits(tmp_path, monkeypatch):
    original = acceptance.DIRECTORY
    for name in ('manifest', *acceptance.CASES):
        (tmp_path / (name+'.json')).write_bytes((original / (name+'.json')).read_bytes())
    path = tmp_path / 'normal.json'
    value = json.loads(path.read_bytes()); value['rubric']['requirements'][0]['mustExpress'] += ' 新增条件'
    path.write_text(json.dumps(value, ensure_ascii=False))
    monkeypatch.setattr(acceptance, 'DIRECTORY', tmp_path)
    with pytest.raises(ValueError): acceptance.load_acceptance_case('normal')


@pytest.mark.parametrize('name', ['../normal', '/tmp/normal', 'fourth'])
def test_no_arbitrary_fixture_path(name):
    with pytest.raises(ValueError): acceptance.load_acceptance_case(name)
