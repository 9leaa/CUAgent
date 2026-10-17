"""Real ZIP/XML and filesystem checks, no simulated GUI success."""
import io
import os
import zipfile
import pytest
from calc_workbook_verify import MIME, inspect_ods, read_saved_workbook


def workbook(text='AbZ中文', *, formula='', rows='', markup=False):
    cell = '<text:span>'+text+'</text:span>' if markup else text
    xml = f'''<office:document-content
      xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
      xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
      xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
      <office:body><office:spreadsheet><table:table table:name="Sheet1">
      <table:table-row {rows}><table:table-cell/></table:table-row>
      <table:table-row><table:table-cell office:value-type="string" {formula}>
      <text:p>{cell}</text:p></table:table-cell></table:table-row>
      </table:table></office:spreadsheet></office:body></office:document-content>'''
    return archive(xml.encode())


def archive(xml, duplicate=False):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype', MIME)
        z.writestr('content.xml', xml)
        if duplicate:z.writestr('content.xml', xml)
    return out.getvalue()


def verify(data):
    return inspect_ods(data, sheet='Sheet1', expected_text='AbZ中文')


def test_exact_unicode_text_without_gui_success_claim():
    result = verify(workbook())
    assert result['status']=='WORKBOOK_CONTENT_VERIFIED'
    assert result['text']=='AbZ中文'
    assert not result['guiExecutionVerified'] and not result['reopenedVerified']


@pytest.mark.parametrize('kwargs', [dict(text='other'), dict(formula='table:formula="of:=1"'),
    dict(rows='table:number-rows-repeated="1048576"'), dict(rows='table:number-rows-repeated="0"'),
    dict(markup=True)])
def test_wrong_or_ambiguous_content_rejected(kwargs):
    with pytest.raises(ValueError):verify(workbook(**kwargs))


@pytest.mark.parametrize('xml', [b'<!DOCTYPE x [<!ENTITY a "abc">]><x/>',
    '<!DOCTYPE x><x/>'.encode('utf-16'), b'<x>\x00</x>'])
def test_unsafe_xml_rejected(xml):
    with pytest.raises((ValueError,UnicodeError)):verify(archive(xml))


def test_duplicate_zip_member_rejected():
    with pytest.warns(UserWarning):data=archive(b'<x/>',duplicate=True)
    with pytest.raises(ValueError,match='unsafe archive'):verify(data)


def test_decompression_limit():
    data=archive(b' '*(8*1024*1024+1))
    assert len(data)<100000
    with pytest.raises(ValueError,match='unsafe archive'):verify(data)


def identity(path):
    s=path.stat()
    return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid)


def test_read_only_real_file_and_bound_parent(tmp_path):
    p=tmp_path/'result.ods';data=workbook();p.write_bytes(data)
    before=p.stat()
    result=read_saved_workbook(p,parent_identity=identity(tmp_path),sheet='Sheet1',expected_text='AbZ中文')
    assert result['bytes']==len(data) and p.read_bytes()==data
    assert p.stat().st_mtime_ns==before.st_mtime_ns
    with pytest.raises(ValueError,match='parent changed'):
        read_saved_workbook(p,parent_identity={**identity(tmp_path),'inode':0},sheet='Sheet1',expected_text='AbZ中文')


@pytest.mark.parametrize('kind',['symlink','hardlink'])
def test_linked_file_rejected(tmp_path,kind):
    source=tmp_path/'source.ods';source.write_bytes(workbook());p=tmp_path/'result.ods'
    if kind=='symlink':p.symlink_to(source)
    else:os.link(source,p)
    with pytest.raises((OSError,ValueError)):
        read_saved_workbook(p,parent_identity=identity(tmp_path),sheet='Sheet1',expected_text='AbZ中文')
