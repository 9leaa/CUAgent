from decimal import localcontext

import pytest

from backend.expense_contract import ExpenseSubmission, amount_cents


def spec():
    return dict(kind='expense-reconcile', asOf='2026-10-08',
                transactionsCsv='transaction_id,date,merchant,amount,currency\n'
                                't1,2026-10-01,商店,0.10,CNY\n'
                                't2,2026-10-02,商店,0.20,CNY\n',
                receipts=[dict(id='r1', sha256='a' * 64, sizeBytes=120,
                               mediaType='image/png', pageCount=1)])


def test_exact_total_and_context_independence():
    with localcontext() as context:
        context.prec = 2
        assert amount_cents('999999.99') == 99999999
        assert ExpenseSubmission.model_validate(spec()).total_cents() == 30


@pytest.mark.parametrize('value', [0.1, 1, True, None, 'NaN', 'Infinity', '1e2',
                                 '01', '0', '0.00', '-1', '+1', '1.001',
                                 '1000000', ' 1', '1 ', '１', '.1', '1.'])
def test_bad_money(value):
    with pytest.raises(ValueError):
        amount_cents(value)


@pytest.mark.parametrize('field,value', [('asOf', '2026-02-30'), ('asOf', '20261008'),
                                      ('kind', 'project-handoff'), ('path', '/etc/passwd')])
def test_bad_top_level(field, value):
    data = spec()
    data[field] = value
    with pytest.raises(ValueError):
        ExpenseSubmission.model_validate(data)


@pytest.mark.parametrize('replacement', [
    't1,2026-10-02,商店,0.20,CNY', 't2,2026-10-02,商店,0.20,USD',
    't2,2026-02-30,商店,0.20,CNY', 't2,2026-10-02,商\x00店,0.20,CNY',
    't2,2026-10-02,商店,0.20,CNY,extra', 't2,2026-10-02,商店,NaN,CNY'])
def test_bad_csv_row(replacement):
    data = spec()
    data['transactionsCsv'] = data['transactionsCsv'].replace('t2,2026-10-02,商店,0.20,CNY', replacement)
    with pytest.raises(ValueError):
        ExpenseSubmission.model_validate(data)


@pytest.mark.parametrize('field,value', [('sizeBytes', True), ('sizeBytes', 0),
    ('sizeBytes', 8388609), ('pageCount', 2), ('sha256', 'A' * 64),
    ('mediaType', 'text/html'), ('id', '../r'), ('url', 'https://example.com')])
def test_bad_receipt(field, value):
    data = spec()
    data['receipts'][0][field] = value
    with pytest.raises(ValueError):
        ExpenseSubmission.model_validate(data)


def test_duplicate_sources_preserved_not_deduplicated():
    data = spec()
    data['receipts'].append(dict(data['receipts'][0], id='r2'))
    parsed = ExpenseSubmission.model_validate(data)
    assert parsed.duplicate_receipt_sources() == (('r1', 'r2'),)
    assert len(parsed.receipts) == 2
    data['receipts'][1]['id'] = 'r1'
    with pytest.raises(ValueError):
        ExpenseSubmission.model_validate(data)


def test_manifest_budget():
    data = spec()
    data['receipts'] = [dict(data['receipts'][0], id=f'r{i}', sizeBytes=8388608) for i in range(5)]
    with pytest.raises(ValueError):
        ExpenseSubmission.model_validate(data)


def test_text_preserved_hash_covers_metadata():
    data = spec()
    data['transactionsCsv'] = data['transactionsCsv'].replace('商店', '=1+1')
    parsed = ExpenseSubmission.model_validate(data)
    assert parsed.transactions()[0].merchant == '=1+1'
    before = parsed.input_sha256()
    data['receipts'][0]['sizeBytes'] += 1
    assert ExpenseSubmission.model_validate(data).input_sha256() != before
    data['asOf'] = '2026-10-09'
    assert ExpenseSubmission.model_validate(data).input_sha256() != before


@pytest.mark.parametrize('method', ['transactions', 'total_cents', 'input_sha256', 'duplicate_receipt_sources'])
def test_unvalidated_copy_rejected(method):
    parsed = ExpenseSubmission.model_validate(spec()).model_copy(update={'asOf': 'bad'})
    with pytest.raises(ValueError):
        getattr(parsed, method)()


def test_nested_unvalidated_copy_rejected():
    parsed = ExpenseSubmission.model_validate(spec())
    receipt = parsed.receipts[0].model_copy(update={'sizeBytes': True})
    with pytest.raises(ValueError):
        parsed.model_copy(update={'receipts': (receipt,)}).input_sha256()


@pytest.mark.parametrize('count', [0, 21])
def test_transaction_count(count):
    data = spec()
    data['transactionsCsv'] = 'transaction_id,date,merchant,amount,currency\n' + ''.join(
        f't{i},2026-10-01,shop,1.00,CNY\n' for i in range(count))
    with pytest.raises(ValueError):
        ExpenseSubmission.model_validate(data)


@pytest.mark.parametrize('count', [0, 21])
def test_receipt_count(count):
    data = spec()
    data['receipts'] = [dict(data['receipts'][0], id=f'r{i}') for i in range(count)]
    with pytest.raises(ValueError):
        ExpenseSubmission.model_validate(data)


def test_oversize_csv_and_merchant():
    for merchant in ['x' * 257, 'x' * 16385]:
        data = spec()
        data['transactionsCsv'] = data['transactionsCsv'].replace('商店', merchant)
        with pytest.raises(ValueError):
            ExpenseSubmission.model_validate(data)


def test_standard_csv_quoted_merchant_and_unchanged_amount():
    data = spec()
    data['transactionsCsv'] = data['transactionsCsv'].replace('商店', '"shop, branch"')
    parsed = ExpenseSubmission.model_validate(data)
    assert parsed.transactions()[0].merchant == 'shop, branch'
    assert parsed.transactions()[0].amount == '0.10'
