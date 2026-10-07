"""Trusted local failure finalization and profile recovery; never dispatches."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import uuid
from sqlalchemy import select
from backend.desktop_client import DesktopControlClient
from backend.desktop_collect import private_path, save_exclusive
from backend.desktop_session import DesktopSessionClient
from backend.desktop_usage import desktop_usage
from backend.handoff_operator import read_private
from backend.models import Artifact, Attempt, Resource, Task, Usage, utcnow
from backend.service import Conflict


def require(condition):
    if not condition:
        raise Conflict('DESKTOP_RECONCILIATION_UNCONFIRMED')


def finalize_interrupted(service, task_id, *, shared_lock, node, official_home, cookie):
    require(str(uuid.UUID(task_id)) == task_id)
    shared_lock = private_path(Path(shared_lock), directory=False)
    quarantine = shared_lock.with_name(shared_lock.name + '.quarantine')
    root = private_path(service.settings.root / ('p2-' + task_id), directory=True)
    inputs = {}
    def read(path):
        raw = read_private(path, 65536)
        inputs[Path(path)] = raw
        return json.loads(raw)
    with os.fdopen(os.open(shared_lock, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(os.fstat(lock.fileno()).st_ino == shared_lock.stat().st_ino)
        require(read(quarantine).get('taskId') == task_id)
        ready = read(root / 'guest-private-receipt.json')
        tunnel = read(root / 'desktop-tunnel-selection.json')
        binding = ready['binding']
        require(binding == tunnel['binding'] and binding.get('runId') == root.name
                and type(binding.get('epoch')) is int and binding['epoch'] > 0
                and type(binding.get('version')) is int and binding['version'] == 1)
        control = read(service.settings.root / 'controls' / (task_id + '.json'))
        require(all(control.get(k) == v for k, v in binding.items())
                and type(control.get('epoch')) is int and control.get('stopped') is True)
        session_binding = read(root / 'desktop-session-binding.json')
        session_id = session_binding['sessionId']
        require(session_binding.get('runId') == root.name and session_binding.get('cwd') == str(root / 'workspace'))
        client = DesktopControlClient(port=tunnel['hostPort'], token=ready['controlToken'],
            run_id=root.name, owner=binding['owner'], epoch=binding['epoch'])
        session = DesktopSessionClient(root=root, session_id=session_id, node=node,
            official_home=official_home, cookie=cookie).inspect()
        guest = client.status()
        require(session.get('sessionId') == session_id and session.get('terminal') is True
                and session.get('running') is False and session.get('userMessages') == 1
                and session.get('promptObserved') is True)
        require(guest.get('stopped') is True and guest.get('pendingCalls') == 0
                and type(guest.get('rawCalls')) is int and 0 <= guest['rawCalls'] <= 30)
        usage = desktop_usage(root, session_id)
        # Do not renew stale authority. This transaction can only record failure.
        with service.sessions.begin() as db:
            resource = db.get(Resource, 'desktop', with_for_update=True)
            task = db.get(Task, task_id, with_for_update=True)
            require(task is not None and resource is not None)
            require(task.payload.get('kind') in ('desktop-textedit', 'project-handoff')
                    and task.status in ('RUNNING', 'STOP_REQUESTED', 'BLOCKED')
                    and task.session_id == session_id and task.run_dir == str(root)
                    and task.owner == binding['owner'] and task.epoch == binding['epoch']
                    and 0 <= task.calls <= guest['rawCalls'])
            require(resource.task_id == task_id and resource.owner == task.owner
                    and resource.epoch == task.epoch and resource.expires_at is not None
                    and resource.expires_at <= utcnow())
            attempts = list(db.scalars(select(Attempt).where(Attempt.task_id == task_id)))
            require(len(attempts) == 1 and attempts[0].owner == task.owner
                    and attempts[0].epoch == task.epoch and attempts[0].finished_at is None)
            require(db.scalar(select(Artifact.id).where(Artifact.task_id == task_id).limit(1)) is None)
            require(all(read_private(path, 65536) == raw for path, raw in inputs.items()))
            proof = dict(version=1, taskId=task_id, sessionId=session_id, binding=binding,
                previousStatus=task.status, status='UNVERIFIED', rawCalls=guest['rawCalls'],
                sessionTerminal=True, guestStopped=True, pendingCalls=0,
                evidenceHashes={str(p): hashlib.sha256(raw).hexdigest() for p, raw in inputs.items()},
                usage=usage, profileRestored=False, quarantineRetained=True)
            raw = json.dumps(proof, sort_keys=True).encode()
            save_exclusive(root / 'desktop-reconcile-intent.json', raw)
            task.status, task.error_code = 'UNVERIFIED', 'DESKTOP_INTERRUPTED_RECONCILED'
            task.calls = guest['rawCalls']
            attempts[0].finished_at = utcnow()
            db.merge(Usage(task_id=task_id, data=usage))
            service.event(db, task, 'finished', status=task.status, error_code=task.error_code,
                          reconciliationSha256=hashlib.sha256(raw).hexdigest())
            resource.owner, resource.task_id, resource.expires_at = None, None, None
        return dict(taskId=task_id, status='UNVERIFIED', quarantineRetained=True, profileRestored=False)


def restore_interrupted_profile(service, task_id, *, shared_lock, adapter):
    """One-shot original profile recovery only; quarantine and guest stay intact."""
    require(str(uuid.UUID(task_id)) == task_id and adapter.service is service)
    shared_lock = private_path(Path(shared_lock), directory=False)
    quarantine = shared_lock.with_name(shared_lock.name + '.quarantine')
    root = private_path(service.settings.root / ('p2-' + task_id), directory=True)
    settings = adapter.settings
    with os.fdopen(os.open(shared_lock, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(os.fstat(lock.fileno()).st_ino == shared_lock.stat().st_ino)
        original_quarantine = read_private(quarantine, 65536)
        require(json.loads(original_quarantine).get('taskId') == task_id)
        proof_raw = read_private(root / 'desktop-reconcile-intent.json', 65536)
        proof = json.loads(proof_raw)
        require(proof['taskId'] == task_id and proof['status'] == 'UNVERIFIED')
        binding, session_id = proof['binding'], proof['sessionId']
        expected_paths = {quarantine, root/'guest-private-receipt.json',
            root/'desktop-tunnel-selection.json', root/'desktop-session-binding.json',
            service.settings.root/'controls'/(task_id+'.json')}
        require(set(proof['evidenceHashes']) == {str(p) for p in expected_paths})
        require(all(hashlib.sha256(read_private(p, 65536)).hexdigest() == proof['evidenceHashes'][str(p)]
                    for p in expected_paths))
        ready = json.loads(read_private(root/'guest-private-receipt.json', 65536))
        tunnel = json.loads(read_private(root/'desktop-tunnel-selection.json', 65536))
        require(ready['binding'] == tunnel['binding'] == binding and binding['runId'] == root.name)
        client = DesktopControlClient(port=tunnel['hostPort'], token=ready['controlToken'],
            run_id=root.name, owner=binding['owner'], epoch=binding['epoch'])
        session = DesktopSessionClient(root=root, session_id=session_id, node=settings.node,
            official_home=settings.official_home, cookie=settings.cookie).inspect()
        require(session.get('sessionId') == session_id and session.get('terminal') is True
                and session.get('running') is False and session.get('userMessages') == 1
                and session.get('promptObserved') is True)
        def stopped():
            guest = client.status()
            require(guest.get('stopped') is True and guest.get('pendingCalls') == 0
                    and type(guest.get('rawCalls')) is int and 0 <= guest['rawCalls'] <= 30
                    and guest['rawCalls'] == proof['rawCalls'])
        stopped()
        with service.sessions() as db:
            task = db.get(Task, task_id)
            resource = db.get(Resource, 'desktop')
            require(task is not None and resource is not None and resource.owner is None
                    and resource.task_id is None and task.status == 'UNVERIFIED'
                    and task.error_code == 'DESKTOP_INTERRUPTED_RECONCILED'
                    and task.owner == binding['owner'] and task.epoch == binding['epoch']
                    and task.session_id == session_id and task.run_dir == str(root)
                    and task.calls == proof['rawCalls'])
            require(db.scalar(select(Task.id).where(Task.status.in_(
                ['QUEUED', 'WAITING_RELEASE', 'RUNNING', 'STOP_REQUESTED'])).limit(1)) is None)
            attempts = list(db.scalars(select(Attempt).where(Attempt.task_id == task_id)))
            require(len(attempts) == 1 and attempts[0].finished_at is not None
                    and attempts[0].owner == task.owner and attempts[0].epoch == task.epoch)
            require(db.scalar(select(Artifact.id).where(Artifact.task_id == task_id).limit(1)) is None)
        plan = json.loads(read_private(root/'profile-plan.json', 65536))
        target = Path(settings.official_home)/'profiles/desktop/cordis.patch.yml'
        require(plan['root'] == str(root) and plan['home'] == str(settings.official_home)
                and plan['target'] == str(target))
        save_exclusive(root/'desktop-recovery-intent.json', json.dumps(dict(taskId=task_id,
            sessionId=session_id, binding=binding, reconciliationSha256=hashlib.sha256(proof_raw).hexdigest(),
            quarantineRetained=True, applicationMayRemain=True)).encode())
        stage = 'stop-restore'
        try:
            for group, stage in [('app','stop-restore'), ('profile','restore'), ('app','start-restore')]:
                adapter.command(root, group, stage)
            require(hashlib.sha256(read_private(target, 1048576)).hexdigest() == plan['beforeSha256'])
            stopped()
            require(read_private(quarantine, 65536) == original_quarantine)
            result = dict(taskId=task_id, profileRestored=True, quarantineRetained=True,
                          applicationMayRemain=True, guestShutdown=False, workerRestarted=False)
            save_exclusive(root/'desktop-recovery-receipt.json', json.dumps(result).encode())
            return result
        except Exception:
            save_exclusive(root/'desktop-recovery-failure.json', json.dumps(dict(
                taskId=task_id, phase=stage, result='UNCONFIRMED', quarantineRetained=True)).encode())
            raise
