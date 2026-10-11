"""Simulated confirmed-commit prerequisite; real temporary path checks."""
import base64
import copy
import json
from pathlib import Path
import struct
import sys
import zlib
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calc_save_task import CalcSaveTask, _inspect_unused_path, inspect_unused_destination
from calc_save import workbook_destination
from desktop_lease import LeaseGate
from driver_smoke import StopRun
from test_calc_save import setup as snapshot_fixture


def test_unused_path_readonly_and_symlink_refusal(tmp_path):
    root=tmp_path.resolve();root.chmod(0o700);p=root/'new.ods'
    assert _inspect_unused_path(p)['inode']==root.stat().st_ino and not p.exists()
    p.symlink_to(root/'missing')
    with pytest.raises(ValueError):_inspect_unused_path(p)
    with pytest.raises(ValueError):inspect_unused_destination(str(p))


def test_existing_and_shared_parent_refused(tmp_path):
    root=tmp_path.resolve();root.chmod(0o700);p=root/'existing.ods';p.write_bytes(b'original')
    with pytest.raises(ValueError):_inspect_unused_path(p)
    assert p.read_bytes()==b'original'
    root.chmod(0o777)
    with pytest.raises(ValueError):_inspect_unused_path(root/'new.ods')


@pytest.fixture
def save_task(tmp_path):
    root=tmp_path.resolve();root.chmod(0o700)
    run='calc-select-11111111-2222-3333-4444-555555555555'
    control=root/'lease.json';lease=dict(version=1,runId=run,owner='worker',epoch=1,stopped=False,expiresAt=120000)
    control.write_text(json.dumps(lease));control.chmod(0o600)
    state,args=snapshot_fixture();serial=[0];calls=[];failure=[None]
    def chunk(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',800,600,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'*(801*600)))+chunk(b'IEND',b'')
    state['screenshot_png_b64']=base64.b64encode(png).decode()
    def transport(tool,payload):
        calls.append((tool,copy.deepcopy(payload)))
        if tool=='click' and failure[0]=='timeout':raise TimeoutError('unknown')
        if tool=='get_window_state':
            serial[0]+=1;s=copy.deepcopy(state);s['snapshot_id']=f's{serial[0]:08x}'
            for e in s['elements']:e['element_token']=s['snapshot_id']+':'+str(e['element_index'])
            return s
        return {'ok':True}
    checker=lambda destination:_inspect_unused_path(root/'test.ods')
    t=CalcSaveTask(root/run,lease=LeaseGate(control,run_id=run,owner='worker',epoch=1,clock=lambda:100),
        pid=10,window_id=20,title='Untitled 1',cell='A2',grid=args['grid'],approved=True,
        input_approved=True,overwrite_disposable=True,approved_text='AbZ中文',approved_kind='text',commit_approved=True,
        save_approved=True,destination=workbook_destination(run),toolbar_region=args['toolbar_region'],destination_check=checker,
        transport=transport,identity=lambda pid:None,environment=lambda:None,shared_lock=root/'bridge.lock')
    t.observe();t.phase='COMMIT_CONFIRMED';t.before_commit='previous-commit-snapshot'
    yield t,calls,control,lease,root,failure
    t.close()


def test_open_save_once_and_observe_is_not_saved(save_task):
    t,calls,*_=save_task
    r=t.open_save(snapshot_id=t.snapshot['snapshot_id'],name_box_index=2)
    assert [x[0] for x in calls]==['get_window_state','click','get_window_state']
    assert calls[1][1]==dict(pid=10,window_id=20,session=t.run_id,element_token='s00000001:4')
    assert r['status']=='SAVE_DIALOG_ATTEMPT_OBSERVED' and not r['saved'] and t.phase=='AWAITING_SAVE_DIALOG'
    with pytest.raises(StopRun):t.open_save(snapshot_id=r['state']['snapshot_id'],name_box_index=2)
    assert t.used==3 and len(calls)==3


def test_save_entry_budget_boundary(save_task):
    t,calls,*_=save_task
    t.used=16
    result=t.open_save(snapshot_id=t.snapshot['snapshot_id'],name_box_index=2)
    assert t.used==18 and len(calls)==3 and not result['saved']


def test_existing_save_intent_prevents_dispatch(save_task):
    t,calls,*_=save_task
    intent=t.directory/'save-open-attempt.json'
    intent.write_bytes(b'original intent')
    with pytest.raises(FileExistsError):
        t.open_save(snapshot_id=t.snapshot['snapshot_id'],name_box_index=2)
    assert t.stopped.is_set() and len(calls)==1
    assert intent.read_bytes()==b'original intent'


@pytest.mark.parametrize('fault',['exists','parent','budget','stopped','unknown','lease','old','phase','value','audit','timeout'])
def test_save_failure_never_retries(save_task,monkeypatch,fault):
    t,calls,control,lease,root,failure=save_task;snapshot=t.snapshot['snapshot_id']
    if fault=='exists':(root/'test.ods').write_bytes(b'original')
    elif fault=='parent':t.destination_identity={'inode':0}
    elif fault=='budget':t.used=17
    elif fault=='stopped':t.stop()
    elif fault=='unknown':t.uncertain=True
    elif fault=='lease':control.write_text(json.dumps(dict(lease,stopped=True)))
    elif fault=='old':snapshot='old'
    elif fault=='phase':t.phase='INPUT_OBSERVED'
    elif fault=='value':t.snapshot['elements'][1]['value']='wrong'
    elif fault=='audit':
        record=t.record
        def failed(row):
            if row['event']=='save_open_intent':raise OSError('audit unavailable')
            return record(row)
        monkeypatch.setattr(t,'record',failed)
    elif fault=='timeout':failure[0]='timeout'
    with pytest.raises((ValueError,StopRun,OSError,TimeoutError)):t.open_save(snapshot_id=snapshot,name_box_index=2)
    assert t.stopped.is_set() and len(calls)==(2 if fault=='timeout' else 1)
    if fault=='timeout':assert t.uncertain
    with pytest.raises(StopRun):t.open_save(snapshot_id=snapshot,name_box_index=2)
    assert len(calls)==(2 if fault=='timeout' else 1)
