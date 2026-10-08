import hashlib
import json
import os
from pathlib import Path

import pytest

from backend.expense_contract import ExpenseSubmission
from backend.expense_sources import collect_expense_sources
import backend.expense_sources as sources


@pytest.fixture
def sample(tmp_path):
    root = tmp_path / 'private'
    root.mkdir(mode=0o700)
    raw = b'opaque source bytes; format intentionally not decoded'
    file = root / 'r1.pdf'
    file.write_bytes(raw)
    file.chmod(0o600)
    submission = dict(kind='expense-reconcile', asOf='2026-10-08',
        transactionsCsv='transaction_id,date,merchant,amount,currency\nt1,2026-10-01,Shop,1.00,CNY\n',
        receipts=[dict(id='r1', sha256=hashlib.sha256(raw).hexdigest(), sizeBytes=len(raw),
                       mediaType='application/pdf', pageCount=1)])
    return root, submission, raw


def test_exact_bytes_without_claiming_decoding(sample):
    root, submission, raw = sample
    result = collect_expense_sources(root, submission)
    assert result['files'] == {'r1': raw}
    assert result['status'] == 'SOURCE_BYTES_VERIFIED'
    assert result['decodedFormatVerified'] is result['extractionVerified'] is result['guiVerified'] is False


@pytest.mark.parametrize('change', ['hash', 'size', 'missing', 'public_file', 'public_root',
                                  'symlink', 'hardlink', 'fifo', 'directory'])
def test_unsafe_or_changed_sources(sample, tmp_path, change):
    root, submission, raw = sample
    file = root / 'r1.pdf'
    if change == 'hash':
        file.write_bytes(b'x' * len(raw))
    elif change == 'size':
        file.write_bytes(raw + b'x')
    elif change == 'missing':
        file.unlink()
    elif change == 'public_file':
        file.chmod(0o644)
    elif change == 'public_root':
        root.chmod(0o755)
    elif change == 'hardlink':
        os.link(file, tmp_path / 'linked')
    else:
        file.unlink()
        if change == 'symlink':
            target = tmp_path / 'target'
            target.write_bytes(raw)
            file.symlink_to(target)
        elif change == 'fifo':
            os.mkfifo(file, 0o600)
        elif change == 'directory':
            file.mkdir(mode=0o700)
    with pytest.raises(ValueError):
        collect_expense_sources(root, submission)


def test_symlink_root_and_relative_root(sample, tmp_path):
    root, submission, _ = sample
    linked = tmp_path / 'alias'
    linked.symlink_to(root, target_is_directory=True)
    for path in (linked, Path('relative')):
        with pytest.raises(ValueError):
            collect_expense_sources(path, submission)


def test_unlisted_files_never_opened(sample, monkeypatch):
    root, submission, _ = sample
    real_open = os.open
    opened = []
    def observed(path, *args, **kwargs):
        opened.append(str(path))
        return real_open(path, *args, **kwargs)
    monkeypatch.setattr(os, 'open', observed)
    (root / 'expected-answer.json').write_text('not for the model')
    collect_expense_sources(root, submission)
    assert opened == [str(root), 'r1.pdf', 'r1.pdf']


def test_same_bytes_replaced_inode_rejected(sample, monkeypatch):
    root, submission, raw = sample
    original = sources._read_source
    calls = 0
    def replace_after_first(fd, receipt):
        nonlocal calls
        output = original(fd, receipt)
        calls += 1
        if calls == 1:
            replacement = root / 'replacement'
            replacement.write_bytes(raw)
            replacement.chmod(0o600)
            replacement.replace(root / 'r1.pdf')
        return output
    monkeypatch.setattr(sources, '_read_source', replace_after_first)
    with pytest.raises(ValueError):
        collect_expense_sources(root, submission)


def test_root_replacement_rejected(sample, monkeypatch):
    root, submission, _ = sample
    original = sources._read_source
    changed = False
    def replace_root(fd, receipt):
        nonlocal changed
        output = original(fd, receipt)
        if not changed:
            changed = True
            root.rename(root.with_name('old-private'))
            root.mkdir(mode=0o700)
        return output
    monkeypatch.setattr(sources, '_read_source', replace_root)
    with pytest.raises(ValueError):
        collect_expense_sources(root, submission)


def test_manifest_bypass_rejected(sample):
    root, submission, _ = sample
    parsed = ExpenseSubmission.model_validate(submission)
    receipt = parsed.receipts[0].model_copy(update={'id': '../outside'})
    with pytest.raises(ValueError):
        collect_expense_sources(root, parsed.model_copy(update={'receipts': (receipt,)}))


def test_foreign_owner_rejected(sample, monkeypatch):
    root, submission, _ = sample
    current = os.getuid()
    monkeypatch.setattr(os, 'getuid', lambda: current + 1)
    with pytest.raises(ValueError):
        collect_expense_sources(root, submission)


def test_changed_bytes_between_passes_rejected(sample, monkeypatch):
    root, submission, raw = sample
    original = sources._read_source
    changed = False
    def change_bytes(fd, receipt):
        nonlocal changed
        output = original(fd, receipt)
        if not changed:
            changed = True
            (root / 'r1.pdf').write_bytes(b'x' * len(raw))
        return output
    monkeypatch.setattr(sources, '_read_source', change_bytes)
    with pytest.raises(ValueError):
        collect_expense_sources(root, submission)


def test_missing_second_source_no_partial_success(sample):
    root, submission, _ = sample
    submission['receipts'].append(dict(submission['receipts'][0], id='r2'))
    with pytest.raises(ValueError):
        collect_expense_sources(root, submission)


def test_collect_original_synthetic_pdf_bytes(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    assets = repository / 'output/pdf/expense-v1'
    entries = json.loads((assets / 'manifest.json').read_text())['normal']
    case = json.loads((repository / 'backend/fixtures/expense-v1/cases.json').read_text())['normal']
    root = tmp_path / 'sources'
    root.mkdir(mode=0o700)
    for entry in entries:
        filename = entry['id'] + '.pdf'
        (root / filename).write_bytes((assets / 'normal' / filename).read_bytes())
        (root / filename).chmod(0o600)
    outcome = collect_expense_sources(root, dict(kind='expense-reconcile', asOf='2026-10-08',
                                                transactionsCsv=case['transactionsCsv'], receipts=entries))
    assert len(outcome['files']) == 2
    assert not outcome['decodedFormatVerified']
