"""Check a report against independently supplied extraction facts, not original images."""
import hashlib
import json
import re
from typing import Literal

from pydantic import Field, StrictInt, StrictStr, field_validator

from .expense_contract import ExpenseModel, ExpenseSubmission, amount_cents
from .handoff_contract import calendar_date, identifier, text


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


class ReceiptFact(ExpenseModel):
    sourceId: StrictStr
    sourceSha256: StrictStr = Field(pattern=r'^[0-9a-f]{64}$')
    page: StrictInt = Field(ge=1, le=20)
    date: StrictStr | None
    merchant: StrictStr | None
    amount: StrictStr | None
    number: StrictStr | None

    _id = field_validator('sourceId')(identifier)

    @field_validator('date')
    @classmethod
    def valid_date(cls, value):
        return calendar_date(value) if value is not None else None

    @field_validator('merchant', 'number')
    @classmethod
    def valid_text(cls, value):
        return text(value, 256) if value is not None else None

    @field_validator('amount')
    @classmethod
    def valid_amount(cls, value):
        if value is not None:
            amount_cents(value)
        return value


class ReceiptFacts(ExpenseModel):
    receipts: tuple[ReceiptFact, ...] = Field(min_length=1, max_length=20)

    def sha256(self):
        checked = ReceiptFacts.model_validate(self)
        return hashlib.sha256(canonical(checked.model_dump(mode='json'))).hexdigest()


class ExpenseRow(ExpenseModel):
    transactionId: StrictStr
    status: Literal['matched', 'missing_receipt', 'amount_mismatch', 'ambiguous', 'needs_confirmation']
    receiptIds: tuple[StrictStr, ...] = Field(max_length=20)
    differenceCents: StrictInt | None
    explanation: StrictStr

    _id = field_validator('transactionId')(identifier)

    @field_validator('explanation')
    @classmethod
    def prose(cls, value):
        return text(value, 2048, multiline=True)


class ExpenseTotals(ExpenseModel):
    totalCents: StrictInt = Field(ge=0)
    matchedCents: StrictInt = Field(ge=0)
    unresolvedCents: StrictInt = Field(ge=0)
    rawKnownReceiptCents: StrictInt = Field(ge=0)
    unknownReceiptAmounts: StrictInt = Field(ge=0, le=20)


class ExpenseResult(ExpenseModel):
    kind: Literal['expense-reconcile']
    runId: StrictStr
    sessionId: StrictStr
    inputSha256: StrictStr = Field(pattern=r'^[0-9a-f]{64}$')
    factsSha256: StrictStr = Field(pattern=r'^[0-9a-f]{64}$')
    rows: tuple[ExpenseRow, ...] = Field(min_length=1, max_length=20)
    unreferencedReceiptIds: tuple[StrictStr, ...] = Field(max_length=20)
    duplicateShaGroups: tuple[tuple[StrictStr, ...], ...] = Field(max_length=20)
    duplicateNumberGroups: tuple[tuple[StrictStr, ...], ...] = Field(max_length=20)
    totals: ExpenseTotals


def _groups(items, key):
    grouped = {}
    for item in items:
        value = key(item)
        if value is not None:
            grouped.setdefault(value, []).append(item.sourceId)
    return {tuple(sorted(ids)) for ids in grouped.values() if len(ids) > 1}


def _check_groups(actual, expected):
    if any(len(group) < 2 or len(set(group)) != len(group) for group in actual):
        raise ValueError('invalid duplicate source group')
    normalized = [tuple(sorted(group)) for group in actual]
    if len(set(normalized)) != len(normalized) or set(normalized) != expected:
        raise ValueError('duplicate source groups incomplete or invented')


def verify_expense_result(submission, facts, result, *, run_id, session_id):
    """Facts/identity come from trusted caller, never from the report being checked."""
    uuid = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    if (type(run_id) is not str or not re.fullmatch('p2-' + uuid, run_id)
            or type(session_id) is not str or not re.fullmatch('session-' + uuid, session_id)):
        raise ValueError('original run/session required')
    submission = ExpenseSubmission.model_validate(submission)
    facts = ReceiptFacts.model_validate(facts)
    result = ExpenseResult.model_validate(result)
    if (result.runId, result.sessionId, result.inputSha256, result.factsSha256) != (
            run_id, session_id, submission.input_sha256(), facts.sha256()):
        raise ValueError('report binding changed')
    if len(canonical(result.model_dump(mode='json'))) > 64 * 1024:
        raise ValueError('report exceeds 64 KiB')
    sources = {receipt.id: receipt for receipt in submission.receipts}
    facts_by_id = {fact.sourceId: fact for fact in facts.receipts}
    if len(facts_by_id) != len(facts.receipts) or set(facts_by_id) != set(sources):
        raise ValueError('facts must cover every original receipt exactly once')
    for fact in facts.receipts:
        source = sources[fact.sourceId]
        if fact.sourceSha256 != source.sha256 or fact.page > source.pageCount:
            raise ValueError('receipt source/page changed')
    sha_groups = _groups(facts.receipts, lambda fact: fact.sourceSha256)
    number_groups = _groups(facts.receipts, lambda fact: fact.number)
    _check_groups(result.duplicateShaGroups, sha_groups)
    _check_groups(result.duplicateNumberGroups, number_groups)
    duplicates = {source for group in sha_groups | number_groups for source in group}

    transactions = submission.transactions()
    rows = {row.transactionId: row for row in result.rows}
    if len(rows) != len(result.rows) or set(rows) != {t.transaction_id for t in transactions}:
        raise ValueError('transaction coverage changed')
    candidates = {}
    for transaction in transactions:
        compatible = [fact for fact in facts.receipts
                      if (fact.date is None or fact.date == transaction.date)
                      and (fact.merchant is None or fact.merchant == transaction.merchant)]
        exact = [fact for fact in compatible if fact.date is not None and fact.merchant is not None
                 and fact.amount is not None and amount_cents(fact.amount) == amount_cents(transaction.amount)]
        unclear = [fact for fact in compatible if None in (fact.date, fact.merchant, fact.amount)]
        # Keep unknown evidence even when an exact candidate exists.
        selected = exact + unclear if exact else compatible
        candidates[transaction.transaction_id] = {fact.sourceId for fact in selected}
    uses = {source: sum(source in ids for ids in candidates.values()) for source in sources}
    referenced = set()
    matched = 0
    for transaction in transactions:
        row = rows[transaction.transaction_id]
        ids = candidates[transaction.transaction_id]
        if len(set(row.receiptIds)) != len(row.receiptIds) or set(row.receiptIds) != ids:
            raise ValueError('receipt candidates incomplete, duplicated or invented')
        referenced.update(ids)
        difference = None
        if not ids:
            status = 'missing_receipt'
        elif len(ids) > 1 or any(uses[source] > 1 for source in ids):
            status = 'ambiguous'
        else:
            source = next(iter(ids))
            fact = facts_by_id[source]
            if source in duplicates or None in (fact.date, fact.merchant, fact.amount):
                status = 'needs_confirmation'
            else:
                difference = amount_cents(transaction.amount) - amount_cents(fact.amount)
                status = 'matched' if difference == 0 else 'amount_mismatch'
        if row.status != status or row.differenceCents != difference:
            raise ValueError('classification or signed difference changed')
        if status == 'matched':
            matched += amount_cents(transaction.amount)
    unused = result.unreferencedReceiptIds
    if len(set(unused)) != len(unused) or set(unused) != set(sources) - referenced:
        raise ValueError('unreferenced receipt coverage changed')
    total = sum(amount_cents(transaction.amount) for transaction in transactions)
    expected = dict(totalCents=total, matchedCents=matched, unresolvedCents=total - matched,
                    rawKnownReceiptCents=sum(amount_cents(fact.amount) for fact in facts.receipts if fact.amount is not None),
                    unknownReceiptAmounts=sum(fact.amount is None for fact in facts.receipts))
    if result.totals.model_dump() != expected:
        raise ValueError('totals changed')
    return dict(status='STRUCTURE_ARITHMETIC_VERIFIED_SEMANTICS_PENDING',
                filesVerified=False, semanticVerified=False, guiVerified=False,
                inputSha256=result.inputSha256, factsSha256=result.factsSha256,
                resultSha256=hashlib.sha256(canonical(result.model_dump(mode='json'))).hexdigest(),
                totals=expected)
