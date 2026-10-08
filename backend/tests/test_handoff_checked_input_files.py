"""Original producer files and real bounded exporter, with simulated GUI/activation."""
import hashlib
import json
from unittest.mock import patch
import pytest
from backend.tests.test_handoff_submit_evidence import test_handoff_trace
from backend.tests.test_handoff_result import fixture, RUN, SESSION
from backend.tests.test_handoff_bundle import archive
from backend.handoff_result import canonical
from backend.handoff_document import expected_document
from backend.handoff_bundle import decode_handoff_bundle
from desktop_control import LeaseController
from handoff_evidence import inspect_handoff_evidence
from handoff_export import build_bundle


@pytest.fixture
def files():
    source, report=fixture()
    f=test_handoff_trace.HandoffTraceTests()
    f.run_id, f.draft_session_id, f.owner=RUN,SESSION,'11111111-1111-1111-1111-111111111111'
    f.material_bytes=canonical(source.model_dump(mode='json'))
    f.document_bytes=expected_document(source, report, run_id=RUN,session_id=SESSION)
    f.draft_args, f.submit_report, f.draft_input_mode=[{'raw':json.dumps(report)}],report,'checked-draft-v1'
    f.setUp()
    try:
        root=f.task.directory
        binding=dict(version=1,runId=RUN,owner=f.owner,epoch=1)
        sid=dict(runId=RUN,sessionId=SESSION,inputSha256=hashlib.sha256(f.material_bytes).hexdigest())
        records={
            'handoff-session-binding.json':sid,
            'handoff-submission-protocol.json':dict(sid,version=1,protocol='p7-tool-submit-v1'),
            'handoff-input-mode.json':dict(sid,version=1,inputMode='checked-draft-v1')}
        for name,status in [('handoff-input-intent.json','INTENT'),('handoff-input-receipt.json','STORED')]:
            records[name]=dict(status=status,binding=binding,inputSha256=sid['inputSha256'],bytes=len(f.material_bytes))
        for name,value in records.items():
            p=root/name;p.write_bytes(canonical(value));p.chmod(0o600)
        controller=LeaseController(root/'lease.json',run_id=RUN,owner=f.owner,epoch=1,clock=lambda:100.)
        controller.revoke()
        yield root,controller,dict(binding=binding,materials=f.material_bytes,expected=f.document_bytes,
            draft_input_mode='checked-draft-v1')
    finally:f.doCleanups()


def export(files):
    root,c,args=files
    return build_bundle(root,c,args['materials'],args['expected'],draft_input_mode=args['draft_input_mode'])


def test_original_saved_files_exported_readonly_and_bound_in_host(files):
    root,_,args=files
    before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
    proof=inspect_handoff_evidence(root,**args)
    assert proof['inputMode']=='checked-draft-v1' and proof['filesVerified']
    assert not proof['sessionVerified'] and not proof['semanticVerified']
    bundle=export(files)
    result=decode_handoff_bundle(archive(bundle),**args)
    assert result['inputMode']=='checked-draft-v1' and result['status']=='TRANSPORT_VERIFIED'
    assert result['files']['artifacts/handoff-'+RUN+'.txt']==args['expected']
    assert not result['sessionVerified'] and not result['semanticVerified']
    assert before=={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('fault',['missing','mode','run','session','sha','bool_version','extra','public','symlink','default','document','result'])
def test_original_mode_record_and_saved_bytes_required(files,fault):
    root,_,args=files;p=root/'handoff-input-mode.json';value=json.loads(p.read_bytes())
    if fault=='missing':p.unlink()
    elif fault=='public':p.chmod(0o644)
    elif fault=='symlink':
        saved=root/'saved-mode.json';p.rename(saved);p.symlink_to(saved)
    elif fault=='default':args['draft_input_mode']='literal-text'
    elif fault in ('document','result'):
        q=root/('result.txt' if fault=='result' else 'artifacts/handoff-'+RUN+'.txt');q.write_bytes(b'changed')
    else:
        if fault=='mode':value['inputMode']='literal-text'
        if fault=='run':value['runId']='other'
        if fault=='session':value['sessionId']='other'
        if fault=='sha':value['inputSha256']='0'*64
        if fault=='bool_version':value['version']=True
        if fault=='extra':value['extra']=True
        p.write_bytes(canonical(value))
    with pytest.raises((ValueError,OSError)):inspect_handoff_evidence(root,**args)
    with pytest.raises((ValueError,OSError)):export(files)


@pytest.mark.parametrize('fault',['missing','mode','session','sha','bool_version','extra','manifest','guest','trace','default'])
def test_host_refuses_mode_tamper_even_with_updated_file_digest(files,fault):
    _,_,args=files;contents=export(files);manifest=json.loads(contents['guest-manifest.json'])
    name='handoff-input-mode.json';value=json.loads(contents[name])
    if fault=='missing':del contents[name];del manifest['guest']['files'][name]
    elif fault=='default':args['draft_input_mode']='literal-text'
    elif fault=='manifest':manifest['inputMode']='literal-text'
    elif fault=='guest':manifest['guest']['inputMode']='literal-text'
    elif fault=='trace':manifest['guest']['trace']['inputMode']='literal-text'
    else:
        if fault=='mode':value['inputMode']='literal-text'
        if fault=='session':value['sessionId']='other'
        if fault=='sha':value['inputSha256']='0'*64
        if fault=='bool_version':value['version']=True
        if fault=='extra':value['extra']=True
        contents[name]=canonical(value)
        manifest['guest']['files'][name]=dict(bytes=len(contents[name]),sha256=hashlib.sha256(contents[name]).hexdigest())
    contents['guest-manifest.json']=canonical(manifest)
    with pytest.raises(ValueError):decode_handoff_bundle(archive(contents),**args)


def test_mode_file_rechecked_after_collection(files):
    root,_,args=files
    import handoff_evidence
    original=handoff_evidence.verify_handoff_trace
    def replaced(*a,**kw):
        result=original(*a,**kw)
        p=root/'handoff-input-mode.json';p.write_bytes(p.read_bytes()+b' ')
        return result
    with patch.object(handoff_evidence,'verify_handoff_trace',side_effect=replaced):
        with pytest.raises(ValueError):inspect_handoff_evidence(root,**args)
