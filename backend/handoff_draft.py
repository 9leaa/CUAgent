"""Pure draft helpers, NOT registered tools or execution/publication authority.

Callers must bind frozen sources/identity. Future model exposure requires the
normal raw-call budget, lease, stop, audit and independent exchange verification.
"""
import hashlib
import json
from pydantic import ValidationError
from backend.handoff_contract import HandoffSubmission, text
from backend.handoff_document import expected_document
from backend.handoff_result import HandoffResult, canonical, verify_result
from backend.handoff_session import strict_json


def locate_quote(submission, *, source_id, quote):
    """Exact codepoint matches only; never choose among ambiguous occurrences."""
    source = HandoffSubmission.model_validate(submission)
    if type(source_id) is not str or type(quote) is not str:
        raise ValueError('exact source identifier and quote required')
    text(quote, 2048, multiline=True)
    sources = {f'notes/{n.id}': n.content for n in source.notes}
    sources.update(tasksCsv=source.tasksCsv, previousReport=source.previousReport)
    if source_id not in sources:
        return dict(status='SOURCE_NOT_FOUND', matches=[], truncated=False)
    original = sources[source_id]
    matches, start = [], 0
    while True:
        at = original.find(quote, start)
        if at < 0:
            break
        if len(matches) == 8:
            return dict(status='AMBIGUOUS', matches=matches, truncated=True)
        matches.append(dict(start=at, end=at + len(quote)))
        start = at + 1  # Preserve overlapping matches too.
    return dict(status='UNIQUE' if len(matches) == 1 else 'AMBIGUOUS' if matches else 'NOT_FOUND',
                sourceId=source_id, sourceSha256=source.source_hashes()[source_id],
                matches=matches, truncated=False)


def check_draft(submission, raw, *, run_id, session_id):
    """Reject malformed/incorrect drafts; never repair, normalize or write them."""
    source = HandoffSubmission.model_validate(submission)
    def rejected(code, **detail):
        return dict(status='DRAFT_REJECTED', code=code, semanticVerified=False,
                    guiVerified=False, **detail)
    if type(raw) is not str:
        return rejected('JSON_TEXT_REQUIRED')
    try:
        encoded = raw.encode('utf-8')
    except UnicodeError:
        return rejected('INVALID_UNICODE')
    if not 0 < len(encoded) <= 64 * 1024:
        return rejected('DRAFT_SIZE_LIMIT')
    try:
        value = strict_json(raw)
    except json.JSONDecodeError as error:
        return rejected('JSON_SYNTAX', line=error.lineno, column=error.colno)
    except (ValueError, RecursionError):
        return rejected('JSON_NOT_STRICT')
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 32:
            return rejected('JSON_NOT_STRICT')
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
    try:
        report = HandoffResult.model_validate(value)
    except ValidationError as error:
        # No input values, quoted material, URLs or exception strings in errors.
        return rejected('SCHEMA', fields=[[part if type(part) is int else str(part)[:64]
                                          for part in e['loc'][:12]] for e in error.errors(
            include_url=False, include_context=False, include_input=False)[:8]])
    try:
        structure = verify_result(source, report, run_id=run_id, session_id=session_id)
    except ValueError:
        return rejected('SOURCE_OR_FACT_BINDING')
    try:
        document = expected_document(source, report, run_id=run_id, session_id=session_id)
    except ValueError:
        return rejected('DOCUMENT_PROJECTION_LIMIT')
    return dict(status='DRAFT_STRUCTURE_VALID', semanticVerified=False, guiVerified=False,
                rawSha256=hashlib.sha256(encoded).hexdigest(), structure=structure,
                report=report.model_dump(mode='json'), canonicalJson=canonical(report.model_dump(mode='json')).decode(),
                document=document.decode(), documentSha256=hashlib.sha256(document).hexdigest())
