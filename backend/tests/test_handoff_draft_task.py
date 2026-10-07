import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/mac_vm'))
from desktop_control import LeaseController
from handoff_task import HandoffDesktopTask
from driver_smoke import StopRun
from backend.handoff_result import canonical
from backend.tests.test_handoff_result import fixture,RUN,SESSION


@pytest.fixture
def task(tmp_path):
    source,report=fixture();raw=canonical(source.model_dump(mode='json'))
    controller=LeaseController(tmp_path/'lease.json',run_id=RUN,owner='worker',epoch=1,clock=lambda:100.)
    controller.renew(1)
    task=HandoffDesktopTask(tmp_path/RUN,lambda *_:pytest.fail('No GUI dispatch'),lambda _:None,
        lease=controller.gate,approved=True,environment=lambda:None,
        input_sha256=hashlib.sha256(raw).hexdigest(),draft_session_id=SESSION)
    p=task.directory/'handoff-input.json';p.write_bytes(raw);p.chmod(0o600)
    return task,controller,report


def test_valid_draft_original_binding_and_audit(task):
    t,_,report=task;t.snapshot={'snapshot_id':'old'}
    result=t.check_draft({'raw':json.dumps(report,ensure_ascii=False)})
    assert result['status']=='DRAFT_STRUCTURE_VALID' and result['used']==1
    assert t.validated_draft['canonicalJson']==canonical(report).decode()
    assert t.snapshot is None and not t.inflight
    rows=[json.loads(l) for l in t.ledger.read_text().splitlines()]
    args=next(r for r in rows if r['event']=='helper_arguments')
    done=next(r for r in rows if r['event']=='result')
    assert args['call_id']==done['call_id'] and done['value']==result


def test_rejected_json_is_counted_feedback_and_clears_prior_draft(task):
    t,_,report=task
    t.check_draft({'raw':json.dumps(report)})
    result=t.check_draft({'raw':'{"tasks":[}'})
    assert result['status']=='DRAFT_REJECTED' and result['code']=='JSON_SYNTAX' and result['used']==2
    assert t.validated_draft is None and not t.inflight


@pytest.mark.parametrize('mode',['session','args','oversize','saved','reopen','unbound','tamper'])
def test_identity_and_lifecycle_cannot_be_supplied_or_bypassed(task,mode):
    t,_,report=task;args={'raw':json.dumps(report)}
    if mode=='session':report['sessionId']='session-33333333-3333-3333-3333-333333333333';args['raw']=json.dumps(report)
    if mode=='args':args['sessionId']=SESSION
    if mode=='oversize':args['raw']='x'*65537
    if mode=='saved':t.saved_once=True
    if mode=='reopen':t.reopen_phase='reopened'
    if mode=='unbound':t.draft_session_id=None
    if mode=='tamper':(t.directory/'handoff-input.json').write_bytes(b'{}')
    if mode=='session':assert t.check_draft(args)['status']=='DRAFT_REJECTED'
    else:
        with pytest.raises((ValueError,StopRun)):t.check_draft(args)
    assert t.used==1 and t.validated_draft is None and not t.inflight


def test_budget_thirty_and_revocation(task):
    t,c,_=task
    for n in range(30):assert t.check_draft({'raw':'{}'})['used']==n+1
    with pytest.raises(StopRun):t.check_draft({'raw':'{}'})
    assert t.used==30


def test_revoked_no_dispatch(task):
    t,c,_=task;c.revoke()
    with pytest.raises(StopRun):t.check_draft({'raw':'{}'})
    assert t.used==0


def test_stop_during_preflight_allows_only_original_admitted_result(task):
    t, _, report = task
    original = t._read_frozen_input
    def stopped_read():
        t.stop()
        return original()
    t._read_frozen_input = stopped_read
    assert t.check_draft({'raw': json.dumps(report)})['used'] == 1
    with pytest.raises(StopRun):
        t.check_draft({'raw': '{}'})
    assert t.used == 1 and not t.inflight


def test_restart_does_not_reset_budget_or_recover_draft_cache(task):
    t, c, report = task
    t.check_draft({'raw': json.dumps(report)})
    restarted = HandoffDesktopTask(t.directory, lambda *_: pytest.fail('No GUI dispatch'), lambda _: None,
        lease=c.gate, approved=True, environment=lambda: None,
        input_sha256=t.input_sha256, draft_session_id=SESSION)
    assert restarted.used == 1 and restarted.validated_draft is None
    with pytest.raises(StopRun):
        restarted.check_draft({'raw': '{}'})
    assert restarted.used == 1
