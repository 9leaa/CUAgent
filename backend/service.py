from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import uuid
from sqlalchemy import and_, or_, select, func
import time
from sqlalchemy.dialects.postgresql import insert
from backend.control import write_control
from backend.desktop_contract import DesktopSubmission
from backend.artifact_contract import artifact_names
from backend.models import Artifact, Attempt, Event, Notification, Resource, Task, Usage, utcnow


class Conflict(ValueError):
    pass


class NotFound(ValueError):
    pass


class TaskService:
    def __init__(self, sessions, settings):
        self.sessions, self.settings = sessions, settings

    def event(self, db, task, kind, **data):
        task.updated_at = utcnow()
        event = Event(task_id=task.id, kind=kind, data=data)
        db.add(event)
        if kind in ('finished', 'stop_requested', 'owner_expired') and task.status in (
                'SUCCEEDED', 'FAILED', 'BLOCKED', 'UNVERIFIED', 'STOPPED'):
            db.flush()
            db.add(Notification(event_id=event.id, task_id=task.id, status=task.status,
                                error_code=task.error_code, created_at=task.updated_at))

    def control(self, task, expires=None, stopped=False):
        if not task.owner:
            return
        return write_control(self.settings.root / 'controls' / (task.id + '.json'),
                             run_id='p2-' + task.id, epoch=task.epoch, owner=task.owner,
                             expires_at=(expires or utcnow()).timestamp() * 1000, stopped=stopped)

    def submit(self, payload, key):
        if 'kind' in payload:
            payload = DesktopSubmission.model_validate(payload).model_dump(mode='json')
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        with self.sessions.begin() as db:
            task_id = str(uuid.uuid4())
            created = db.execute(insert(Task).values(id=task_id, idempotency_key=key,
                request_sha256=digest, payload=payload, status='QUEUED', epoch=0, calls=0,
                release_at=datetime.fromisoformat(payload['releaseAt']) if payload.get('releaseAt') else None,
                created_at=utcnow(), updated_at=utcnow()).on_conflict_do_nothing(index_elements=['idempotency_key']).returning(Task.id)).scalar_one_or_none()
            task = db.scalar(select(Task).where(Task.idempotency_key == key))
            if task.request_sha256 != digest:
                raise Conflict('IDEMPOTENCY_BODY_CONFLICT')
            if created:
                self.event(db, task, 'submitted')
            return task.id, bool(created)

    def claim(self, owner, *, kind='daily-report'):
        if kind not in ('daily-report', 'desktop-textedit'):
            raise ValueError('UNSUPPORTED_TASK_KIND')
        # Missing discriminator means legacy report, not JSON null or unknown.
        selector = (~Task.payload.has_key('kind') if kind == 'daily-report' else
                    Task.payload['kind'].astext == 'desktop-textedit')
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
            task = db.scalar(select(Task).where(selector, or_(Task.status == 'QUEUED',
                and_(Task.status == 'WAITING_RELEASE', Task.release_at <= utcnow())))
                .order_by(Task.created_at).with_for_update(skip_locked=True).limit(1))
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

    def heartbeat(self, task_id, owner, epoch, *, dispatch_stopped=False):
        with self.sessions.begin() as db:
            resource = db.get(Resource, 'desktop', with_for_update=True)
            task = db.get(Task, task_id, with_for_update=True)
            if not task or resource.owner != owner or resource.task_id != task_id or resource.epoch != epoch or not resource.expires_at or resource.expires_at <= utcnow():
                raise Conflict('STALE_EXECUTION_OWNER')
            stop = task.status == 'STOP_REQUESTED'
            if task.status not in ('RUNNING', 'STOP_REQUESTED'):
                raise Conflict('TASK_NOT_RUNNING')
            resource.expires_at = utcnow() + timedelta(seconds=self.settings.lease_seconds)
            self.control(task, resource.expires_at, stopped=stop or dispatch_stopped)
            return stop

    def desktop_authority(self, task_id, owner, epoch, *, clock=time.monotonic):
        # Start before querying/locking: DB latency shortens rather than extends
        # the monotonic deadline. No network I/O may occur inside this transaction.
        started = clock()
        with self.sessions.begin() as db:
            resource = db.get(Resource, 'desktop', with_for_update=True)
            task = db.get(Task, task_id, with_for_update=True)
            now = db.scalar(select(func.clock_timestamp()))
            if (resource is None or task is None or task.payload.get('kind') != 'desktop-textedit'
                    or task.status != 'RUNNING' or task.owner != owner or task.epoch != epoch
                    or resource.owner != owner or resource.epoch != epoch or resource.task_id != task_id
                    or resource.expires_at is None or resource.expires_at <= now):
                raise Conflict('DESKTOP_EXECUTION_AUTHORITY_UNAVAILABLE')
            return started + min((resource.expires_at - now).total_seconds(), self.settings.lease_seconds)

    def stop(self, task_id):
        with self.sessions.begin() as db:
            task = db.get(Task, task_id, with_for_update=True)
            if task is None:
                raise NotFound('TASK_NOT_FOUND')
            if task.status in ('SUCCEEDED', 'FAILED', 'UNVERIFIED', 'STOPPED'):
                return task.status
            task.status = 'STOPPED' if task.status in ('QUEUED', 'WAITING_RELEASE') else 'STOP_REQUESTED'
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
            if 'kind' in task.payload:
                attempted = db.scalar(select(Attempt.id).where(Attempt.task_id == task.id).limit(1))
                if task.payload['kind'] != 'desktop-textedit' or attempted is not None or task.session_id or task.calls or task.run_dir or task.checkpoint:
                    raise Conflict('DESKTOP_RECOVERY_REQUIRES_VERIFIED_ADAPTER')
            # Same ID/session/ledger; worker reconciles any previous dispatch.
            task.status = 'WAITING_RELEASE' if task.release_at and task.release_at > utcnow() and task.checkpoint else 'QUEUED'
            task.error_code = None
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
                allowed = artifact_names(task.payload)
                if not allowed:
                    raise Conflict('UNKNOWN_TASK_ARTIFACT_TYPE')
                expected = None
                if task.payload.get('kind') == 'desktop-textedit':
                    if task.status != 'RUNNING':
                        raise Conflict('DESKTOP_TASK_NO_LONGER_RUNNING')
                    if result.get('kind') != 'desktop-textedit' or set(result.get('artifacts', {})) != set(allowed):
                        raise Conflict('DESKTOP_ARTIFACT_SET_REQUIRED')
                    document = DesktopSubmission.model_validate(task.payload).expected_document()
                    expected = {'document.txt': document, 'result.txt': document + b'\n'}
                for name, digest in result['artifacts'].items():
                    if name not in allowed:
                        raise Conflict('INVALID_ARTIFACT')
                    path = Path(task.run_dir) / 'workspace' / name
                    if path.is_symlink():
                        raise Conflict('ARTIFACT_CHANGED')
                    if expected is not None and not path.resolve().is_relative_to(self.settings.root):
                        raise Conflict('ARTIFACT_PATH_CHANGED')
                    data = path.read_bytes()
                    if hashlib.sha256(data).hexdigest() != digest:
                        raise Conflict('ARTIFACT_CHANGED')
                    if expected is not None and data != expected[name]:
                        raise Conflict('DESKTOP_ARTIFACT_CONTENT_MISMATCH')
                    db.add(Artifact(task_id=task_id, name=name, sha256=digest, bytes=len(data)))
            if result and result.get('usage'):
                db.merge(Usage(task_id=task_id, data=result['usage']))
            task.status, task.error_code = status, error_code
            self.control(task, stopped=True)
            self.event(db, task, 'finished', status=status, error_code=error_code)
            attempt = db.scalar(select(Attempt).where(Attempt.task_id == task_id, Attempt.epoch == epoch))
            if attempt:
                attempt.finished_at = utcnow()
            resource.owner, resource.task_id, resource.expires_at = None, None, None

    def wait_for_release(self, task_id, owner, epoch, *, usage=None):
        with self.sessions.begin() as db:
            resource = db.get(Resource, 'desktop', with_for_update=True)
            task = db.get(Task, task_id, with_for_update=True)
            if (not task or resource.owner != owner or resource.task_id != task_id or resource.epoch != epoch
                    or not resource.expires_at or resource.expires_at <= utcnow() or task.status != 'RUNNING'):
                raise Conflict('STALE_EXECUTION_OWNER')
            if not task.release_at or not task.checkpoint or task.checkpoint['evidence']['pending']:
                raise Conflict('VERIFIED_RELEASE_CHECKPOINT_REQUIRED')
            task.status = 'WAITING_RELEASE'
            if usage:
                db.merge(Usage(task_id=task_id, data=usage))
            self.control(task, stopped=True)
            self.event(db, task, 'waiting_release', release_at=task.release_at.isoformat())
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
            return {'id': task.id, 'kind': task.payload.get('kind', 'daily-report'),
                    'status': task.status, 'error_code': task.error_code,
                    'session_id': task.session_id, 'budget': {'used': task.calls, 'limit': 30},
                    'release_at': task.release_at.isoformat() if task.release_at else None,
                    'checkpoint': {k: task.checkpoint[k] for k in ('phase', 'epoch', 'at')} if task.checkpoint else None,
                    'business_progress': task.checkpoint.get('businessProgress') if task.checkpoint else None,
                    'created_at': task.created_at.isoformat(), 'updated_at': task.updated_at.isoformat(),
                    'usage': usage.data if usage else None,
                    'artifacts': [{'name': a.name, 'sha256': a.sha256, 'bytes': a.bytes} for a in db.scalars(select(Artifact).where(Artifact.task_id == task_id))]}
