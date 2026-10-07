import json
import hashlib
from types import SimpleNamespace
from datetime import timedelta
from unittest.mock import Mock
import pytest
from sqlalchemy import select
import backend.desktop_reconcile as module
from backend.models import Artifact, Attempt, Notification, Resource, Task, utcnow


@pytest.fixture
def case(service, monkeypatch):
    task_id, _ = service.submit(dict(kind='desktop-textedit', lines=['example']), 'reconcile')
    task = service.claim('original-owner', kind='desktop-textedit', task_id=task_id)
    root = service.settings.root / ('p2-' + task_id); root.mkdir(mode=0o700)
    session_id = 'session-00000000-0000-4000-8000-000000000001'
    service.record_prepared(task_id, task.owner, task.epoch, root, session_id)
    service.control(task, stopped=True)
    binding = dict(version=1, runId=root.name, owner=task.owner, epoch=task.epoch)
    def save(path, value):
        path.write_text(json.dumps(value)); path.chmod(0o600)
    lock = service.settings.root / 'desktop-worker.lock'; lock.touch(mode=0o600)
    quarantine = lock.with_name(lock.name + '.quarantine'); save(quarantine, dict(taskId=task_id))
    save(root / 'guest-private-receipt.json', dict(binding=binding, controlToken='x'*43))
    save(root / 'desktop-tunnel-selection.json', dict(binding=binding, hostPort=19099))
    save(root / 'desktop-session-binding.json', dict(runId=root.name, sessionId=session_id, cwd=str(root/'workspace')))
    session = dict(sessionId=session_id, terminal=True, running=False, userMessages=1, promptObserved=True)
    guest = dict(stopped=True, pendingCalls=0, rawCalls=9)
    monkeypatch.setattr(module, 'DesktopSessionClient', Mock(return_value=Mock(inspect=lambda:session)))
    monkeypatch.setattr(module, 'DesktopControlClient', Mock(return_value=Mock(status=lambda:guest)))
    with service.sessions.begin() as db:
        db.get(Resource,'desktop').expires_at = utcnow()-timedelta(seconds=10)
    run = lambda: module.finalize_interrupted(service,task_id,shared_lock=lock,node='/unused',official_home='/unused',cookie='/unused')
    return task_id, root, quarantine, session, guest, run


def test_original_failure_finalized_without_success_or_unquarantine(service, case):
    task_id,root,quarantine,session,guest,run=case
    original=quarantine.read_bytes()
    assert run()['status']=='UNVERIFIED'
    assert quarantine.read_bytes()==original
    assert (root/'desktop-reconcile-intent.json').stat().st_mode & 0o077 == 0
    with service.sessions() as db:
        task=db.get(Task,task_id)
        assert task.status=='UNVERIFIED' and task.calls==9 and task.epoch==1
        assert db.get(Resource,'desktop').owner is None
        attempts=list(db.scalars(select(Attempt).where(Attempt.task_id==task_id)))
        assert len(attempts)==1 and attempts[0].finished_at is not None
        assert not list(db.scalars(select(Artifact)))
        assert all(n.read_at is None for n in db.scalars(select(Notification)))
    with pytest.raises(ValueError): run()


@pytest.mark.parametrize('fault',['running','pending','not-stopped','budget','regression','owner','epoch','lease','control','intent','artifact'])
def test_bad_evidence_keeps_original_state(service,case,fault):
    task_id,root,quarantine,session,guest,run=case
    if fault=='running': session['running']=True
    elif fault=='pending':guest['pendingCalls']=1
    elif fault=='not-stopped':guest['stopped']=False
    elif fault=='budget':guest['rawCalls']=31
    elif fault=='control':
        path=service.settings.root/'controls'/(task_id+'.json')
        v=json.loads(path.read_text());v['stopped']=False;path.write_text(json.dumps(v))
    elif fault=='intent': (root/'desktop-reconcile-intent.json').write_text('prior')
    else:
        with service.sessions.begin() as db:
            r=db.get(Resource,'desktop'); t=db.get(Task,task_id)
            if fault=='owner':r.owner='different'
            elif fault=='epoch':r.epoch+=1
            elif fault=='lease':r.expires_at=utcnow()+timedelta(seconds=60)
            elif fault=='regression':t.calls=10
            elif fault=='artifact':db.add(Artifact(task_id=task_id,name='document.txt',sha256='a'*64,bytes=1))
    with pytest.raises((ValueError,FileExistsError)):run()
    assert service.view(task_id)['status']=='RUNNING'
    assert quarantine.exists()
    if fault=='intent':assert (root/'desktop-reconcile-intent.json').read_text()=='prior'


@pytest.fixture
def recovery(service, case):
    task_id, root, quarantine, session, guest, finalize = case
    finalize()
    home = root/'home'; target = home/'profiles/desktop/cordis.patch.yml'
    target.parent.mkdir(parents=True, mode=0o700)
    target.write_bytes(b'active'); target.chmod(0o600)
    plan = dict(root=str(root), home=str(home), target=str(target),
                beforeSha256=hashlib.sha256(b'baseline').hexdigest())
    path=root/'profile-plan.json'; path.write_text(json.dumps(plan)); path.chmod(0o600)
    calls=[]
    def command(run, group, mode):
        assert run == root
        calls.append((group, mode))
        if mode=='restore':target.write_bytes(b'baseline')
    adapter=SimpleNamespace(service=service,settings=SimpleNamespace(
        node='/unused',official_home=home,cookie='/unused'),command=command)
    run=lambda:module.restore_interrupted_profile(service,task_id,
        shared_lock=quarantine.with_name('desktop-worker.lock'),adapter=adapter)
    return run,calls,adapter,target


def test_recovery_restores_only_original_profile(service, case, recovery):
    task_id,root,quarantine,session,guest,_=case
    run,calls,adapter,target=recovery
    original=quarantine.read_bytes()
    result=run()
    assert result['profileRestored'] and not result['guestShutdown'] and not result['workerRestarted']
    assert calls==[('app','stop-restore'),('profile','restore'),('app','start-restore')]
    assert quarantine.read_bytes()==original and target.read_bytes()==b'baseline'
    assert service.view(task_id)['status']=='UNVERIFIED'
    assert (root/'desktop-recovery-receipt.json').stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError): run()
    assert len(calls)==3


@pytest.mark.parametrize('fault',['running','pending','budget','evidence','owner','resource','attempt','prior-intent'])
def test_recovery_refuses_without_mutation(service, case, recovery, fault):
    task_id,root,quarantine,session,guest,_=case
    run,calls,adapter,target=recovery
    if fault=='running':session['running']=True
    elif fault=='pending':guest['pendingCalls']=1
    elif fault=='budget':guest['rawCalls']=10
    elif fault=='evidence':quarantine.write_text(json.dumps(dict(taskId=task_id,changed=True)))
    elif fault=='prior-intent':(root/'desktop-recovery-intent.json').write_text('original')
    else:
        with service.sessions.begin() as db:
            if fault=='owner':db.get(Task,task_id).owner='other'
            elif fault=='resource':db.get(Resource,'desktop').owner='other'
            elif fault=='attempt':db.scalar(select(Attempt).where(Attempt.task_id==task_id)).finished_at=None
    with pytest.raises((ValueError,FileExistsError)): run()
    assert calls==[] and target.read_bytes()==b'active' and quarantine.exists()


@pytest.mark.parametrize('failed_phase',['stop-restore','restore','start-restore'])
def test_recovery_failure_stops_without_replay(case,recovery,failed_phase):
    _,root,quarantine,_,_,_=case
    run,calls,adapter,target=recovery
    original=adapter.command
    def fail(run,group,mode):
        original(run,group,mode)
        if mode==failed_phase:raise RuntimeError('SECRET_SENTINEL')
    adapter.command=fail
    with pytest.raises(RuntimeError):run()
    count=len(calls)
    assert calls[-1][1]==failed_phase and quarantine.exists()
    assert not (root/'desktop-recovery-receipt.json').exists()
    assert 'SECRET_SENTINEL' not in (root/'desktop-recovery-failure.json').read_text()
    with pytest.raises(FileExistsError):run()
    assert len(calls)==count
