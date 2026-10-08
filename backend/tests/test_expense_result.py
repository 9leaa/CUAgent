from copy import deepcopy

import pytest

from backend.expense_contract import ExpenseSubmission
from backend.expense_result import ExpenseResult, ReceiptFacts, verify_expense_result

RUN = 'p2-11111111-1111-1111-1111-111111111111'
SESSION = 'session-22222222-2222-2222-2222-222222222222'


def fixture():
    submission = dict(kind='expense-reconcile', asOf='2026-10-08',
        transactionsCsv='transaction_id,date,merchant,amount,currency\n'
        't1,2026-10-01,A,0.10,CNY\n'
        't2,2026-10-02,B,2.00,CNY\n'
        't3,2026-10-03,C,3.00,CNY\n',
        receipts=[dict(id=f'r{i}', sha256=char * 64, sizeBytes=120,
                       mediaType='image/png', pageCount=1) for i, char in enumerate('abc', 1)])
    facts = dict(receipts=[
        dict(sourceId='r1', sourceSha256='a' * 64, page=1, date='2026-10-01', merchant='A', amount='0.10', number='N1'),
        dict(sourceId='r2', sourceSha256='b' * 64, page=1, date='2026-10-02', merchant='B', amount='1.75', number='N2'),
        dict(sourceId='r3', sourceSha256='c' * 64, page=1, date='2026-10-04', merchant='D', amount='4.00', number=None)])
    report = dict(kind='expense-reconcile', runId=RUN, sessionId=SESSION,
        rows=[dict(transactionId='t1', status='matched', receiptIds=['r1'], differenceCents=0, explanation='同日同商户同额，业务关联待审。'),
              dict(transactionId='t2', status='amount_mismatch', receiptIds=['r2'], differenceCents=25, explanation='交易比票据多0.25。'),
              dict(transactionId='t3', status='missing_receipt', receiptIds=[], differenceCents=None, explanation='无相容票据。')],
        unreferencedReceiptIds=['r3'], duplicateShaGroups=[], duplicateNumberGroups=[],
        totals=dict(totalCents=510, matchedCents=10, unresolvedCents=500,
                    rawKnownReceiptCents=585, unknownReceiptAmounts=0))
    return submission, facts, report


def bind(submission, facts, report):
    report['inputSha256'] = ExpenseSubmission.model_validate(submission).input_sha256()
    report['factsSha256'] = ReceiptFacts.model_validate(facts).sha256()
    return report


def verify(submission, facts, report):
    return verify_expense_result(submission, facts, bind(submission, facts, report), run_id=RUN, session_id=SESSION)


def test_normal_mismatch_missing_and_unused():
    result = verify(*fixture())
    assert result['status'] == 'STRUCTURE_ARITHMETIC_VERIFIED_SEMANTICS_PENDING'
    assert result['totals']['totalCents'] == 510
    assert result['filesVerified'] is result['semanticVerified'] is result['guiVerified'] is False


@pytest.mark.parametrize('field', ['runId', 'sessionId', 'inputSha256', 'factsSha256'])
def test_binding_tamper(field):
    submission, facts, report = fixture()
    bind(submission, facts, report)
    report[field] = 'f' * 64
    with pytest.raises(ValueError):
        verify_expense_result(submission, facts, report, run_id=RUN, session_id=SESSION)


@pytest.mark.parametrize('field,value', [('status', 'matched'), ('differenceCents', -25),
    ('differenceCents', True), ('receiptIds', ['r1']), ('receiptIds', []),
    ('receiptIds', ['r2', 'r2']), ('transactionId', 'invented'), ('permission', 'allow')])
def test_bad_row(field, value):
    submission, facts, report = fixture()
    report['rows'][1][field] = value
    with pytest.raises(ValueError):
        verify(submission, facts, report)


@pytest.mark.parametrize('field', ['totalCents', 'matchedCents', 'unresolvedCents',
                                 'rawKnownReceiptCents', 'unknownReceiptAmounts'])
def test_totals_recomputed(field):
    submission, facts, report = fixture()
    report['totals'][field] += 1
    with pytest.raises(ValueError):
        verify(submission, facts, report)


@pytest.mark.parametrize('target,change', [('rows', 'missing'), ('rows', 'duplicate'),
                                        ('facts', 'missing'), ('facts', 'duplicate')])
def test_complete_coverage(target, change):
    submission, facts, report = fixture()
    items = report['rows'] if target == 'rows' else facts['receipts']
    if change == 'missing':
        items.pop()
    else:
        items.append(deepcopy(items[0]))
    with pytest.raises(ValueError):
        verify(submission, facts, report)


@pytest.mark.parametrize('unused', [[], ['r1', 'r3'], ['r3', 'r3'], ['invented']])
def test_unused_coverage(unused):
    submission, facts, report = fixture()
    report['unreferencedReceiptIds'] = unused
    with pytest.raises(ValueError):
        verify(submission, facts, report)


@pytest.mark.parametrize('field,value', [('sourceSha256', 'f' * 64), ('page', 2),
    ('sourceId', 'invented'), ('amount', 'NaN'), ('amount', 1.75), ('date', '2026-02-30')])
def test_fact_sources_and_types(field, value):
    submission, facts, report = fixture()
    facts['receipts'][1][field] = value
    with pytest.raises(ValueError):
        verify(submission, facts, report)


def test_unclear_amount_not_guessed():
    submission, facts, report = fixture()
    facts['receipts'][1]['amount'] = None
    report['rows'][1].update(status='needs_confirmation', differenceCents=None)
    report['totals'].update(rawKnownReceiptCents=410, unknownReceiptAmounts=1)
    verify(submission, facts, report)
    report['rows'][1].update(status='matched', differenceCents=0)
    with pytest.raises(ValueError):
        verify(submission, facts, report)


def test_unknown_date_and_merchant_prevent_false_missing():
    submission, facts, report = fixture()
    facts['receipts'][2].update(date=None, merchant=None)
    for row, ids in zip(report['rows'], [['r1', 'r3'], ['r2', 'r3'], ['r3']]):
        row.update(status='ambiguous', receiptIds=ids, differenceCents=None)
    report['totals'].update(matchedCents=0, unresolvedCents=510)
    report['unreferencedReceiptIds'] = []
    verify(submission, facts, report)
    report['rows'][2].update(status='missing_receipt', receiptIds=[])
    with pytest.raises(ValueError):
        verify(submission, facts, report)


def test_shared_receipt_cannot_match_two_transactions():
    submission, facts, report = fixture()
    submission['transactionsCsv'] = submission['transactionsCsv'].replace('2026-10-02,B,2.00', '2026-10-01,A,0.10')
    for row in report['rows'][:2]:
        row.update(status='ambiguous', receiptIds=['r1'], differenceCents=None)
    report['totals'].update(totalCents=320, matchedCents=0, unresolvedCents=320)
    report['unreferencedReceiptIds'] = ['r2', 'r3']
    verify(submission, facts, report)
    report['rows'][0].update(status='matched', differenceCents=0)
    with pytest.raises(ValueError):
        verify(submission, facts, report)


@pytest.mark.parametrize('kind', ['number', 'sha'])
def test_duplicate_originals_not_auto_matched(kind):
    submission, facts, report = fixture()
    if kind == 'number':
        facts['receipts'][2]['number'] = 'N1'
        report['duplicateNumberGroups'] = [['r1', 'r3']]
    else:
        submission['receipts'][2]['sha256'] = 'a' * 64
        facts['receipts'][2]['sourceSha256'] = 'a' * 64
        report['duplicateShaGroups'] = [['r1', 'r3']]
    report['rows'][0].update(status='needs_confirmation', differenceCents=None)
    report['totals'].update(matchedCents=0, unresolvedCents=510)
    verify(submission, facts, report)
    report['duplicateNumberGroups' if kind == 'number' else 'duplicateShaGroups'] = []
    with pytest.raises(ValueError):
        verify(submission, facts, report)


def test_multiple_exact_candidates_cannot_choose_one():
    submission, facts, report = fixture()
    facts['receipts'][2].update(date='2026-10-01', merchant='A', amount='0.10')
    report['rows'][0].update(status='ambiguous', receiptIds=['r1', 'r3'], differenceCents=None)
    report['unreferencedReceiptIds'] = []
    report['totals'].update(matchedCents=0, unresolvedCents=510, rawKnownReceiptCents=195)
    verify(submission, facts, report)
    report['rows'][0].update(status='matched', receiptIds=['r1'], differenceCents=0)
    with pytest.raises(ValueError):
        verify(submission, facts, report)


def test_revalidate_bypassed_model_instance():
    submission, facts, report = fixture()
    result = ExpenseResult.model_validate(bind(submission, facts, report))
    result = result.model_copy(update={'totals': result.totals.model_copy(update={'totalCents': True})})
    with pytest.raises(ValueError):
        verify_expense_result(submission, facts, result, run_id=RUN, session_id=SESSION)


def test_changed_facts_not_silently_used():
    submission, facts, report = fixture()
    bind(submission, facts, report)
    facts['receipts'][0]['amount'] = '0.11'
    with pytest.raises(ValueError, match='binding'):
        verify_expense_result(submission, facts, report, run_id=RUN, session_id=SESSION)


def test_negative_difference_not_absolute_value():
    submission, facts, report = fixture()
    facts['receipts'][1]['amount'] = '2.25'
    report['rows'][1]['differenceCents'] = -25
    report['totals']['rawKnownReceiptCents'] = 635
    verify(submission, facts, report)
    report['rows'][1]['differenceCents'] = 25
    with pytest.raises(ValueError):
        verify(submission, facts, report)


def test_different_merchant_does_not_match_same_date_amount():
    submission, facts, report = fixture()
    facts['receipts'][0]['merchant'] = 'other'
    report['rows'][0].update(status='missing_receipt', receiptIds=[], differenceCents=None)
    report['unreferencedReceiptIds'] = ['r1', 'r3']
    report['totals'].update(matchedCents=0, unresolvedCents=510)
    verify(submission, facts, report)


@pytest.mark.parametrize('groups', [[['r1', 'r2']], [['r1', 'r1']], [['r1']], [['invented', 'r1']]])
def test_invented_duplicate_groups(groups):
    submission, facts, report = fixture()
    report['duplicateNumberGroups'] = groups
    with pytest.raises(ValueError):
        verify(submission, facts, report)


def test_explanation_control_characters_rejected():
    submission, facts, report = fixture()
    report['rows'][0]['explanation'] = 'ok\u202e'
    with pytest.raises(ValueError):
        verify(submission, facts, report)


def test_wrong_trusted_identity_rejected():
    submission, facts, report = fixture()
    with pytest.raises(ValueError):
        verify_expense_result(submission, facts, bind(submission, facts, report), run_id='wrong', session_id=SESSION)
