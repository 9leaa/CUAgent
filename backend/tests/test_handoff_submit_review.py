import json
from pathlib import Path

import pytest
from backend.handoff_operator import record_review, review_protocol
from backend.handoff_publication import prepare_publication
from backend.tests.test_handoff_operator import operator
from backend.tests.test_handoff_verify import evidence
from backend.tests.test_handoff_review import context

source, report = context()
pytestmark = pytest.mark.parametrize('evidence', [dict(source=source, report=report,
    protocol='p7-tool-submit-v1')], indirect=True)


def test_new_protocol_real_reverification_review_and_readonly_publication(operator):
    kwargs, _, _ = operator
    # Same permissions as the production bundle collector, not new authority.
    for path in (kwargs['root'] / 'guest').rglob('*'):
        path.chmod(0o700 if path.is_dir() else 0o600)
    result = record_review(**kwargs)
    assert result['status'] == 'REVIEW_ACCEPTED' and not result['published']
    digest = Path(result['receipt']).parent.name
    before = {p: p.read_bytes() for p in kwargs['root'].rglob('*') if p.is_file()}
    prepared = prepare_publication(kwargs['root'], digest)
    assert prepared['status'] == 'PUBLICATION_EVIDENCE_PREPARED'
    assert not prepared['published'] and not prepared['databaseChanged']
    assert prepared['files']['result.txt'] == prepared['files']['document.txt'] + b'\n'
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize('fault', ['missing', 'unknown', 'downgrade', 'bool_version', 'extra'])
def test_new_context_no_silent_fallback(operator, fault):
    kwargs, _, save = operator
    path = kwargs['root'] / 'handoff-review-context.json'
    data = json.loads(path.read_bytes())
    if fault == 'missing': del data['protocol']
    if fault == 'unknown': data['protocol'] = 'auto'
    if fault == 'downgrade': data['version'] = 1; del data['protocol']
    if fault == 'bool_version': data['version'] = True
    if fault == 'extra': data['allowFallback'] = True
    save(path, data)
    assert record_review(**kwargs)['status'] == 'REVIEW_RECORD_REJECTED'


@pytest.mark.parametrize('decision', ['FAIL', 'UNVERIFIED'])
def test_new_protocol_negative_semantic_review_never_publishes(operator, decision):
    kwargs, review, save = operator
    review['checks'][0]['decision'] = decision
    save(kwargs['review_file'], review)
    result = record_review(**kwargs)
    assert result['status'] == 'REVIEW_NOT_PASSED'
    with pytest.raises(ValueError):
        prepare_publication(kwargs['root'], Path(result['receipt']).parent.name)


def test_protocol_mutation_after_accepted_review_blocks_publication(operator):
    kwargs, _, save = operator
    result = record_review(**kwargs)
    assert result['status'] == 'REVIEW_ACCEPTED'
    path = kwargs['root'] / 'handoff-review-context.json'
    data = json.loads(path.read_bytes()); data['version'] = 1; del data['protocol']; save(path, data)
    with pytest.raises(ValueError):
        prepare_publication(kwargs['root'], Path(result['receipt']).parent.name)
