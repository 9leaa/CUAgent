"""New input mode uses original full evidence and synthetic independent review."""
import json
from pathlib import Path
import pytest
from backend.handoff_operator import record_review, review_protocol, review_input_mode
from backend.handoff_publication import prepare_publication
from backend.tests.test_handoff_operator import operator
from backend.tests.test_handoff_verify import evidence
from backend.tests.test_handoff_review import context

source, report = context()
pytestmark = pytest.mark.parametrize('evidence',[dict(source=source,report=report,
    protocol='p7-tool-submit-v1',inputMode='checked-draft-v1')],indirect=True)


def test_full_mode_review_and_publication_preparation_are_readonly(operator):
    kwargs, _, _ = operator
    for p in (kwargs['root']/'guest').rglob('*'):
        p.chmod(0o700 if p.is_dir() else 0o600)
    value = json.loads((kwargs['root']/'handoff-review-context.json').read_bytes())
    assert value['version'] == 3
    assert review_protocol(value) == 'p7-tool-submit-v1'
    assert review_input_mode(value) == 'checked-draft-v1'
    reviewed = record_review(**kwargs)
    assert reviewed['status'] == 'REVIEW_ACCEPTED'
    before = {p:p.read_bytes() for p in kwargs['root'].rglob('*') if p.is_file()}
    prepared = prepare_publication(kwargs['root'],Path(reviewed['receipt']).parent.name)
    assert prepared['inputMode'] == 'checked-draft-v1'
    assert prepared['status'] == 'PUBLICATION_EVIDENCE_PREPARED'
    assert not prepared['published'] and not prepared['databaseChanged']
    assert prepared['files']['result.txt'] == prepared['files']['document.txt']+b'\n'
    assert all(p.read_bytes()==raw for p,raw in before.items())


@pytest.mark.parametrize('fault',['missing','unknown','downgrade','extra','bool_version','protocol'])
@pytest.mark.parametrize('after_review',[False,True])
def test_context_cannot_change_or_downgrade_before_or_after_review(operator,fault,after_review):
    kwargs, _, save = operator
    reviewed = record_review(**kwargs) if after_review else None
    if reviewed: assert reviewed['status'] == 'REVIEW_ACCEPTED'
    path = kwargs['root']/'handoff-review-context.json'
    value = json.loads(path.read_bytes())
    if fault == 'missing': del value['inputMode']
    if fault == 'unknown': value['inputMode'] = 'auto'
    if fault == 'downgrade': value['version']=2; del value['inputMode']
    if fault == 'extra': value['allowFallback'] = True
    if fault == 'bool_version': value['version'] = True
    if fault == 'protocol': value['protocol'] = 'legacy-final-json'
    save(path,value)
    if after_review:
        with pytest.raises(ValueError): prepare_publication(kwargs['root'],Path(reviewed['receipt']).parent.name)
    else: assert record_review(**kwargs)['status'] == 'REVIEW_RECORD_REJECTED'


@pytest.mark.parametrize('decision',['FAIL','UNVERIFIED'])
def test_negative_review_never_prepares_publication(operator,decision):
    kwargs, review, save = operator
    review['checks'][0]['decision'] = decision
    save(kwargs['review_file'],review)
    result = record_review(**kwargs)
    assert result['status'] == 'REVIEW_NOT_PASSED'
    with pytest.raises(ValueError): prepare_publication(kwargs['root'],Path(result['receipt']).parent.name)


@pytest.mark.parametrize('file',['handoff-input-mode.json','result.txt','trace.jsonl'])
def test_original_guest_evidence_changed_after_review_cannot_publish(operator,file):
    kwargs, _, _ = operator
    result = record_review(**kwargs)
    assert result['status'] == 'REVIEW_ACCEPTED'
    path = kwargs['root']/'guest'/kwargs['root'].name/file
    path.write_bytes(path.read_bytes()+b'x')
    with pytest.raises((ValueError,RuntimeError)):
        prepare_publication(kwargs['root'],Path(result['receipt']).parent.name)
