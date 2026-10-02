from datetime import timedelta
import hashlib
import json
from pathlib import Path
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from backend.control import write_control
from backend.models import Artifact, Attempt, Event, Resource, Task, Usage, utcnow


class Conflict(ValueError):
    pass


class NotFound(ValueError):
    pass


class TaskService:
    def __init__(self, sessions, settings):
        self.sessions, self.settings = sessions, settings

    def event(self, db, task, kind, **data):
        task.updated_at = utcnow()
        db.add(Event(task_id=task.id, kind=kind, data=data))

    def control(self, task, expires=None, stopped=False):
        if not task.owner:
            return
        return write_control(self.settings.root / 'controls' / (task.id + '.json'),
                             run_id='p2-' + task.id, epoch=task.epoch, owner=task.owner,
                             expires_at=(expires or utcnow()).timestamp() * 1000, stopped=stopped)

    def submit(self, payload, key):
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        with self.sessions.begin() as db:
            task_id = str(uuid.uuid4())
            created = db.execute(insert(Task).values(id=task_id, idempotency_key=key,
                request_sha256=digest, payload=payload, status='QUEUED', epoch=0, calls=0,
                created_at=utcnow(), updated_at=utcnow()).on_conflict_do_nothing(index_elements=['idempotency_key']).returning(Task.id)).scalar_one_or_none()
            task = db.scalar(select(Task).where(Task.idempotency_key == key))
            if task.request_sha256 != digest:
                raise Conflict('IDEMPOTENCY_BODY_CONFLICT')
            if created:
                self.event(db, task, 'submitted')
            return task.id, bool(created)

    def claim(self, owner):
        with self.sessions.begin() as db:
            resource = db.scalar(select(Resource).where(Resource.name == 'desktop').with_for_update(skip_locked=True))
            if resource is None:
                return None
            if resource.owner:
                if resource.expires_at and resource.expires_at > utcnow():
                    return None
                old = db.get(Task, resource.task_id, with_for_update=True)
                if old and old.status in ('RUNNING', 'STOP_REQUESTED'):
                    old.status, old.error_code = 'BLOCKED', 'OWNER_LEASE_EXPIRED'
                    self.control(old, stopped=True)
                    self.event(db, old, 'owner_expired')
                resource.owner, resource.task_id, resource.expires_at = None, None, None
            task = db.scalar(select(Task).where(Task.status == 'QUEUED').order_by(Task.created_at).with_for_update(skip_locked=True).limit(1))
            if task is None:
                return None
            resource.epoch += 1
            resource.owner, resource.task_id = owner, task.id
            resource.expires_at = utcnow() + timedelta(seconds=self.settings.lease_seconds)
            task.owner, task.epoch, task.status, task.error_code = owner, resource.epoch, 'RUNNING', None
            self.control(task, resource.expires_at)
            db.add(Attempt(task_id=task.id, owner=owner, epoch=task.epoch))
            self.event(db, task, 'claimed', epoch=task.epoch)
            db.flush()
            return task

    def heartbeat(self, task_id, owner, epoch):
        with self.sessions.begin() as db:
            resource = db.get(Resource, 'desktop', with_for_update=True)
            task = db.get(Task, task_id, with_for_update=True)
            if not task or resource.owner != owner or resource.task_id != task_id or resource.epoch != epoch or not resource.expires_at or resource.expires_at <= utcnow():
                raise Conflict('STALE_EXECUTION_OWNER')
            stop = task.status == 'STOP_REQUESTED'
            if task.status not in ('RUNNING', 'STOP_REQUESTED'):
                raise Conflict('TASK_NOT_RUNNING')
            resource.expires_at = utcnow() + timedelta(seconds=self.settings.lease_seconds)
            self.control(task, resource.expires_at, stopped=stop)
            return stop

    def stop(self, task_id):
        with self.sessions.begin() as db:
            task = db.get(Task, task_id, with_for_update=True)
            if task is None:
                raise NotFound('TASK_NOT_FOUND')
            if task.status in ('SUCCEEDED', 'FAILED', 'UNVERIFIED', 'STOPPED'):
                return task.status
            task.status = 'STOPPED' if task.status == 'QUEUED' else 'STOP_REQUESTED'
            self.control(task, stopped=True)
            self.event(db, task, 'stop_requested')
            return task.status

    def resume(self, task_id):
        with self.sessions.begin() as db:
            resource = db.get(Resource, 'desktop', with_for_update=True)
            task = db.get(Task, task_id, with_for_update=True)
            if task is None:
                raise NotFound('TASK_NOT_FOUND')
            if resource.task_id == task_id and resource.owner and resource.expires_at and resource.expires_at > utcnow():
                raise Conflict('OWNER_STILL_ACTIVE')
            if task.status not in ('STOPPED', 'BLOCKED', 'RUNNING', 'STOP_REQUESTED'):
                raise Conflict('TASK_NOT_RESUMABLE')
            # Same ID/session/ledger; worker reconciles any previous dispatch.
            task.status, task.error_code = 'QUEUED', None
            if resource.task_id == task_id:
                resource.owner, resource.task_id, resource.expires_at = None, None, None
            self.event(db, task, 'resume_requested', mode='reconcile_original_session')
            return task.status

    def record_prepared(self, task_id, owner, epoch, run_dir, session_id):
        with self.sessions.begin() as db:
            task = db.get(Task, task_id, with_for_update=True)
            if task.owner != owner or task.epoch != epoch or task.status not in ('RUNNING', 'STOP_REQUESTED'):
                raise Conflict('STALE_EXECUTION_OWNER')
            if task.session_id and task.session_id != session_id:
                raise Conflict('SESSION_ID_CHANGED')
            task.run_dir, task.session_id = str(run_dir), session_id
            self.event(db, task, 'prepared', session_id=session_id)

    def progress(self, task_id, owner, epoch, calls):
        with self.sessions.begin() as db:
            task = db.get(Task, task_id, with_for_update=True)
            if task.owner != owner or task.epoch != epoch or task.status not in ('RUNNING', 'STOP_REQUESTED'):
                raise Conflict('STALE_EXECUTION_OWNER')
            if calls < task.calls or calls > 30:
                raise Conflict('INVALID_BUDGET_PROGRESS')
            if calls != task.calls:
                task.calls = calls
                self.event(db, task, 'progress', raw_calls=calls)

    def checkpoint(self, task_id, owner, epoch, phase, evidence, *, business_progress=None):
        if phase not in ('prepared', 'activating', 'activated', 'starting', 'observing', 'verifying'):
            raise ValueError('INVALID_CHECKPOINT_PHASE')
        with self.sessions.begin() as db:
            resource = db.get(Resource, 'desktop', with_for_update=True)
            task = db.get(Task, task_id, with_for_update=True)
            if (not task or resource.owner != owner or resource.task_id != task_id
                    or resource.epoch != epoch or not resource.expires_at or resource.expires_at <= utcnow()
                    or task.status not in ('RUNNING', 'STOP_REQUESTED')):
                raise Conflict('STALE_EXECUTION_OWNER')
            if evidence['runId'] != 'p2-' + task_id or evidence['sessionId'] != task.session_id:
                raise Conflict('CHECKPOINT_IDENTITY_CHANGED')
            old = task.checkpoint
            if (type(evidence['used']) is not int or not task.calls <= evidence['used'] <= 30
                    or (old and evidence['auditBytes'] < old['evidence']['auditBytes'])):
                raise Conflict('CHECKPOINT_BUDGET_OR_AUDIT_REGRESSED')
            task.calls = evidence['used']
            task.checkpoint = {'phase': phase, 'epoch': epoch, 'at': utcnow().isoformat(), 'evidence': evidence}
            if business_progress is not None:
                task.checkpoint = {**task.checkpoint, 'businessProgress': business_progress}
            elif old and 'businessProgress' in old:
                task.checkpoint = {**task.checkpoint, 'businessProgress': old['businessProgress']}
            self.event(db, task, 'checkpoint', phase=phase, raw_calls=task.calls,
                       unresolved_calls=len(evidence['pending']))

    def import_audit(self, task_id, owner, epoch, rows):
        with self.sessions.begin() as db:
            task = db.get(Task, task_id, with_for_update=True)
            if task.owner != owner or task.epoch != epoch or task.status not in ('RUNNING', 'STOP_REQUESTED'):
                raise Conflict('STALE_EXECUTION_OWNER')
            for index, row in enumerate(rows):
                if row.get('runId') != 'p2-' + task_id or row.get('sessionId') != task.session_id:
                    raise Conflict('AUDIT_IDENTITY_CHANGED')
                if row['event'] not in ('dispatch', 'result', 'denied'):
                    continue
                # Metadata only: source audit remains the execution authority.
                allowed = ('callId', 'name', 'used', 'durationMs', 'outcome', 'errorCode', 'reason', 'artifact')
                data = {key: row[key] for key in allowed if key in row}
                db.execute(insert(Event).values(task_id=task_id, external_id='audit:' + str(index),
                    kind='tool_' + row['event'], data=data, created_at=utcnow()).on_conflict_do_nothing(index_elements=['task_id', 'external_id']))

    def finish(self, task_id, owner, epoch, status, *, result=None, error_code=None):
        if status not in ('SUCCEEDED', 'FAILED', 'BLOCKED', 'UNVERIFIED', 'STOPPED'):
            raise ValueError('invalid terminal status')
        with self.sessions.begin() as db:
            resource = db.get(Resource, 'desktop', with_for_update=True)
            task = db.get(Task, task_id, with_for_update=True)
            if resource.owner != owner or resource.task_id != task_id or resource.epoch != epoch or not resource.expires_at or resource.expires_at <= utcnow():
                raise Conflict('STALE_EXECUTION_OWNER')
            if status == 'SUCCEEDED':
                if not result or result.get('status') != 'SUCCEEDED' or result.get('sessionId') != task.session_id:
                    raise Conflict('INDEPENDENT_VERIFICATION_REQUIRED')
                for name, digest in result['artifacts'].items():
                    if name not in ('report.json', 'report.md'):
                        raise Conflict('INVALID_ARTIFACT')
                    path = Path(task.run_dir) / 'workspace' / name
                    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                        raise Conflict('ARTIFACT_CHANGED')
                    db.add(Artifact(task_id=task_id, name=name, sha256=digest, bytes=path.stat().st_size))
            if result and result.get('usage'):
                db.merge(Usage(task_id=task_id, data=result['usage']))
            task.status, task.error_code = status, error_code
            self.control(task, stopped=True)
            self.event(db, task, 'finished', status=status, error_code=error_code)
            attempt = db.scalar(select(Attempt).where(Attempt.task_id == task_id, Attempt.epoch == epoch))
            if attempt:
                attempt.finished_at = utcnow()
            resource.owner, resource.task_id, resource.expires_at = None, None, None

    def view(self, task_id):
        with self.sessions() as db:
            task = db.get(Task, task_id)
            if task is None:
                raise NotFound('TASK_NOT_FOUND')
            usage = db.get(Usage, task_id)
            return {'id': task.id, 'status': task.status, 'error_code': task.error_code,
                    'session_id': task.session_id, 'budget': {'used': task.calls, 'limit': 30},
                    'checkpoint': {k: task.checkpoint[k] for k in ('phase', 'epoch', 'at')} if task.checkpoint else None,
                    'created_at': task.created_at.isoformat(), 'updated_at': task.updated_at.isoformat(),
                    'usage': usage.data if usage else None,
                    'artifacts': [{'name': a.name, 'sha256': a.sha256, 'bytes': a.bytes} for a in db.scalars(select(Artifact).where(Artifact.task_id == task_id))]}
