"""Read-only preparation for a later original-task publication transaction.

No model tool, DB mutation, file publication or automatic semantic proof.
The current local OS user is the authority; reviewer labels are declarations.
"""
import hashlib
import os
import re
from datetime import datetime, timezone
from backend.desktop_collect import private_path
from backend.handoff_operator import read_private
from backend.handoff_contract import HandoffSubmission
from backend.handoff_document import expected_document
from backend.handoff_result import canonical
from backend.handoff_review import validate_independent_review
from backend.handoff_session import require, strict_json
from backend.handoff_verify import verify_handoff_execution


def prepare_publication(root, review_sha256):
    root = private_path(root, directory=True)
    require(re.fullmatch(r'p2-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', root.name))
    require(type(review_sha256) is str and re.fullmatch('[0-9a-f]{64}', review_sha256))
    attempt = private_path(root / 'handoff-reviews' / review_sha256, directory=True)
    originals = {}

    def read(path, limit):
        raw = read_private(path, limit)
        originals[path] = (raw, limit)
        return raw

    def value(path, limit):
        return strict_json(read(path, limit).decode())

    raw_review = read(attempt / 'review.json', 128*1024)
    require(hashlib.sha256(raw_review).hexdigest() == review_sha256)
    review = strict_json(raw_review.decode())
    intent = value(attempt / 'intent.json', 4096)
    receipt = value(attempt / 'receipt.json', 128*1024)
    authority = dict(transport='local-os-user', uid=os.getuid(),
        reviewerKind=review['reviewer']['kind'], reviewerId=review['reviewer']['id'],
        authenticatedReviewerLabel=False)
    require(type(intent) is dict and set(intent) == {'version', 'runId', 'reviewFileSha256', 'recordedAt', 'authority'})
    when = datetime.fromisoformat(intent['recordedAt'])
    require(when.utcoffset() is not None and when <= datetime.now(timezone.utc))
    require(canonical(intent) == canonical(dict(version=1, runId=root.name,
        reviewFileSha256=review_sha256, recordedAt=intent['recordedAt'], authority=authority)))
    context = value(root / 'handoff-review-context.json', 384*1024)
    previous = value(root / 'handoff-execution-verification.json', 1024*1024)
    require(type(context) is dict and set(context) == {'version', 'submission', 'sessionId', 'binding', 'home'}
            and type(context['version']) is int and context['version'] == 1)
    source = HandoffSubmission.model_validate(context['submission'])
    guest = root / 'guest' / root.name
    current = verify_handoff_execution(root, guest_directory=guest, home=context['home'],
        submission=source, session_id=context['sessionId'], binding=context['binding'])
    require(canonical(current) == canonical(previous))
    verdict = validate_independent_review(review, submission=source, report=current['result'],
        execution=current, case_name=review['binding']['caseName'])
    require(verdict['status'] == 'REVIEW_ACCEPTED' and verdict['reviewAccepted'] is True)
    require(canonical(receipt) == canonical(dict(version=1, runId=root.name, result=verdict,
        authority=authority, reviewFileSha256=review_sha256, published=False, databaseChanged=False)))
    document = read(guest / 'artifacts' / ('handoff-' + root.name + '.txt'), 4096)
    result = read(guest / 'result.txt', 4097)
    require(document == expected_document(source, current['result'], run_id=root.name,
        session_id=context['sessionId']) and result == document + b'\n')
    files = {'document.txt': document, 'result.txt': result, 'report.json': canonical(current['result'])}
    for path, (raw, limit) in originals.items():
        require(read_private(path, limit) == raw)
    return dict(status='PUBLICATION_EVIDENCE_PREPARED', published=False, databaseChanged=False,
        binding=verdict['binding'], executionBinding=context['binding'],
        submission=source.model_dump(mode='json'), reviewFileSha256=review_sha256,
        reviewReceiptSha256=hashlib.sha256(originals[attempt / 'receipt.json'][0]).hexdigest(),
        artifacts={name: dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)) for name, raw in files.items()},
        files=files)
