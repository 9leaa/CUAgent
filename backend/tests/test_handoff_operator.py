"""Local recorder with real combination checks; synthetic Driver/reviewer only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch
import pytest
from backend.handoff_operator import record_review, read_private
from backend.handoff_result import canonical
from backend.handoff_review import review_subject
from backend.handoff_verify import verify_handoff_execution
from backend.tests.test_handoff_verify import evidence
from backend.tests.test_handoff_review import context, attestation

pytestmark = pytest.mark.parametrize('evidence', [context()], indirect=True)


@pytest.fixture
def operator(evidence, tmp_path):
    args, _, _ = evidence; root = args['root']
    guest = root / 'guest' / root.name; guest.parent.mkdir(mode=0o700)
    shutil.copytree(args['guest_directory'], guest)
    args = dict(args, guest_directory=guest)
    protocol = json.loads((root / 'desktop-session-binding.json').read_bytes()).get('protocol', 'legacy-final-json')
    mode = json.loads((root / 'desktop-session-binding.json').read_bytes()).get('inputMode','literal-text')
    execution = verify_handoff_execution(**args, protocol=protocol, draft_input_mode=mode)
    source = args['submission']; report = execution['result']
    review, _ = attestation(source, report)
    binding, _, _, snapshots, _ = review_subject(source, report, execution, 'normal')
    review.update(binding=binding, imagesReviewed=snapshots, reviewedAt='2026-10-05T00:00:00+00:00')
    def save(path, value):
        path.write_bytes(canonical(value)); path.chmod(0o600)
    review_context = dict(version=1, submission=source.model_dump(mode='json'),
        sessionId=args['session_id'], binding=args['binding'], home=str(args['home']))
    if protocol == 'p7-tool-submit-v1': review_context.update(version=2, protocol=protocol)
    if mode == 'checked-draft-v1': review_context.update(version=3,inputMode=mode)
    save(root / 'handoff-review-context.json', review_context)
    save(root / 'handoff-execution-verification.json', execution)
    record = tmp_path / 'review.json'; save(record, review)
    return dict(root=root, review_file=record, reviewer_kind='codex', reviewer_id='synthetic-reviewer'), review, save


def test_real_reverification_records_attestation_without_publishing(operator):
    kwargs, _, _ = operator
    originals = {p: p.read_bytes() for p in kwargs['root'].rglob('*') if p.is_file()}
    result = record_review(**kwargs)
    assert result['status'] == 'REVIEW_ACCEPTED' and result['published'] is False
    receipt = json.loads(Path(result['receipt']).read_bytes())
    assert receipt['authority']['uid'] == os.getuid()
    assert receipt['authority']['authenticatedReviewerLabel'] is False
    assert receipt['result']['automaticSemanticProof'] is False
    assert receipt['databaseChanged'] is False
    assert all(p.read_bytes() == data for p, data in originals.items())
    assert all(p.stat().st_mode & 0o077 == 0 for p in Path(result['receipt']).parent.rglob('*'))
    with pytest.raises(FileExistsError): record_review(**kwargs)


@pytest.mark.parametrize('decision', ['FAIL', 'UNVERIFIED'])
def test_negative_review_kept_as_negative(operator, decision):
    kwargs, review, save = operator
    review['checks'][0]['decision'] = decision; save(kwargs['review_file'], review)
    result = record_review(**kwargs)
    assert result['status'] == 'REVIEW_NOT_PASSED'
    receipt = json.loads(Path(result['receipt']).read_bytes())
    assert decision in receipt['result']['decisions'].values()


@pytest.mark.parametrize('fault', ['reviewer', 'source', 'execution', 'context', 'review', 'missing', 'symlink'])
def test_rejected_evidence_is_recorded_without_retry(operator, fault):
    kwargs, review, save = operator; root = kwargs['root']
    if fault == 'reviewer': kwargs['reviewer_id'] = 'different-operator'
    elif fault == 'source': (root / 'guest' / root.name / 'result.txt').write_bytes(b'changed')
    elif fault == 'execution':
        path = root / 'handoff-execution-verification.json'; value = json.loads(path.read_bytes()); value['semanticVerified'] = True; save(path, value)
    elif fault == 'context':
        path = root / 'handoff-review-context.json'; value = json.loads(path.read_bytes()); value['sessionId'] = 'other'; save(path, value)
    elif fault == 'review': review['checks'].pop(); save(kwargs['review_file'], review)
    elif fault == 'missing': (root / 'session.jsonl').unlink()
    else:
        path = root / 'handoff-execution-verification.json'; target = root / 'renamed.json'; path.rename(target); path.symlink_to(target)
    result = record_review(**kwargs)
    assert result['status'] == 'REVIEW_RECORD_REJECTED'
    assert Path(result['receipt']).exists()
    with pytest.raises(FileExistsError): record_review(**kwargs)


def test_failed_receipt_write_leaves_original_attempt(operator):
    kwargs, _, _ = operator
    from backend.desktop_collect import save_exclusive
    def write(path, data):
        if path.name == 'receipt.json': raise OSError('synthetic disk error')
        save_exclusive(path, data)
    with patch('backend.handoff_operator.save_exclusive', side_effect=write):
        with pytest.raises(OSError): record_review(**kwargs)
    attempts = list((kwargs['root'] / 'handoff-reviews').iterdir())
    assert len(attempts) == 1 and (attempts[0] / 'review.json').exists()
    with pytest.raises(FileExistsError): record_review(**kwargs)


def test_private_record_permissions_and_links_required(operator, tmp_path):
    kwargs, _, _ = operator; path = kwargs['review_file']
    path.chmod(0o644)
    with pytest.raises(ValueError): read_private(path, 128*1024)
    path.chmod(0o600)
    link = tmp_path / 'linked'; link.symlink_to(path)
    with pytest.raises(ValueError): read_private(link, 128*1024)
    hard = tmp_path / 'hard'; os.link(path, hard)
    with pytest.raises(ValueError): read_private(path, 128*1024)
    assert not (kwargs['root'] / 'handoff-reviews').exists()


def test_cli_actual_subprocess_records_once_and_reports_only_summary(operator):
    kwargs, _, _ = operator
    args = [sys.executable, '-m', 'backend.handoff_operator', '--root', str(kwargs['root']),
            '--review', str(kwargs['review_file']), '--reviewer-kind', 'codex', '--reviewer-id', kwargs['reviewer_id']]
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert set(summary) == {'status', 'receipt', 'published'} and summary['status'] == 'REVIEW_ACCEPTED'
    repeated = subprocess.run(args, capture_output=True, text=True, timeout=30)
    assert repeated.returncode == 1 and json.loads(repeated.stdout)['status'] == 'REVIEW_RECORD_UNCONFIRMED'
