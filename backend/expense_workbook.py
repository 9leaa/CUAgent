"""Read-only, bounded ODS value decoding. Not GUI, provenance or business acceptance."""
import hashlib
import io
import re
import zipfile
import zlib
from decimal import Decimal
from xml.etree import ElementTree as ET

O = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
T = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
X = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
MIME = b'application/vnd.oasis.opendocument.spreadsheet'
ERROR = 'EXPENSE_WORKBOOK_UNVERIFIED'
MAX_CELLS = 10000


def _require(ok):
    if not ok:
        raise ValueError(ERROR)


def _count(node, attribute, limit):
    raw = node.get(attribute, '1')
    _require(re.fullmatch(r'[1-9][0-9]{0,6}', raw) is not None)
    value = int(raw)
    _require(value <= limit)
    return value


def _text(node, depth=0):
    _require(depth <= 16)
    result = node.text or ''
    for child in node:
        if child.tag == X + 'span':
            part = _text(child, depth + 1)
        else:
            _require(not list(child) and not child.text)
            if child.tag == X + 's':
                part = ' ' * _count(child, X + 'c', 4096)
            elif child.tag == X + 'tab':
                part = '\t'
            elif child.tag == X + 'line-break':
                part = '\n'
            else:
                raise ValueError(ERROR)
        result += part + (child.tail or '')
        _require(len(result) <= 4096)
    _require(len(result.encode('utf-8')) <= 4096)
    return result


def _cell(node):
    _require(node.tag == T + 'table-cell')
    for key in node.attrib:
        _require(not (key.startswith(T) and ('spanned' in key or 'formula' in key)))
    _require(not (node.text or '').strip())
    _require(all(p.tag == X + 'p' and not (p.tail or '').strip() for p in node))
    display = '\n'.join(_text(p) for p in node)
    _require(len(display.encode('utf-8')) <= 4096)
    kind = node.get(O + 'value-type')
    values = {k: v for k, v in node.attrib.items() if k.startswith(O)}
    if kind is None:
        _require(not values and not display)
        return None
    if kind == 'string':
        _require(set(values) <= {O + 'value-type', O + 'string-value'})
        value = node.get(O + 'string-value', display)
        _require(value == display)
    elif kind == 'float':
        _require(set(values) == {O + 'value-type', O + 'value'})
        value = values[O + 'value']
        _require(len(value) <= 128 and re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value) is not None)
        _require(Decimal(value).is_finite())
    else:
        raise ValueError(ERROR)
    return dict(type=kind, value=value, display=display)


def _read_member(archive, name, limit):
    info = archive.getinfo(name)
    _require(info.file_size <= limit)
    with archive.open(info) as stream:
        raw = stream.read(limit + 1)
    _require(len(raw) == info.file_size and len(raw) <= limit)
    return raw


def decode_expense_workbook(raw):
    """Caller supplies independently collected bytes. No filesystem or execution side effects."""
    try:
        _require(type(raw) is bytes and 0 < len(raw) <= 8 * 1024 * 1024)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            names = [m.filename for m in members]
            _require(0 < len(members) <= 128 and len(set(names)) == len(names))
            _require(sum(m.file_size for m in members) <= 32 * 1024 * 1024)
            for member in members:
                name = member.filename
                _require(name == member.orig_filename and '\\' not in name
                         and not name.startswith('/') and ':' not in name
                         and all(p not in ('', '.', '..') for p in name.rstrip('/').split('/')))
                _require(not member.flag_bits & 1 and member.compress_type in (0, 8))
            _require(_read_member(archive, 'mimetype', 128) == MIME)
            xml = _read_member(archive, 'content.xml', 4 * 1024 * 1024)
        # Reject alternate encodings, DTDs and entities before XML parsing.
        text = xml.decode('utf-8')
        _require('\x00' not in text and '<!DOCTYPE' not in text and '<!ENTITY' not in text)
        declaration = re.match(r'\ufeff?<\?xml\s+([^?]*)\?>', text)
        if declaration:
            encoding = re.search(r'encoding\s*=\s*[\"\']([^\"\']+)', declaration[1])
            _require(encoding is None or encoding[1].lower() == 'utf-8')
        root = ET.fromstring(xml)
        _require(root.tag == O + 'document-content')
        for node in root.iter():
            _require(T + 'formula' not in node.attrib
                     and '{http://www.w3.org/1999/xlink}href' not in node.attrib)
        bodies = root.findall(O + 'body')
        _require(len(bodies) == 1 and len(bodies[0]) == 1)
        book = bodies[0][0]
        _require(book.tag == O + 'spreadsheet' and 1 <= len(book) <= 10)
        tables, metadata, seen_metadata = [], {}, set()
        for child in book:
            if child.tag == T + 'table':
                tables.append(child)
                continue
            _require(child.tag in (T + 'calculation-settings', T + 'named-expressions')
                     and child.tag not in seen_metadata)
            seen_metadata.add(child.tag)
            _require(not list(child) and not (child.text or '').strip()
                     and not (child.tail or '').strip())
            if child.tag == T + 'named-expressions':
                _require(not child.attrib)
            else:
                for key, value in child.attrib.items():
                    if key in {T + 'automatic-find-labels', T + 'use-regular-expressions', T + 'use-wildcards'}:
                        _require(value in ('true', 'false'))
                    elif key == T + 'null-year':
                        _require(re.fullmatch(r'[0-9]{4}', value) is not None)
                    else:
                        raise ValueError(ERROR)
                metadata = {key[len(T):]: value for key, value in child.attrib.items()}
        _require(1 <= len(tables) <= 8)
        sheets, names, total = [], set(), 0
        for table in tables:
            _require(table.tag == T + 'table')
            name = table.get(T + 'name')
            _require(name and len(name.encode('utf-8')) <= 256 and name not in names)
            names.add(name)
            cells, row_index = [], 1
            for row in table:
                if row.tag == T + 'table-column':
                    _require(not list(row))
                    continue
                _require(row.tag == T + 'table-row')
                repeat_rows = _count(row, T + 'number-rows-repeated', 1048576)
                _require(row_index + repeat_rows - 1 <= 1048576)
                row_cells, column = [], 1
                for cell in row:
                    repeat_cols = _count(cell, T + 'number-columns-repeated', 16384)
                    _require(column + repeat_cols - 1 <= 16384)
                    value = _cell(cell)
                    if value is not None:
                        _require(total + (len(row_cells) + repeat_cols) * repeat_rows <= MAX_CELLS)
                        row_cells.extend(dict(column=c, **value) for c in range(column, column + repeat_cols))
                    column += repeat_cols
                if row_cells:
                    cells.extend(dict(row=r, **cell) for r in range(row_index, row_index + repeat_rows) for cell in row_cells)
                    total += len(row_cells) * repeat_rows
                row_index += repeat_rows
            sheets.append(dict(name=name, cells=cells))
        return dict(status='CELL_VALUES_DECODED', sha256=hashlib.sha256(raw).hexdigest(),
                    sizeBytes=len(raw), sheets=sheets, guiVerified=False,
                    semanticVerified=False, fileSafetyVerified=False,
                    declaredCalculationSettings=metadata, calculationSettingsApplied=False)
    except (ValueError, TypeError, KeyError, OverflowError, RuntimeError, OSError, ET.ParseError, zipfile.BadZipFile, NotImplementedError, zlib.error):
        raise ValueError(ERROR) from None
