"""Local OS-user review recording only; no dispatch, database or publication."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from backend.desktop_collect import private_path, save_exclusive
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import canonical
from backend.handoff_session import strict_json, require
from backend.handoff_review import validate_independent_review
from backend.handoff_verify import verify_handoff_execution


def read_private(path, limit):
    path = private_path(path, directory=False)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_uid, s.st_nlink)
    with os.fdopen(fd, 'rb') as file:
        info = os.fstat(file.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077
                and info.st_nlink == 1 and 0 < info.st_size <= limit)
        raw = file.read(info.st_size + 1)
        require(len(raw) == info.st_size and signature(os.fstat(file.fileno())) == signature(info))
    require(signature(path.stat(follow_symlinks=False)) == signature(info))
    return raw


def review_protocol(context):
    """Trusted private context selects a version; never infer from model output."""
    fields = {'version', 'submission', 'sessionId', 'binding', 'home'}
    require(type(context) is dict and type(context.get('version')) is int)
    if context['version'] == 1:
        require(set(context) == fields)
        return 'legacy-final-json'
    require(context['version'] in (2, 3) and set(context) == fields | {'protocol'} |
            ({'inputMode'} if context['version'] == 3 else set())
            and context['protocol'] == 'p7-tool-submit-v1')
    if context['version'] == 3:
        require(context['inputMode'] == 'checked-draft-v1')
    return context['protocol']


def review_input_mode(context):
    review_protocol(context)
    return context['inputMode'] if context['version'] == 3 else 'literal-text'


def record_review(root, review_file, *, reviewer_kind, reviewer_id):
    """Caller identity is the local OS user; reviewer labels are declarations.

    This is not an HTTP endpoint, model tool, signature service, or login system.
    Same-user privileged processes are within the trusted operator boundary.
    """
    root = private_path(root, directory=True)
    require(re.fullmatch(r'p2-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', root.name))
    require(reviewer_kind in ('human', 'codex') and type(reviewer_id) is str
            and 0 < len(reviewer_id.strip().encode()) <= 256)
    raw_review = read_private(review_file, 128*1024)
    digest = hashlib.sha256(raw_review).hexdigest()
    parent = root / 'handoff-reviews'
    try: parent.mkdir(mode=0o700)
    except FileExistsError: private_path(parent, directory=True)
    attempt = parent / digest
    attempt.mkdir(mode=0o700)  # Unknown prior outcome must be inspected, never replayed.
    save_exclusive(attempt / 'review.json', raw_review)
    authority = dict(transport='local-os-user', uid=os.getuid(), reviewerKind=reviewer_kind,
                     reviewerId=reviewer_id, authenticatedReviewerLabel=False)
    save_exclusive(attempt / 'intent.json', canonical(dict(version=1, runId=root.name,
        reviewFileSha256=digest, recordedAt=datetime.now(timezone.utc).isoformat(), authority=authority)))
    try:
        raw_context = read_private(root / 'handoff-review-context.json', 384*1024)
        raw_execution = read_private(root / 'handoff-execution-verification.json', 1024*1024)
        context, previous, review = (strict_json(raw.decode()) for raw in (raw_context, raw_execution, raw_review))
        protocol = review_protocol(context)
        submission = HandoffSubmission.model_validate(context['submission'])
        current = verify_handoff_execution(root, guest_directory=root / 'guest' / root.name,
            home=context['home'], submission=submission, session_id=context['sessionId'], binding=context['binding'],
            protocol=protocol, draft_input_mode=review_input_mode(context))
        require(canonical(current) == canonical(previous))
        require(review['reviewer'] == dict(kind=reviewer_kind, id=reviewer_id))
        result = validate_independent_review(review, submission=submission, report=current['result'],
            execution=current, case_name=review['binding']['caseName'])
        require(read_private(root / 'handoff-review-context.json', 384*1024) == raw_context
                and read_private(root / 'handoff-execution-verification.json', 1024*1024) == raw_execution
                and read_private(review_file, 128*1024) == raw_review)
        receipt = dict(version=1, runId=root.name, result=result, authority=authority,
                       reviewFileSha256=digest, published=False, databaseChanged=False)
    except Exception:
        receipt = dict(version=1, runId=root.name, result=dict(status='REVIEW_RECORD_REJECTED'),
                       authority=authority, reviewFileSha256=digest, published=False, databaseChanged=False)
    save_exclusive(attempt / 'receipt.json', canonical(receipt))
    return dict(status=receipt['result']['status'], receipt=str(attempt / 'receipt.json'), published=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--reviewer-kind', choices=['human', 'codex'], required=True)
    parser.add_argument('--reviewer-id', required=True)
    args = parser.parse_args()
    try:
        result = record_review(args.root, args.review, reviewer_kind=args.reviewer_kind, reviewer_id=args.reviewer_id)
        print(json.dumps(result))
        return 0 if result['status'] == 'REVIEW_ACCEPTED' else 1
    except Exception:
        print(json.dumps(dict(status='REVIEW_RECORD_UNCONFIRMED', published=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
