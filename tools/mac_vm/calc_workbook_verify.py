"""Bounded, read-only ODS content verification; never proves GUI execution."""
import hashlib
import io
import os
from pathlib import Path
import stat
import zipfile
from xml.etree import ElementTree as ET

MIME = b'application/vnd.oasis.opendocument.spreadsheet'
NS = {'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
      'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
      'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
MAX_BYTES = 8 * 1024 * 1024


def _attr(element, prefix, name, default=None):
    return element.get('{'+NS[prefix]+'}'+name, default)


def _repeat(element, name):
    raw = _attr(element, 'table', name, '1')
    if not raw.isascii() or not raw.isdecimal() or not 1 <= int(raw) <= 1048576:
        raise ValueError('invalid repetition')
    return int(raw)


def inspect_ods(data, *, sheet, expected_text):
    if (not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES
            or not isinstance(sheet, str) or not sheet
            or not isinstance(expected_text, str) or not expected_text
            or len(expected_text.encode('utf8')) > 256):
        raise ValueError('bounded workbook and explicit expectation required')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        if (len(entries) > 256 or len(set(names)) != len(names)
                or sum(item.file_size for item in entries) > MAX_BYTES
                or any(item.flag_bits & 1 or stat.S_ISLNK(item.external_attr >> 16)
                       or item.file_size > MAX_BYTES for item in entries)):
            raise ValueError('unsafe archive structure')
        if archive.read('mimetype') != MIME:
            raise ValueError('ODS mimetype required')
        xml = archive.read('content.xml')
    # ODF content is UTF-8; decode before checking so alternate byte encodings
    # cannot hide an entity/DTD declaration from this bounded parser.
    source = xml.decode('utf-8-sig')
    if '\x00' in source or '<!DOCTYPE' in source.upper() or '<!ENTITY' in source.upper():
        raise ValueError('DTD and entities forbidden')
    root = ET.fromstring(source)
    spreadsheets = root.findall('office:body/office:spreadsheet', NS)
    if len(spreadsheets) != 1:
        raise ValueError('single spreadsheet required')
    tables = [e for e in spreadsheets[0].findall('table:table', NS)
              if _attr(e, 'table', 'name') == sheet]
    if len(tables) != 1:
        raise ValueError('unique bound sheet required')
    # Only A2 is supported. Count repeats arithmetically, never expand them.
    row_number = 1
    target = None
    for row in tables[0].findall('table:table-row', NS):
        repeat = _repeat(row, 'number-rows-repeated')
        if row_number <= 2 < row_number + repeat:
            target = row
            break
        row_number += repeat
    if target is None:
        raise ValueError('A2 missing')
    cells = [e for e in target if e.tag in
             ('{'+NS['table']+'}table-cell', '{'+NS['table']+'}covered-table-cell')]
    if not cells or cells[0].tag.endswith('covered-table-cell'):
        raise ValueError('A2 missing or covered')
    cell = cells[0]
    _repeat(cell, 'number-columns-repeated')
    if (_attr(cell, 'table', 'formula') is not None
            or _attr(cell, 'office', 'value-type') != 'string'):
        raise ValueError('literal text cell required')
    paragraphs = cell.findall('text:p', NS)
    # Exact literal text only for this fixed acceptance payload; unsupported
    # markup fails closed instead of silently normalizing spaces or fields.
    if any(list(p) for p in paragraphs):
        raise ValueError('unsupported text markup')
    text = '\n'.join(p.text or '' for p in paragraphs)
    attribute_text = _attr(cell, 'office', 'string-value')
    if text != expected_text or (attribute_text is not None and attribute_text != text):
        raise ValueError('A2 content mismatch')
    return dict(status='WORKBOOK_CONTENT_VERIFIED', sheet=sheet, cell='A2',
                text=text, sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data), guiExecutionVerified=False, reopenedVerified=False)


def read_saved_workbook(path, *, parent_identity, sheet, expected_text):
    """Caller supplies the originally admitted destination and parent identity."""
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError('canonical absolute bound path required')
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError('canonical directory ancestry required')
    before = path.parent.lstat()
    identity = dict(device=before.st_dev, inode=before.st_ino, uid=before.st_uid)
    if identity != parent_identity or before.st_uid != os.getuid() or before.st_mode & 0o022:
        raise ValueError('destination parent changed')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or not 0 < info.st_size <= MAX_BYTES):
            raise ValueError('owned bounded regular workbook required')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
        after = os.fstat(fd)
        if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('workbook changed while reading')
        if path.lstat() != after or path.parent.lstat() != before:
            raise ValueError('destination changed while reading')
    finally:
        os.close(fd)
    return inspect_ods(data, sheet=sheet, expected_text=expected_text)
