"""Synthetic in-memory parser cases, never evidence of a GUI-created workbook."""
import io
import hashlib
import zipfile

import pytest

from backend.expense_workbook import decode_expense_workbook, MIME


def package(rows='', *, xml=None, extra=()):
    if xml is None:
        xml = ('''<office:document-content
          xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
          xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
          xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
          xmlns:xlink="http://www.w3.org/1999/xlink">
          <office:body><office:spreadsheet><table:table table:name="Sheet1">'''
          + rows + '</table:table></office:spreadsheet></office:body></office:document-content>').encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('mimetype', MIME)
        archive.writestr('content.xml', xml)
        for name, value in extra:
            archive.writestr(name, value)
    return output.getvalue()


def row(cell):
    return '<table:table-row>' + cell + '</table:table-row>'


def string(value, attrs=''):
    return f'<table:table-cell office:value-type="string" {attrs}><text:p>{value}</text:p></table:table-cell>'


def test_values_are_decoded_not_accepted():
    raw = package(row(string('abz')) + row('<table:table-cell office:value-type="float" office:value="12.3"><text:p>12.30</text:p></table:table-cell>'))
    result = decode_expense_workbook(raw)
    assert result['status'] == 'CELL_VALUES_DECODED'
    assert result['sheets'][0]['cells'] == [
        dict(row=1, column=1, type='string', value='abz', display='abz'),
        dict(row=2, column=1, type='float', value='12.3', display='12.30')]
    assert not result['guiVerified'] and not result['semanticVerified'] and not result['fileSafetyVerified']
    assert result['sizeBytes'] == len(raw)
    assert result['sha256'] == hashlib.sha256(raw).hexdigest()


def test_repeated_empty_rows_do_not_expand_and_coordinates_preserved():
    rows = '<table:table-row table:number-rows-repeated="1048575"><table:table-cell table:number-columns-repeated="16384"/></table:table-row>'
    rows += row('<table:table-cell table:number-columns-repeated="16383"/>' + string('X'))
    cells = decode_expense_workbook(package(rows))['sheets'][0]['cells']
    assert len(cells) == 1 and cells[0]['row'] == 1048576 and cells[0]['column'] == 16384


def test_repeated_values_and_odf_whitespace():
    cell = string('A<text:s text:c="2"/><text:span>B</text:span><text:tab/>C<text:line-break/>D', 'table:number-columns-repeated="2"')
    rows = '<table:table-row table:number-rows-repeated="2">' + cell + '</table:table-row>'
    cells = decode_expense_workbook(package(rows))['sheets'][0]['cells']
    assert [(c['row'], c['column']) for c in cells] == [(1, 1), (1, 2), (2, 1), (2, 2)]
    assert all(c['value'] == 'A  B\tC\nD' for c in cells)


@pytest.mark.parametrize('cell', [
    string('cached', 'table:formula="of:=1+1"'),
    string('merged', 'table:number-columns-spanned="2"'),
    string('link', 'xlink:href="https://example.invalid"'),
    string('<text:a xlink:href="file:///etc/passwd">link</text:a>'),
    string('<text:s text:c="9999999"/>'),
    string('x' * 4097),
    string('x', 'office:string-value="different"'),
    '<table:covered-table-cell/>',
    '<table:table-cell><text:p>untyped</text:p></table:table-cell>',
    '<table:table-cell office:value-type="boolean" office:boolean-value="true"/>',
    '<table:table-cell office:value-type="date" office:date-value="2026-10-09"/>',
    '<table:table-cell office:value-type="float" office:value="NaN"/>',
    '<table:table-cell office:value-type="float" office:value="1e999999"/>',
    '<table:table-cell office:value-type="float" office:value="01.2"/>',
    string('x', 'table:number-columns-repeated="10001"'),
    string('x', 'table:number-columns-repeated="0"'),
    string('x', 'table:number-columns-repeated="-1"'),
])
def test_unsupported_or_unsafe_cells_fail_closed(cell):
    with pytest.raises(ValueError, match='EXPENSE_WORKBOOK_UNVERIFIED'):
        decode_expense_workbook(package(row(cell)))


@pytest.mark.parametrize('raw', [b'', b'not zip', b'x' * (8 * 1024 * 1024 + 1), None, bytearray()])
def test_invalid_container(raw):
    with pytest.raises(ValueError, match='EXPENSE_WORKBOOK_UNVERIFIED'):
        decode_expense_workbook(raw)


@pytest.mark.parametrize('xml', [b'<!DOCTYPE a [<!ENTITY x "y">]><a/>', b'<a/>', b'<a>', b'<a/>\x00', '<a/>'.encode('utf-16'), b'<?xml version="1.0" encoding="ISO-8859-1"?><a/>', b'x' * (4 * 1024 * 1024 + 1)])
def test_bad_xml(xml):
    with pytest.raises(ValueError, match='EXPENSE_WORKBOOK_UNVERIFIED'):
        decode_expense_workbook(package(xml=xml))


@pytest.mark.parametrize('name', ['../x', '/x', 'a/../x', 'a\\b', 'a:b', 'a//b'])
def test_bad_member_paths(name):
    with pytest.raises(ValueError, match='EXPENSE_WORKBOOK_UNVERIFIED'):
        decode_expense_workbook(package(extra=[(name, b'x')]))


def test_duplicate_members():
    with pytest.warns(UserWarning, match='Duplicate name'):
        raw = package(extra=[('content.xml', b'<a/>')])
    with pytest.raises(ValueError, match='EXPENSE_WORKBOOK_UNVERIFIED'):
        decode_expense_workbook(raw)


def test_unknown_table_structure_rejected():
    with pytest.raises(ValueError):
        decode_expense_workbook(package('<table:table-row-group>' + row(string('not silently dropped')) + '</table:table-row-group>'))


def test_expanded_row_budget():
    with pytest.raises(ValueError):
        decode_expense_workbook(package('<table:table-row table:number-rows-repeated="10001">' + string('x') + '</table:table-row>'))


def test_formula_like_plain_text_is_not_executed():
    result = decode_expense_workbook(package(row(string('=1+1'))))
    assert result['sheets'][0]['cells'][0]['value'] == '=1+1'


def test_decimal_precision_and_case_are_not_normalized():
    value = '99999999999999999999.123456789'
    cells = decode_expense_workbook(package(row(string('AbZ')) + row(
        f'<table:table-cell office:value-type="float" office:value="{value}"><text:p>rounded display</text:p></table:table-cell>')))['sheets'][0]['cells']
    assert cells[0]['value'] == 'AbZ'
    assert cells[1]['value'] == value and cells[1]['display'] == 'rounded display'


@pytest.mark.parametrize('repeat', ['0', '-1', '1048577', '99999999999999999'])
def test_invalid_row_repeats(repeat):
    with pytest.raises(ValueError):
        decode_expense_workbook(package(f'<table:table-row table:number-rows-repeated="{repeat}"/>'))


def test_member_count_limit():
    with pytest.raises(ValueError):
        decode_expense_workbook(package(extra=[(f'x{i}', b'') for i in range(127)]))


def test_all_sheets_decoded_and_duplicate_names_rejected():
    raw = package(row(string('first')))
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        xml = archive.read('content.xml')
    second = '<table:table table:name="Second">' + row(string('second')) + '</table:table>'
    xml = xml.replace(b'</office:spreadsheet>', second.encode() + b'</office:spreadsheet>')
    decoded = decode_expense_workbook(package(xml=xml))
    assert [(s['name'], s['cells'][0]['value']) for s in decoded['sheets']] == [('Sheet1', 'first'), ('Second', 'second')]
    with pytest.raises(ValueError):
        decode_expense_workbook(package(xml=xml.replace(b'name="Second"', b'name="Sheet1"')))
