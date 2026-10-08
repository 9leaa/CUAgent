"""Pure P7 submission candidate check; no tool, execution or publication authority."""
import hashlib
import json

from handoff_draft import check


def candidate(source, args, *, run_id, session_id, draft):
    """Validate the model's complete object against trusted source/last draft.

    Lifecycle, original read-back, lease, raw budget and durable terminal commit
    belong to the caller. A valid candidate alone is never a submitted result.
    """
    def reject(code):
        return dict(status='SUBMISSION_REJECTED', code=code,
                    semanticVerified=False, guiVerified=False)

    if type(args) is not dict or set(args) != {'report'} or type(args['report']) is not dict:
        return reject('REPORT_OBJECT_REQUIRED')
    # Bound work before serializing an untrusted recursive Python/JSON value.
    pending = [(args['report'], 0)]
    nodes = 0
    while pending:
        value, depth = pending.pop()
        nodes += 1
        if depth > 32 or nodes > 65536:
            return reject('REPORT_LIMIT')
        if type(value) is dict:
            if len(value) > 65536 or any(type(k) is not str for k in value):
                return reject('REPORT_NOT_JSON')
            pending.extend((v, depth + 1) for v in value.values())
        elif type(value) is list:
            if len(value) > 65536:
                return reject('REPORT_LIMIT')
            pending.extend((v, depth + 1) for v in value)
        elif type(value) not in (str, int, float, bool, type(None)):
            return reject('REPORT_NOT_JSON')
    try:
        raw = json.dumps(args['report'], ensure_ascii=False, allow_nan=False,
                         sort_keys=True, separators=(',', ':'))
        if not 0 < len(raw.encode('utf8')) <= 65536:
            return reject('REPORT_LIMIT')
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        return reject('REPORT_NOT_JSON')
    checked = check(source, raw, run_id=run_id, session_id=session_id)
    if checked['status'] != 'DRAFT_STRUCTURE_VALID':
        return reject('REPORT_INVALID')
    if (type(draft) is not dict or draft.get('status') != 'DRAFT_STRUCTURE_VALID'
            or any(checked[key] != draft.get(key)
                   for key in ('canonicalJson', 'document', 'documentSha256'))):
        return reject('DRAFT_MISMATCH')
    return dict(status='SUBMISSION_CANDIDATE_VALID', protocol='p7-tool-submit-v1',
                reportSha256=hashlib.sha256(checked['canonicalJson'].encode()).hexdigest(),
                documentSha256=checked['documentSha256'],
                semanticVerified=False, guiVerified=False)
