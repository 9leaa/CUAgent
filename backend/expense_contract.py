"""Expense input metadata and exact money parsing; no file or execution access."""
import csv
from decimal import Decimal, localcontext
import hashlib
import io
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

from .handoff_contract import calendar_date, identifier, text


def amount_cents(value: str) -> int:
    if type(value) is not str or not re.fullmatch(r'(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,2})?', value):
        raise ValueError('bounded decimal string required')
    with localcontext() as context:
        context.prec = 16
        cents = int(Decimal(value) * 100)
    if not 1 <= cents <= 99999999:
        raise ValueError('positive CNY amount required')
    return cents


class ExpenseModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, revalidate_instances='always')


class ExpenseTransaction(ExpenseModel):
    transaction_id: StrictStr
    date: StrictStr
    merchant: StrictStr
    amount: StrictStr
    currency: Literal['CNY']

    _id = field_validator('transaction_id')(identifier)
    _date = field_validator('date')(calendar_date)

    @field_validator('merchant')
    @classmethod
    def merchant_text(cls, value):
        return text(value, 256)

    @field_validator('amount')
    @classmethod
    def money(cls, value):
        amount_cents(value)
        return value


class ExpenseReceipt(ExpenseModel):
    id: StrictStr
    sha256: StrictStr
    sizeBytes: StrictInt = Field(ge=1, le=8 * 1024 * 1024)
    mediaType: Literal['application/pdf', 'image/png', 'image/jpeg']
    pageCount: StrictInt = Field(ge=1, le=20)

    _id = field_validator('id')(identifier)

    @field_validator('sha256')
    @classmethod
    def digest(cls, value):
        if not re.fullmatch(r'[0-9a-f]{64}', value):
            raise ValueError('lowercase SHA256 required')
        return value

    @model_validator(mode='after')
    def image_pages(self):
        if self.mediaType != 'application/pdf' and self.pageCount != 1:
            raise ValueError('image requires one page')
        return self


def _transactions(value):
    columns = ['transaction_id', 'date', 'merchant', 'amount', 'currency']
    try:
        rows = list(csv.reader(io.StringIO(value, newline=''), strict=True))
    except csv.Error:
        raise ValueError('invalid CSV') from None
    if not rows or rows[0] != columns or not 2 <= len(rows) <= 21:
        raise ValueError('fixed header and 1-20 transactions required')
    if any(len(row) != 5 for row in rows[1:]):
        raise ValueError('invalid row width')
    items = tuple(ExpenseTransaction.model_validate(dict(zip(columns, row))) for row in rows[1:])
    if len({item.transaction_id for item in items}) != len(items):
        raise ValueError('duplicate transaction ID')
    return items


class ExpenseSubmission(ExpenseModel):
    kind: Literal['expense-reconcile']
    asOf: StrictStr
    transactionsCsv: StrictStr
    receipts: tuple[ExpenseReceipt, ...] = Field(min_length=1, max_length=20)

    _date = field_validator('asOf')(calendar_date)

    @field_validator('transactionsCsv')
    @classmethod
    def csv_text(cls, value):
        return text(value, 16 * 1024, multiline=True)

    @model_validator(mode='after')
    def contents(self):
        _transactions(self.transactionsCsv)
        if len({item.id for item in self.receipts}) != len(self.receipts):
            raise ValueError('duplicate receipt ID')
        if sum(item.sizeBytes for item in self.receipts) > 32 * 1024 * 1024:
            raise ValueError('receipt byte budget exceeded')
        return self

    def transactions(self):
        checked = type(self).model_validate(self)
        return _transactions(checked.transactionsCsv)

    def total_cents(self):
        return sum(amount_cents(item.amount) for item in self.transactions())

    def input_sha256(self):
        checked = type(self).model_validate(self)
        payload = json.dumps(checked.model_dump(mode='json'), sort_keys=True,
                             ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(payload).hexdigest()

    def duplicate_receipt_sources(self):
        checked = type(self).model_validate(self)
        groups = {}
        for item in checked.receipts:
            groups.setdefault(item.sha256, []).append(item.id)
        return tuple(tuple(ids) for ids in groups.values() if len(ids) > 1)
