"""Structural/source verification only: neither semantic nor GUI acceptance."""
import hashlib
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator
from backend.handoff_contract import HandoffSubmission, HandoffTask, text


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def input_digest(submission: HandoffSubmission):
    return hashlib.sha256(canonical(submission.model_dump(mode='json'))).hexdigest()


class Frozen(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, revalidate_instances='always')


class Citation(Frozen):
    sourceId: StrictStr = Field(min_length=1, max_length=80)
    sourceSha256: StrictStr = Field(pattern=r'^[0-9a-f]{64}$')
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(gt=0)
    quote: StrictStr

    @field_validator('quote')
    @classmethod
    def quoted_text(cls, value):
        return text(value, 2048, multiline=True)


class Statement(Frozen):
    text: StrictStr
    citations: tuple[Citation, ...] = Field(min_length=1, max_length=8)

    @field_validator('text')
    @classmethod
    def prose(cls, value):
        return text(value, 2048, multiline=True)


class TaskReport(HandoffTask):
    overdue: StrictBool
    progress: Statement
    handoff: Statement  # Always a recommendation, not a new owner assignment.


class Issue(Statement):
    category: Literal['conflict', 'unknown_owner', 'overdue', 'needs_confirmation']
    taskIds: tuple[StrictStr, ...] = Field(min_length=1, max_length=20)


class Counts(Frozen):
    todo: StrictInt = Field(ge=0, le=20)
    doing: StrictInt = Field(ge=0, le=20)
    done: StrictInt = Field(ge=0, le=20)
    blocked: StrictInt = Field(ge=0, le=20)


class HandoffResult(Frozen):
    kind: Literal['project-handoff']
    runId: StrictStr
    sessionId: StrictStr
    inputSha256: StrictStr = Field(pattern=r'^[0-9a-f]{64}$')
    counts: Counts
    tasks: tuple[TaskReport, ...] = Field(min_length=1, max_length=20)
    issues: tuple[Issue, ...] = Field(max_length=60)


def verify_result(submission: HandoffSubmission, result: HandoffResult, *, run_id, session_id):
    """Trusted caller supplies original identity. Does not infer claim entailment."""
    import re
    uuid = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    if not (isinstance(run_id, str) and re.fullmatch('p2-' + uuid, run_id)
            and isinstance(session_id, str) and re.fullmatch('session-' + uuid, session_id)):
        raise ValueError('trusted original run/session required')
    # Revalidate even model_construct/model_copy instances at the trust boundary.
    # Validate raw instance fields first: serialization can coerce malformed values.
    submission = HandoffSubmission.model_validate(submission)
    result = HandoffResult.model_validate(result)
    if (result.runId, result.sessionId, result.inputSha256) != (run_id, session_id, input_digest(submission)):
        raise ValueError('report binding changed')
    serialized = canonical(result.model_dump(mode='json'))
    if len(serialized) > 64 * 1024:
        raise ValueError('report exceeds 64 KiB')
    originals = {task.task_id: task for task in submission.tasks()}
    if len({task.task_id for task in result.tasks}) != len(result.tasks) or {t.task_id for t in result.tasks} != set(originals):
        raise ValueError('tasks missing, duplicated or invented')
    sources = {f'notes/{note.id}': note.content for note in submission.notes}
    sources.update(tasksCsv=submission.tasksCsv, previousReport=submission.previousReport)
    hashes = submission.source_hashes()

    def citations(statement):
        seen = set()
        for cite in statement.citations:
            key = (cite.sourceId, cite.start, cite.end)
            if key in seen or cite.sourceId not in sources or cite.sourceSha256 != hashes[cite.sourceId]:
                raise ValueError('duplicate or unbound citation')
            seen.add(key)
            source = sources[cite.sourceId]
            if not 0 <= cite.start < cite.end <= len(source) or source[cite.start:cite.end] != cite.quote:
                raise ValueError('citation does not match original text')
        return seen

    counts = dict.fromkeys(('todo', 'doing', 'done', 'blocked'), 0)
    overdue_ids, unknown_ids = set(), set()
    for task in result.tasks:
        original = originals[task.task_id]
        for field in ('title', 'owner', 'status', 'due_date'):
            if getattr(task, field) != getattr(original, field):
                raise ValueError('original task facts changed')
        overdue = original.status != 'done' and original.due_date < submission.asOf
        if task.overdue is not overdue:
            raise ValueError('incorrect overdue flag')
        counts[original.status] += 1
        if overdue: overdue_ids.add(task.task_id)
        if original.owner == '': unknown_ids.add(task.task_id)
        citations(task.progress)
        citations(task.handoff)
    if result.counts.model_dump() != counts:
        raise ValueError('incorrect task counts')
    categories = {'unknown_owner': set(), 'overdue': set()}
    issue_keys = set()
    for issue in result.issues:
        ids = set(issue.taskIds)
        if len(ids) != len(issue.taskIds) or not ids <= set(originals):
            raise ValueError('invalid issue task references')
        key = (issue.category, tuple(sorted(ids)), issue.text)
        if key in issue_keys:
            raise ValueError('duplicate issue')
        issue_keys.add(key)
        refs = citations(issue)
        if issue.category == 'conflict' and len(refs) < 2:
            raise ValueError('conflict needs distinct source excerpts')
        if issue.category in categories:
            categories[issue.category].update(ids)
    if categories['unknown_owner'] != unknown_ids or categories['overdue'] != overdue_ids:
        raise ValueError('missing or incorrect deterministic issues')
    return {'status': 'STRUCTURE_VERIFIED_SEMANTICS_PENDING', 'runId': run_id, 'sessionId': session_id,
            'inputSha256': result.inputSha256, 'resultSha256': hashlib.sha256(serialized).hexdigest(),
            'semanticVerified': False, 'guiVerified': False, 'counts': counts}
