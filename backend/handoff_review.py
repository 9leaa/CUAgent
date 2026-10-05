"""Validate operator-provided independent review attestations, not entailment.

The trusted caller authenticates the reviewer and re-verifies original execution.
A self-consistent JSON supplied by the tested model is never authority to publish.
"""
from datetime import datetime, timezone
import hashlib
import re
from backend.handoff_acceptance import load_acceptance_case
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import HandoffResult, canonical, input_digest, verify_result
from backend.handoff_document import expected_document
from backend.handoff_session import require

GLOBAL = ('no_unsupported_claims', 'suggestions_not_facts', 'gui_readability')


def review_subject(submission, report, execution, case_name):
    submission = HandoffSubmission.model_validate(submission)
    report = HandoffResult.model_validate(report)
    case, checked = load_acceptance_case(case_name)
    require(input_digest(submission) == checked['inputSha256'])
    structure = verify_result(submission, report, run_id=execution['runId'], session_id=execution['sessionId'])
    require(execution['status'] == 'EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING'
            and execution['sessionVerified'] is True and execution['guiEvidenceVerified'] is True
            and execution['imageBytesVerified'] is True and execution['semanticVerified'] is False
            and canonical(execution['result']) == canonical(report.model_dump(mode='json')))
    require(type(execution['sessionSha256']) is str and re.fullmatch('[0-9a-f]{64}', execution['sessionSha256']))
    document = expected_document(submission, report, run_id=report.runId, session_id=report.sessionId)
    require(execution['documentSha256'] == hashlib.sha256(document).hexdigest())
    fields = {f'task/{task.task_id}/{field}': getattr(task, field).text
              for task in report.tasks for field in ('progress', 'handoff')}
    fields.update({f'issue/{i}': issue.text for i, issue in enumerate(report.issues)})
    allowed = {name: {name} for name in fields}
    for row in case['rubric']['requirements']:
        targets = {f'task/{task}/{field}' for task in row['taskIds'] for field in ('progress', 'handoff')}
        targets.update(f'issue/{i}' for i, issue in enumerate(report.issues) if set(issue.taskIds) & set(row['taskIds']))
        allowed['requirement/' + row['id']] = targets
    allowed.update({'global/' + name: set(fields) for name in GLOBAL})
    snapshots = [image['snapshotId'] for image in execution['images']['images']]
    require(snapshots and all(type(s) is str and s for s in snapshots) and len(set(snapshots)) == len(snapshots))
    binding = dict(caseName=case_name, runId=report.runId, sessionId=report.sessionId,
        inputSha256=structure['inputSha256'], reportSha256=structure['resultSha256'],
        sessionSha256=execution['sessionSha256'], documentSha256=execution['documentSha256'],
        rubricSha256=checked['rubricSha256'], executionSha256=hashlib.sha256(canonical(execution)).hexdigest())
    conflict_ids = {task for issue in report.issues if issue.category == 'conflict' for task in issue.taskIds}
    return binding, fields, allowed, snapshots, conflict_ids == set(case['rubric']['conflictTasks'])


def validate_independent_review(review, *, submission, report, execution, case_name, now=None):
    binding, fields, allowed, snapshots, conflict_coverage = review_subject(submission, report, execution, case_name)
    require(type(review) is dict and len(canonical(review)) <= 128*1024
            and set(review) == {'version', 'binding', 'reviewer', 'reviewedAt', 'imagesReviewed', 'checks'})
    require(type(review['version']) is int and review['version'] == 1 and canonical(review['binding']) == canonical(binding))
    reviewer = review['reviewer']
    require(type(reviewer) is dict and set(reviewer) == {'kind', 'id'} and reviewer['kind'] in ('human', 'codex')
            and type(reviewer['id']) is str and 0 < len(reviewer['id'].strip().encode()) <= 256)
    require(type(review['reviewedAt']) is str)
    at = datetime.fromisoformat(review['reviewedAt']); now = now or datetime.now(timezone.utc)
    require(at.tzinfo is not None and now.tzinfo is not None and at <= now)
    require(review['imagesReviewed'] == snapshots)
    checks = review['checks']
    require(type(checks) is list and len(checks) == len(allowed))
    decisions = {}
    for row in checks:
        require(type(row) is dict and set(row) == {'id', 'decision', 'reason', 'reportQuotes'})
        name = row['id']; require(type(name) is str and name in allowed and name not in decisions)
        require(row['decision'] in ('PASS', 'FAIL', 'UNVERIFIED') and type(row['reason']) is str
                and 0 < len(row['reason'].strip().encode()) <= 4096)
        quotes = row['reportQuotes']; require(type(quotes) is list and len(quotes) <= 8)
        require(row['decision'] != 'PASS' or name.startswith('global/') or bool(quotes))
        seen = set()
        for ref in quotes:
            require(type(ref) is dict and set(ref) == {'path', 'start', 'end', 'quote'})
            path = ref['path']; require(type(path) is str and path in allowed[name])
            start, end, quote = ref['start'], ref['end'], ref['quote']
            require(type(start) is int and type(end) is int and 0 <= start < end <= len(fields[path])
                    and type(quote) is str and len(quote.encode()) <= 2048 and fields[path][start:end] == quote)
            key = (path, start, end); require(key not in seen); seen.add(key)
        decisions[name] = row['decision']
    require(set(decisions) == set(allowed))
    passed = conflict_coverage and all(d == 'PASS' for d in decisions.values())
    return dict(status='REVIEW_ACCEPTED' if passed else 'REVIEW_NOT_PASSED', reviewAccepted=passed,
        binding=binding, reviewSha256=hashlib.sha256(canonical(review)).hexdigest(), reviewer=dict(reviewer),
        decisions=decisions, conflictCoverage=conflict_coverage, automaticSemanticProof=False,
        basis='external independent review attestation', userAdoption='NOT_ASSESSED')
