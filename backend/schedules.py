"""Two-phase bounded scheduling. Collection never holds the plan database lock."""
from datetime import datetime, timedelta
import re
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from backend.batches import BatchService, digest
from backend.models import Occurrence, Schedule, utcnow
from backend.schemas import ScheduleSubmission
from backend.service import Conflict, NotFound

DAY = timedelta(days=1)
GRACE = timedelta(minutes=10)
PREPARE_LEASE = timedelta(seconds=60)


class ScheduleService:
    def __init__(self, task_service, *, collect, permitted, clock=utcnow):
        self.sessions = task_service.sessions
        self.batches = BatchService(task_service)
        self.collect, self.permitted, self.clock = collect, permitted, clock

    def create(self, body, key):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', key):
            raise ValueError('INVALID_IDEMPOTENCY_KEY')
        config = ScheduleSubmission.model_validate(body).model_dump(mode='json')
        checksum = digest(config)
        with self.sessions.begin() as db:
            identity = str(uuid.uuid4())
            created = db.execute(insert(Schedule).values(id=identity, idempotency_key=key,
                request_sha256=checksum, config=config, status='ACTIVE',
                next_at=datetime.fromisoformat(config['startAt']), occurrences=0,
                last_commit=config['baselineCommit'], created_at=self.clock()).on_conflict_do_nothing(
                index_elements=['idempotency_key']).returning(Schedule.id)).scalar_one_or_none()
            plan = db.scalar(select(Schedule).where(Schedule.idempotency_key == key))
            if plan.request_sha256 != checksum:
                raise Conflict('IDEMPOTENCY_BODY_CONFLICT')
            if created and not self.clock() <= plan.next_at <= self.clock() + DAY * 7:
                raise ValueError('FIRST_OCCURRENCE_MUST_BE_WITHIN_NEXT_SEVEN_DAYS')
            return plan.id, bool(created)

    def _locked(self, db, identity):
        plan = db.scalar(select(Schedule).where(Schedule.id == identity).with_for_update())
        if plan is None: raise NotFound('SCHEDULE_NOT_FOUND')
        return plan

    @staticmethod
    def _settle(plan):
        if plan.status == 'ACTIVE' and plan.occurrences >= plan.config['runs']:
            plan.status = 'EXHAUSTED'

    def pause(self, identity):
        with self.sessions.begin() as db:
            plan = self._locked(db, identity)
            plan.status = 'PAUSED'
            for occurrence in db.scalars(select(Occurrence).where(Occurrence.schedule_id == identity,
                                                                  Occurrence.status == 'PREPARING')):
                occurrence.status = 'CANCELLED'
        return self.view(identity)

    def view(self, identity):
        with self.sessions() as db:
            plan = db.get(Schedule, identity)
            if plan is None: raise NotFound('SCHEDULE_NOT_FOUND')
            rows = list(db.scalars(select(Occurrence).where(Occurrence.schedule_id == identity)
                                   .order_by(Occurrence.due_at)))
            return {'id': plan.id, 'status': plan.status, 'config': plan.config,
                    'next_at': plan.next_at.isoformat(), 'occurrences': plan.occurrences,
                    'observation_end': (datetime.fromisoformat(plan.config['startAt']) + DAY * plan.config['runs']).isoformat(),
                    'items': [{'id': r.id, 'due_at': r.due_at.isoformat(), 'status': r.status,
                               'batch_id': r.batch_id, 'source_sha256': r.source_sha256} for r in rows]}

    def prepare(self, identity):
        with self.sessions.begin() as db:
            plan = self._locked(db, identity)
            now = self.clock()
            pending = db.scalar(select(Occurrence).where(Occurrence.schedule_id == identity,
                                                          Occurrence.status == 'PREPARING'))
            if pending:
                if now < pending.prepare_deadline: return {'status': 'PREPARING'}
                pending.status = 'PREPARATION_EXPIRED'
                self._settle(plan)
            if plan.status != 'ACTIVE': return {'status': plan.status}
            if plan.occurrences >= plan.config['runs']:
                self._settle(plan)
                return {'status': plan.status}
            if now < plan.next_at: return {'status': 'NOT_DUE'}
            missed = now > plan.next_at + GRACE
            if not missed and not self.permitted(plan.id, plan.next_at, now):
                return {'status': 'WAITING_PERMISSION'}
            occurrence = Occurrence(id=str(uuid.uuid4()), schedule_id=identity, due_at=plan.next_at,
                status='MISSED' if missed else 'PREPARING', created_at=now,
                prepare_deadline=None if missed else min(now + PREPARE_LEASE, plan.next_at + GRACE))
            db.add(occurrence)
            plan.occurrences += 1
            plan.next_at += DAY
            if missed: self._settle(plan)
            return {'id': occurrence.id, 'status': occurrence.status, 'scheduleId': identity,
                    'dueAt': occurrence.due_at, 'config': dict(plan.config), 'lastCommit': plan.last_commit}

    def finish_preparation(self, ticket, snapshot=None, source_error=False):
        with self.sessions.begin() as db:
            plan = self._locked(db, ticket['scheduleId'])
            occurrence = db.get(Occurrence, ticket['id'])
            if occurrence is None or occurrence.schedule_id != plan.id or occurrence.due_at != ticket['dueAt']:
                raise Conflict('OCCURRENCE_IDENTITY_CHANGED')
            if occurrence.status != 'PREPARING': return {'status': occurrence.status, 'id': occurrence.id}
            now = self.clock()
            if plan.status != 'ACTIVE': occurrence.status = 'CANCELLED'
            elif now >= occurrence.prepare_deadline: occurrence.status = 'PREPARATION_EXPIRED'
            elif source_error: occurrence.status = 'SOURCE_ERROR'
            elif not self.permitted(plan.id, occurrence.due_at, now): occurrence.status = 'PERMISSION_REVOKED'
            else:
                if (not isinstance(snapshot, list) or len(snapshot) != 2 or
                        [s['workflow'] for s in snapshot] != ['project-changes', 'task-operations']):
                    raise ValueError('EXACT_TWO_WORKFLOW_SNAPSHOTS_REQUIRED')
                project = snapshot[0]['source']
                if project['fromExclusive'] != plan.last_commit or not re.fullmatch('[0-9a-f]{40}', project['toInclusive']):
                    raise Conflict('PROJECT_SOURCE_IDENTITY_CHANGED')
                operations = snapshot[1]['source']
                if (datetime.fromisoformat(operations['fromInclusive']) != occurrence.due_at - DAY or
                        datetime.fromisoformat(operations['toExclusive']) != occurrence.due_at):
                    raise Conflict('OPERATIONS_WINDOW_CHANGED')
                body = {'tasks': [{**source['payload'], 'inputMode': 'aggregate'} for source in snapshot]}
                batch, created = self.batches.submit_in_transaction(db, body, 'schedule_' + occurrence.id)
                if not created: raise Conflict('UNEXPECTED_PREEXISTING_BATCH')
                occurrence.source, occurrence.source_sha256 = snapshot, digest(snapshot)
                occurrence.batch_id, occurrence.status = batch, 'SUBMITTED'
                plan.last_commit = project['toInclusive']
            self._settle(plan)
            return {'id': occurrence.id, 'status': occurrence.status, 'batch_id': occurrence.batch_id}

    def tick(self, identity):
        ticket = self.prepare(identity)
        if ticket['status'] != 'PREPARING' or 'id' not in ticket: return ticket
        try:
            snapshot = self.collect(ticket)
        except Exception:
            # Do not expose arbitrary source error text or silently recapture different input.
            return self.finish_preparation(ticket, source_error=True)
        try:
            return self.finish_preparation(ticket, snapshot=snapshot)
        except (ValueError, KeyError, TypeError, IndexError):
            return self.finish_preparation(ticket, source_error=True)
