"""Unexposed checked draft selector; original raw GUI path, simulated transport."""
import hashlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools/mac_vm'))
from backend.tests.test_handoff_result import fixture, RUN, SESSION
from backend.handoff_result import canonical
from desktop_control import LeaseController
from handoff_task import HandoffDesktopTask
from driver_smoke import StopRun


@pytest.fixture
def selected(tmp_path):
    source, report = fixture()
    raw = canonical(source.model_dump(mode='json'))
    control = LeaseController(tmp_path/'lease.json', run_id=RUN, owner='worker', epoch=1, clock=lambda:100.)
    control.renew(1)
    send = Mock(return_value={'ok': True})
    t = HandoffDesktopTask(tmp_path/RUN, send, lambda _:None, lease=control.gate,
        approved=True, environment=lambda:None, input_sha256=hashlib.sha256(raw).hexdigest(),
        draft_session_id=SESSION, submission_protocol='p7-tool-submit-v1', draft_input_mode='checked-draft-v1')
    p=t.directory/'handoff-input.json'; p.write_bytes(raw); p.chmod(0o600)
    checked=t.check_draft({'raw':json.dumps(report)})
    t.pid,t.window=10,20
    t.snapshot=dict(snapshot_id='fresh', elements=[
        dict(role='AXWindow',label=t.case.title,element_index=0),
        dict(role='AXTextArea',element_index=1,element_token='fresh:1',parent_index=0)])
    t.observed_at=time.monotonic()
    args=dict(snapshot_id='fresh',element_index=1,element_token='fresh:1',documentSha256=checked['documentSha256'])
    return t,control,send,checked,args


def test_selection_uses_exact_bound_bytes_once_via_raw_gui(selected):
    t,_,send,draft,args=selected
    assert t.type_checked_draft(args)=={'ok':True}
    send.assert_called_once_with('type_text',dict(pid=10,window_id=20,session=RUN,
        element_index=1,element_token='fresh:1',text=draft['document']))
    assert t.used==2 and t.input_once and t.snapshot is None
    assert t.document.read_bytes()==b''  # No direct file writing by selector.
    rows=[json.loads(x) for x in t.ledger.read_text().splitlines()]
    intent=next(r for r in rows if r['event']=='checked_draft_input_intent')
    assert intent['args']==args and intent['used']==1 and intent['mode']=='checked-draft-v1'
    assert sum(r['event']=='dispatch' and r['tool']=='type_text' for r in rows)==1
    with pytest.raises(StopRun):t.type_checked_draft(args)
    assert t.used==2 and send.call_count==1


@pytest.mark.parametrize('fault',['mode','draft','digest','tamper','extra','snapshot','token','stale',
    'stop','lease','budget','reopen','input','uncertain'])
def test_bad_selector_or_authority_never_sends(selected,fault):
    t,c,send,_,args=selected
    if fault=='mode':t.draft_input_mode='literal-text'
    if fault=='draft':t.validated_draft=None
    if fault=='digest':args['documentSha256']='0'*64
    if fault=='tamper':t.validated_draft['document']+='changed'
    if fault=='extra':args['text']='replacement'
    if fault=='snapshot':args['snapshot_id']='old'
    if fault=='token':args['element_token']='other'
    if fault=='stale':t.observed_at-=31
    if fault=='stop':t.stop()
    if fault=='lease':c.revoke()
    if fault=='budget':
        while t.used<30:t.charge_rejection('fixture',t.used,'fixture')
    if fault=='reopen':t.reopen_phase='closing'
    if fault=='input':t.input_once=True
    if fault=='uncertain':t.uncertain=True
    before=t.used
    with pytest.raises(StopRun):t.type_checked_draft(args)
    send.assert_not_called(); assert t.used==before


def test_literal_method_cannot_bypass_selected_mode(selected):
    t,_,send,draft,args=selected
    with pytest.raises(StopRun):
        t.type_text({k:v for k,v in args.items() if k!='documentSha256'}|{'text':draft['document']})
    send.assert_not_called()


def test_intent_write_failure_prevents_gui(selected):
    t,_,send,_,args=selected
    t.record=Mock(side_effect=OSError('injected audit failure'))
    with pytest.raises(OSError):t.type_checked_draft(args)
    send.assert_not_called(); assert t.used==1


def test_unknown_gui_input_is_counted_and_cannot_be_replayed(selected):
    t,_,send,_,args=selected
    send.side_effect=TimeoutError('unknown')
    with pytest.raises(TimeoutError):t.type_checked_draft(args)
    assert t.used==2 and t.uncertain
    with pytest.raises(StopRun):t.type_checked_draft(args)
    assert send.call_count==1 and t.used==2


@pytest.mark.parametrize('protocol,session,mode',[
    ('legacy-final-json',SESSION,'checked-draft-v1'),
    ('p7-tool-submit-v1',None,'checked-draft-v1'),
    ('p7-tool-submit-v1',SESSION,'unknown')])
def test_constructor_requires_explicit_trusted_binding(tmp_path,protocol,session,mode):
    with pytest.raises(ValueError):
        HandoffDesktopTask(tmp_path/'never-created',input_sha256='a'*64,
            draft_session_id=session,submission_protocol=protocol,draft_input_mode=mode)
    assert not (tmp_path/'never-created').exists()
