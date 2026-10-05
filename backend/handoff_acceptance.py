"""Frozen operator-side acceptance materials, never sent to the tested model.

Checks fixture consistency, not the semantic truth of a generated report.
"""
import hashlib
from pathlib import Path
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import canonical, input_digest
from backend.handoff_session import strict_json, require

DIRECTORY = Path(__file__).resolve().parent / 'fixtures/handoff-v1'
CASES = ('normal', 'conflict', 'dependencies')


def inspect_acceptance_case(value):
    require(type(value) is dict and set(value) == {'input', 'rubric'})
    submission = HandoffSubmission.model_validate(value['input'])
    rubric = value['rubric']
    require(type(rubric) is dict and set(rubric) == {'counts', 'overdue', 'unknownOwners', 'conflictTasks', 'requirements'})
    tasks = submission.tasks(); identities = {t.task_id for t in tasks}
    counts = {s: sum(t.status == s for t in tasks) for s in ('todo', 'doing', 'done', 'blocked')}
    require(canonical(rubric['counts']) == canonical(counts))
    for name in ('overdue', 'unknownOwners', 'conflictTasks'):
        ids = rubric[name]
        require(type(ids) is list and all(type(i) is str and i in identities for i in ids) and len(set(ids)) == len(ids))
    require(set(rubric['overdue']) == {t.task_id for t in tasks if t.status != 'done' and t.due_date < submission.asOf})
    require(set(rubric['unknownOwners']) == {t.task_id for t in tasks if not t.owner})
    sources = {f'notes/{n.id}': n.content for n in submission.notes}
    sources.update(tasksCsv=submission.tasksCsv, previousReport=submission.previousReport)
    requirements = rubric['requirements']
    require(type(requirements) is list and 1 <= len(requirements) <= 60)
    seen, covered, conflicts, references = set(), set(), set(), []
    for row in requirements:
        require(type(row) is dict and set(row) == {'id', 'taskIds', 'mustExpress', 'mustNotExpress', 'evidence'})
        for field in ('id', 'mustExpress', 'mustNotExpress'):
            require(type(row[field]) is str and 0 < len(row[field].encode()) <= 4096)
        require(row['id'] not in seen); seen.add(row['id'])
        ids = row['taskIds']
        require(type(ids) is list and ids and all(type(i) is str and i in identities for i in ids) and len(set(ids)) == len(ids))
        covered.update(ids)
        evidence = row['evidence']; require(type(evidence) is list and 1 <= len(evidence) <= 8)
        names = set()
        for ref in evidence:
            require(type(ref) is dict and set(ref) == {'sourceId', 'quote'})
            name, quote = ref['sourceId'], ref['quote']
            require(type(name) is str and name in sources and type(quote) is str and quote
                    and len(quote.encode()) <= 2048 and sources[name].count(quote) == 1)
            start = sources[name].index(quote); names.add(name)
            references.append(dict(requirementId=row['id'], sourceId=name, start=start, end=start+len(quote),
                                   sourceSha256=submission.source_hashes()[name]))
        if len(names) >= 2: conflicts.update(ids)
    require(covered == identities and set(rubric['conflictTasks']) <= conflicts)
    return dict(status='ACCEPTANCE_FIXTURE_CONSISTENT', inputSha256=input_digest(submission),
                rubricSha256=hashlib.sha256(canonical(rubric)).hexdigest(), requirements=len(requirements),
                references=references, semanticVerified=False, realExecutionVerified=False)


def load_acceptance_case(name):
    require(name in CASES)
    manifest = strict_json((DIRECTORY / 'manifest.json').read_text())
    require(set(manifest) == {'version', 'cases'} and type(manifest['version']) is int and manifest['version'] == 1
            and set(manifest['cases']) == set(CASES))
    raw = (DIRECTORY / (name + '.json')).read_bytes()
    require(len(raw) <= 128*1024)
    value = strict_json(raw.decode())
    checked = inspect_acceptance_case(value)
    require(manifest['cases'][name] == dict(inputSha256=checked['inputSha256'], rubricSha256=checked['rubricSha256'],
                                          fileSha256=hashlib.sha256(raw).hexdigest()))
    return value, checked
