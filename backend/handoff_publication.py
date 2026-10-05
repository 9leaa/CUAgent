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
        binding=verdict['binding'], executionBinding=context['binding'], rawCalls=current['guest']['rawCalls'],
        submission=source.model_dump(mode='json'), reviewFileSha256=review_sha256,
        reviewReceiptSha256=hashlib.sha256(originals[attempt / 'receipt.json'][0]).hexdigest(),
        artifacts={name: dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)) for name, raw in files.items()},
        files=files)


def publish_reviewed_task(service, task_id, review_sha256):
    """Trusted local operator only. An unknown outcome must be queried, not retried."""
    from pathlib import Path
    from sqlalchemy import select
    from backend.desktop_collect import save_exclusive
    from backend.models import Artifact, Attempt, Event, Resource, Task
    from backend.service import Conflict

    with service.sessions.begin() as db:
        resource = db.get(Resource, 'desktop', with_for_update=True)
        task = db.get(Task, task_id, with_for_update=True)
        if (not resource or resource.owner is not None or resource.task_id is not None
                or resource.expires_at is not None or not task or task.status != 'UNVERIFIED'
                or task.payload.get('kind') != 'project-handoff' or not task.run_dir):
            raise Conflict('HANDOFF_PUBLICATION_STATE_REQUIRED')
        root = private_path(Path(task.run_dir), directory=True)
        require(root.is_relative_to(service.settings.root.resolve()) and root.name == 'p2-' + task.id)
        require(task.owner is not None and type(task.epoch) is int and task.epoch > 0)
        attempts = list(db.scalars(select(Attempt).where(Attempt.task_id == task.id, Attempt.epoch == task.epoch)))
        require(len(attempts) == 1 and attempts[0].owner == task.owner and attempts[0].finished_at is not None)
        require(db.scalar(select(Attempt.id).where(Attempt.task_id == task.id, Attempt.finished_at.is_(None))) is None)
        prior = db.scalar(select(Event).where(Event.task_id == task.id, Event.kind == 'finished').order_by(Event.id.desc()).limit(1))
        require(prior is not None and prior.data.get('status') == 'UNVERIFIED')
        require(db.scalar(select(Artifact.id).where(Artifact.task_id == task.id)) is None)
        control_path = service.settings.root / 'controls' / (task.id + '.json')
        raw_control = read_private(control_path, 4096)
        control = strict_json(raw_control.decode())
        identity = dict(version=1, runId=root.name, owner=task.owner, epoch=task.epoch)
        require(control.get('stopped') is True and all(control.get(k) == v for k, v in identity.items()))
        prepared = prepare_publication(root, review_sha256)
        require(canonical(prepared['executionBinding']) == canonical(identity)
                and prepared['binding']['sessionId'] == task.session_id
                and canonical(prepared['submission']) == canonical(task.payload)
                and hashlib.sha256(canonical(task.payload)).hexdigest() == task.request_sha256
                and type(task.calls) is int and 1 <= task.calls <= 30 and task.calls == prepared['rawCalls'])
        workspace = private_path(root / 'workspace', directory=True)
        require(read_private(control_path, 4096) == raw_control)
        intent = dict(version=1, taskId=task.id, sessionId=task.session_id, identity=identity,
            previousEventId=prior.id, previousErrorCode=task.error_code, reviewFileSha256=review_sha256,
            reviewReceiptSha256=prepared['reviewReceiptSha256'], artifacts=prepared['artifacts'])
        save_exclusive(root / 'handoff-publication-intent.json', canonical(intent))
        for name, raw in prepared['files'].items():
            save_exclusive(workspace / name, raw)
        for name, raw in prepared['files'].items():
            require(read_private(workspace / name, 128*1024) == raw)
            db.add(Artifact(task_id=task.id, name=name, **prepared['artifacts'][name]))
        require(read_private(control_path, 4096) == raw_control)
        db.add(Event(task_id=task.id, kind='handoff_published', external_id='handoff-publication', data=intent))
        task.status, task.error_code = 'SUCCEEDED', None
        service.event(db, task, 'finished', status='SUCCEEDED', reviewFileSha256=review_sha256,
                      previousEventId=prior.id, acceptanceBasis='independent-review-attestation')
    return dict(status='SUCCEEDED', taskId=task_id, reviewFileSha256=review_sha256)
