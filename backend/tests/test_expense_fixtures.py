"""Frozen synthetic inputs and handwritten outcomes, not model/VM acceptance."""
import hashlib
import json
from pathlib import Path

import pytest

from backend.expense_contract import ExpenseSubmission
from backend.expense_result import ReceiptFacts, verify_expense_result

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'backend/fixtures/expense-v1/cases.json'
ASSETS = ROOT / 'output/pdf/expense-v1'
RUN = 'p2-11111111-1111-1111-1111-111111111111'
SESSION = 'session-22222222-2222-2222-2222-222222222222'


@pytest.mark.parametrize('name', ['normal', 'anomalies', 'ambiguity'])
def test_frozen_sources_against_independently_written_expected(name):
    case = json.loads(SOURCE.read_text())[name]
    entries = json.loads((ASSETS / 'manifest.json').read_text())[name]
    assert len(entries) == len(case['receipts'])
    for entry in entries:
        data = (ASSETS / name / (entry['id'] + '.pdf')).read_bytes()
        assert len(data) == entry['sizeBytes']
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        assert data.startswith(b'%PDF-')  # Format prefix alone is not PDF validation.
    submission = ExpenseSubmission.model_validate(dict(kind='expense-reconcile', asOf='2026-10-08',
        transactionsCsv=case['transactionsCsv'], receipts=entries))
    by_id = {entry['id']: entry for entry in entries}
    facts = ReceiptFacts.model_validate(dict(receipts=[dict(sourceId=receipt['id'],
        sourceSha256=by_id[receipt['id']]['sha256'], page=1,
        **{field: receipt[field] for field in ('date', 'merchant', 'amount', 'number')})
        for receipt in case['receipts']]))
    report = dict(case['expected'], kind='expense-reconcile', runId=RUN, sessionId=SESSION,
                  inputSha256=submission.input_sha256(), factsSha256=facts.sha256())
    outcome = verify_expense_result(submission, facts, report, run_id=RUN, session_id=SESSION)
    assert not outcome['filesVerified']
    assert not outcome['semanticVerified']
    assert not outcome['guiVerified']
    assert outcome['totals'] == case['expected']['totals']


def test_real_duplicate_bytes_and_distinct_ambiguous_receipts():
    assert (ASSETS / 'anomalies/r2.pdf').read_bytes() == (ASSETS / 'anomalies/r3.pdf').read_bytes()
    assert (ASSETS / 'ambiguity/r1.pdf').read_bytes() != (ASSETS / 'ambiguity/r2.pdf').read_bytes()


def test_generator_cannot_generate_expected_answers():
    source = (SOURCE.parent / 'generate.py').read_text()
    assert 'verify_expense_result' not in source
    assert "['expected']" not in source
