"""Synthetic review/Driver evidence; never real semantic acceptance."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from backend.handoff_operator import record_review
from backend.handoff_publication import prepare_publication
from backend.handoff_result import canonical
from backend.tests.test_handoff_operator import operator
from backend.tests.test_handoff_verify import evidence
from backend.tests.test_handoff_review import context

pytestmark = pytest.mark.parametrize('evidence', [context()], indirect=True)


def recorded(operator):
    kwargs, _, _ = operator
    # Match production collect_handoff_bundle's private host extraction.
    for path in (kwargs['root'] / 'guest').rglob('*'):
        path.chmod(0o700 if path.is_dir() else 0o600)
    result = record_review(**kwargs)
    assert result['status'] == 'REVIEW_ACCEPTED'
    path = Path(result['receipt'])
    return kwargs['root'], path.parent.name, path


def test_prepares_original_bytes_without_writes(operator):
    root, digest, _ = recorded(operator)
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = prepare_publication(root, digest)
    assert result['status'] == 'PUBLICATION_EVIDENCE_PREPARED'
    assert result['published'] is False and result['databaseChanged'] is False
    assert set(result['files']) == {'document.txt', 'result.txt', 'report.json'}
    assert result['files']['result.txt'] == result['files']['document.txt'] + b'\n'
    for name, raw in result['files'].items():
        assert result['artifacts'][name] == dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    assert result['files']['document.txt'] == (root / 'guest' / root.name / 'artifacts' / ('handoff-' + root.name + '.txt')).read_bytes()
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('fault', ['uid', 'accepted', 'binding', 'published', 'intent', 'review', 'guest', 'session', 'context', 'extra', 'symlink'])
def test_changed_receipt_or_evidence_never_prepares(operator, fault):
    root, digest, receipt = recorded(operator)
    value = json.loads(receipt.read_bytes())
    if fault == 'uid': value['authority']['uid'] += 1
    elif fault == 'accepted': value['result']['reviewAccepted'] = False
    elif fault == 'binding': value['result']['binding']['sessionId'] = 'other'
    elif fault == 'published': value['published'] = True
    elif fault == 'extra': value['extra'] = True
    elif fault in ('intent', 'review', 'guest', 'session', 'context'):
        path = {'intent': receipt.parent / 'intent.json', 'review': receipt.parent / 'review.json',
                'guest': root / 'guest' / root.name / 'result.txt', 'session': root / 'session.jsonl',
                'context': root / 'handoff-review-context.json'}[fault]
        path.write_bytes(b'{}')
    else:
        target = receipt.with_name('moved.json'); receipt.rename(target); receipt.symlink_to(target)
    if fault in ('uid', 'accepted', 'binding', 'published', 'extra'): receipt.write_bytes(canonical(value))
    with pytest.raises((ValueError, KeyError, RuntimeError)): prepare_publication(root, digest)
    assert not (root / 'handoff-publication-intent.json').exists()


@pytest.mark.parametrize('decision', ['FAIL', 'UNVERIFIED'])
def test_negative_review_cannot_be_published(operator, decision):
    kwargs, review, save = operator
    review['checks'][0]['decision'] = decision; save(kwargs['review_file'], review)
    result = record_review(**kwargs)
    with pytest.raises(ValueError): prepare_publication(kwargs['root'], Path(result['receipt']).parent.name)


@pytest.mark.parametrize('digest', ['../review', '', 'A'*64, True])
def test_review_identifier_is_not_a_path(operator, digest):
    with pytest.raises(ValueError): prepare_publication(operator[0]['root'], digest)


def test_receipt_changed_during_full_reverification_rejected(operator):
    root, digest, receipt = recorded(operator)
    from backend.handoff_verify import verify_handoff_execution
    def changed(*args, **kwargs):
        result = verify_handoff_execution(*args, **kwargs)
        receipt.write_bytes(b'{}')
        return result
    with patch('backend.handoff_publication.verify_handoff_execution', side_effect=changed):
        with pytest.raises(ValueError): prepare_publication(root, digest)
