"""No model or GUI: guest candidate vs independent host draft validation."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/mac_vm'))
from handoff_submit import candidate
from backend.handoff_draft import check_draft
from backend.tests.test_handoff_result import fixture, RUN, SESSION


def inputs():
    source, report = fixture()
    draft = check_draft(source, json.dumps(report), run_id=RUN, session_id=SESSION)
    assert draft['status'] == 'DRAFT_STRUCTURE_VALID'
    return source.model_dump(mode='json'), {'report': report}, draft


def test_valid_original_object_has_no_execution_or_semantic_authority():
    source, args, draft = inputs()
    before = copy.deepcopy((source, args, draft))
    result = candidate(source, args, run_id=RUN, session_id=SESSION, draft=draft)
    assert result == dict(status='SUBMISSION_CANDIDATE_VALID', protocol='p7-tool-submit-v1',
                         reportSha256=hashlib.sha256(draft['canonicalJson'].encode()).hexdigest(),
                         documentSha256=draft['documentSha256'], semanticVerified=False, guiVerified=False)
    assert (source, args, draft) == before


@pytest.mark.parametrize('mode', ['raw', 'extra', 'missing', 'identity', 'fact', 'text',
                                 'no_draft', 'bad_draft', 'body', 'hash', 'canonical'])
def test_reject_changes_without_repair(mode):
    source, args, draft = inputs()
    if mode == 'raw': args = {'report': json.dumps(args['report'])}
    if mode == 'extra': args['sessionId'] = SESSION
    if mode == 'missing': args = {}
    if mode == 'identity': args['report']['sessionId'] = SESSION + 'x'
    if mode == 'fact': args['report']['tasks'][0]['owner'] = 'invented'
    if mode == 'text': args['report']['tasks'][0]['progress']['text'] = 'changed'
    if mode == 'no_draft': draft = None
    if mode == 'bad_draft': draft['status'] = 'DRAFT_REJECTED'
    if mode == 'body': draft['document'] += 'x'
    if mode == 'hash': draft['documentSha256'] = '0' * 64
    if mode == 'canonical': draft['canonicalJson'] = '{}'
    before = copy.deepcopy((source, args, draft))
    result = candidate(source, args, run_id=RUN, session_id=SESSION, draft=draft)
    assert result['status'] == 'SUBMISSION_REJECTED'
    assert (source, args, draft) == before


@pytest.mark.parametrize('value', [float('nan'), float('inf'), '\ud800', ('tuple',),
                                 {1: 'non-string key'}, 'x' * 65537, [0] * 65537])
def test_non_json_and_size_limits(value):
    source, args, draft = inputs()
    args['report']['extra'] = value
    assert candidate(source, args, run_id=RUN, session_id=SESSION, draft=draft)['status'] == 'SUBMISSION_REJECTED'


def test_cycles_and_deep_values_are_bounded():
    source, args, draft = inputs()
    args['report']['cycle'] = args['report']
    assert candidate(source, args, run_id=RUN, session_id=SESSION, draft=draft)['code'] == 'REPORT_LIMIT'


def test_key_order_not_textual_draft_serialization_is_binding():
    source, args, draft = inputs()
    args['report'] = dict(reversed(list(args['report'].items())))
    assert candidate(source, args, run_id=RUN, session_id=SESSION, draft=draft)['status'] == 'SUBMISSION_CANDIDATE_VALID'
