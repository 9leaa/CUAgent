"""Synthetic review attestations; tests do not claim actual semantic acceptance."""
import copy
from datetime import datetime, timezone
import hashlib
import pytest
from backend.handoff_acceptance import load_acceptance_case
from backend.handoff_contract import HandoffSubmission
from backend.handoff_document import expected_document
from backend.handoff_result import input_digest
from backend.handoff_review import review_subject, validate_independent_review
from backend.tests.test_handoff_result import RUN, SESSION

NOW = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)


def context():
    case, _ = load_acceptance_case('normal')
    submission = HandoffSubmission.model_validate(case['input'])
    sources = {f'notes/{n.id}': n.content for n in submission.notes}
    def cite(name):
        return dict(sourceId=name, sourceSha256=submission.source_hashes()[name], start=0,
                    end=len(sources[name]), quote=sources[name])
    progress = ['N1通过固定三例字段校验，不能推断全场景覆盖。', 'N2完成分页与100条测试，一万条及取消导出待测。', 'N3尚未开始，等待导出截图。']
    handoff = ['建议林澄交字段说明给周禾。', '建议周禾完成大数据量及取消回归，提供截图给许宁。', '建议许宁依据截图编写手册并包含失败处理说明。']
    tasks = [dict(task.model_dump(), overdue=False,
                  progress=dict(text=progress[i], citations=[cite('notes/meeting'), cite('notes/qa')]),
                  handoff=dict(text=handoff[i], citations=[cite('notes/meeting'), cite('notes/qa')]))
             for i, task in enumerate(submission.tasks())]
    report = dict(kind='project-handoff', runId=RUN, sessionId=SESSION, inputSha256=input_digest(submission),
                  counts=case['rubric']['counts'], tasks=tasks, issues=[])
    return submission, report


def attestation(submission, report):
    document = expected_document(submission, report, run_id=RUN, session_id=SESSION)
    execution = dict(status='EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING', runId=RUN, sessionId=SESSION,
        sessionVerified=True, guiEvidenceVerified=True, imageBytesVerified=True, semanticVerified=False,
        result=copy.deepcopy(report), sessionSha256='a'*64, documentSha256=hashlib.sha256(document).hexdigest(),
        images=dict(images=[dict(snapshotId='synthetic-snapshot', sourceSha256='b'*64)]))
    args = dict(submission=submission, report=report, execution=execution, case_name='normal', now=NOW)
    binding, fields, allowed, snapshots, _ = review_subject(submission, report, execution, 'normal')
    rows = []
    for key, names in allowed.items():
        path = sorted(names)[0]
        quotes = [] if key.startswith('global/') else [dict(path=path, start=0, end=len(fields[path]), quote=fields[path])]
        rows.append(dict(id=key, decision='PASS', reason='合成审阅声明，仅验证记录边界，不代表真实模型验收。', reportQuotes=quotes))
    review = dict(version=1, binding=binding, reviewer=dict(kind='codex', id='synthetic-reviewer'),
                  reviewedAt=NOW.isoformat(), imagesReviewed=snapshots, checks=rows)
    return review, args


def test_complete_attestation_is_not_automatic_semantic_proof():
    review, args = attestation(*context()); original = copy.deepcopy(review)
    result = validate_independent_review(review, **args)
    assert result['status'] == 'REVIEW_ACCEPTED' and result['reviewAccepted'] is True
    assert result['automaticSemanticProof'] is False and result['userAdoption'] == 'NOT_ASSESSED'
    assert review == original


@pytest.mark.parametrize('decision', ['FAIL', 'UNVERIFIED'])
def test_failure_and_uncertainty_preserved(decision):
    review, args = attestation(*context()); review['checks'][0]['decision'] = decision
    review['checks'][0]['reportQuotes'] = []
    result = validate_independent_review(review, **args)
    assert result['status'] == 'REVIEW_NOT_PASSED' and result['reviewAccepted'] is False
    assert decision in result['decisions'].values()


@pytest.mark.parametrize('field', ['caseName', 'runId', 'sessionId', 'inputSha256', 'reportSha256', 'sessionSha256', 'documentSha256', 'rubricSha256', 'executionSha256'])
def test_any_binding_change_refused(field):
    review, args = attestation(*context()); review['binding'][field] = 'changed'
    with pytest.raises(ValueError): validate_independent_review(review, **args)


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'extra', 'blank-reason', 'bool-decision', 'empty-quote', 'wrong-quote', 'bool-index', 'foreign-path', 'duplicate-quote', 'self-review', 'future', 'naive-time', 'missing-image', 'changed-execution'])
def test_incomplete_or_forged_review_refused(fault):
    review, args = attestation(*context()); row = review['checks'][0]
    if fault == 'missing': review['checks'].pop()
    elif fault == 'duplicate': review['checks'][-1] = copy.deepcopy(row)
    elif fault == 'extra': row['approved'] = True
    elif fault == 'blank-reason': row['reason'] = ' '
    elif fault == 'bool-decision': row['decision'] = True
    elif fault == 'empty-quote': row['reportQuotes'] = []
    elif fault == 'wrong-quote': row['reportQuotes'][0]['quote'] = 'different'
    elif fault == 'bool-index': row['reportQuotes'][0]['start'] = False
    elif fault == 'foreign-path': row['reportQuotes'][0]['path'] = 'task/N2/progress'
    elif fault == 'duplicate-quote': row['reportQuotes'] *= 2
    elif fault == 'self-review': review['reviewer']['kind'] = 'deepseek'
    elif fault == 'future': review['reviewedAt'] = '2099-01-01T00:00:00+00:00'
    elif fault == 'naive-time': review['reviewedAt'] = '2026-10-05T00:00:00'
    elif fault == 'missing-image': review['imagesReviewed'] = []
    else: args['execution']['images']['images'][0]['sourceSha256'] = 'c'*64
    with pytest.raises(ValueError): validate_independent_review(review, **args)


def test_declared_conflict_coverage_cannot_be_overridden_by_all_passes():
    submission, report = context()
    report['issues'] = [dict(category='conflict', taskIds=['N1'], text='合成错误冲突声明。',
                            citations=copy.deepcopy(report['tasks'][0]['progress']['citations']))]
    review, args = attestation(submission, report)
    result = validate_independent_review(review, **args)
    assert result['reviewAccepted'] is False and result['conflictCoverage'] is False


def test_changed_report_or_unverified_execution_never_becomes_reviewable():
    review, args = attestation(*context())
    args['report']['tasks'][0]['progress']['text'] = '不同报告'
    with pytest.raises(ValueError): validate_independent_review(review, **args)
    review, args = attestation(*context()); args['execution']['sessionVerified'] = False
    with pytest.raises(ValueError): validate_independent_review(review, **args)
