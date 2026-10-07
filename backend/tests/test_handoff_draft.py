import copy
import json
import importlib.util
from pathlib import Path
import pytest
from backend.handoff_draft import check_draft, locate_quote
from backend.tests.test_handoff_result import fixture, RUN, SESSION


def check(source, data):
    return check_draft(source, json.dumps(data, ensure_ascii=False), run_id=RUN, session_id=SESSION)


def test_valid_draft_not_semantic_or_gui_acceptance():
    source, data = fixture(); before = copy.deepcopy(data)
    result = check(source, data)
    assert result['status'] == 'DRAFT_STRUCTURE_VALID'
    assert result['semanticVerified'] is result['guiVerified'] is False
    assert result['document'].endswith('\n')
    assert json.loads(result['canonicalJson']) == data == before


@pytest.mark.parametrize('raw,code', [('{"tasks":[}', 'JSON_SYNTAX'),
    ('{"x":1,"x":2}', 'JSON_NOT_STRICT'), ('NaN', 'JSON_NOT_STRICT'),
    ('[]', 'SCHEMA'), ('', 'DRAFT_SIZE_LIMIT'), ('x'*65537, 'DRAFT_SIZE_LIMIT'),
    ('\ud800', 'INVALID_UNICODE'), ({}, 'JSON_TEXT_REQUIRED'),
    pytest.param('['*2000+']'*2000, 'JSON_NOT_STRICT', id='excessive-depth')])
def test_invalid_json_no_repair(raw, code):
    source, _ = fixture()
    result = check_draft(source, raw, run_id=RUN, session_id=SESSION)
    assert result['code'] == code and 'document' not in result


@pytest.mark.parametrize('fault', ['missing_handoff','citation','count','identity','fact'])
def test_original_gates_preserved(fault):
    source, data = fixture()
    if fault == 'missing_handoff': del data['tasks'][0]['handoff']
    if fault == 'citation': data['tasks'][0]['progress']['citations'][0]['end'] = 1
    if fault == 'count': data['counts']['done'] = 2
    if fault == 'identity': data['runId'] = RUN + 'x'
    if fault == 'fact': data['tasks'][0]['owner'] = 'invented'
    result = check(source, data)
    assert result['status'] == 'DRAFT_REJECTED' and 'document' not in result


def test_schema_errors_do_not_echo_untrusted_input():
    source, data = fixture(); data['tasks'][0]['overdue'] = 'PRIVATE_INPUT'
    result = check(source, data)
    assert result['fields'] == [['tasks',0,'overdue']]
    assert 'PRIVATE_INPUT' not in json.dumps(result)


def test_quote_codepoints_exact_no_normalization():
    source, _ = fixture()
    result = locate_quote(source, source_id='notes/meeting', quote='🙂e\u0301')
    assert result['matches'] == [dict(start=2,end=5)]
    assert result['status'] == 'UNIQUE'
    assert locate_quote(source, source_id='notes/meeting', quote='🙂é')['status'] == 'NOT_FOUND'
    assert locate_quote(source, source_id='../../secret', quote='x')['status'] == 'SOURCE_NOT_FOUND'


def test_ambiguous_overlapping_quotes_bounded_not_selected():
    source, _ = fixture()
    source = source.model_copy(update={'previousReport':'a'*20})
    result = locate_quote(source, source_id='previousReport', quote='aa')
    assert result['status'] == 'AMBIGUOUS' and result['truncated']
    assert len(result['matches']) == 8
    assert result['matches'][1] == dict(start=1,end=3)


@pytest.mark.parametrize('quote', ['', ' ', 'x'*2049, '\ud800', 1])
def test_invalid_quote_rejected(quote):
    source, _ = fixture()
    with pytest.raises((ValueError, UnicodeError)):
        locate_quote(source, source_id='notes/meeting', quote=quote)


@pytest.mark.parametrize('source_id,quote', [('notes/meeting','🙂e\u0301'),
    ('notes/meeting','🙂é'),('previousReport','aa'),('tasksCsv','接口'),('../../secret','x')])
def test_host_guest_quote_projection_parity(source_id,quote):
    path = Path(__file__).resolve().parents[2] / 'tools/mac_vm/handoff_quote.py'
    spec = importlib.util.spec_from_file_location('quote_parity',path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    source, _ = fixture()
    source = source.model_copy(update={'previousReport':'a'*20})
    assert module.locate(source.model_dump(mode='json'),dict(sourceId=source_id,quote=quote)) == locate_quote(
        source,source_id=source_id,quote=quote)
