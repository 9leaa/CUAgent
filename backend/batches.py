"""Batch persistence only; each task retains its own execution and safety boundary."""
from datetime import datetime
import hashlib
import json
import re
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from backend.models import Batch, BatchItem, Task, utcnow
from backend.schemas import BatchSubmission
from backend.service import Conflict, NotFound


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


class BatchService:
    def __init__(self, task_service):
        self.tasks = task_service
        self.sessions = task_service.sessions

    def submit(self, body, key):
        try:
            with self.sessions.begin() as db:
                return self.submit_in_transaction(db, body, key)
        except IntegrityError as error:
            raise Conflict('BATCH_INSERT_CONFLICT') from error

    def submit_in_transaction(self, db, body, key):
        """Caller owns transaction; scheduler records and child tasks commit together."""
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', key):
            raise ValueError('INVALID_IDEMPOTENCY_KEY')
        payload = BatchSubmission.model_validate(body).model_dump(mode='json', exclude_none=True)
        checksum = digest(payload)
        identity = str(uuid.uuid4())
        created = db.execute(insert(Batch).values(id=identity, idempotency_key=key,
            request_sha256=checksum, created_at=utcnow()).on_conflict_do_nothing(
            index_elements=['idempotency_key']).returning(Batch.id)).scalar_one_or_none()
        batch = db.scalar(select(Batch).where(Batch.idempotency_key == key))
        if batch.request_sha256 != checksum:
            raise Conflict('IDEMPOTENCY_BODY_CONFLICT')
        if created:
            for position, item in enumerate(payload['tasks']):
                task = Task(id=str(uuid.uuid4()), idempotency_key=f'batch_{identity}_{position}',
                            request_sha256=digest(item), payload=item, status='QUEUED', epoch=0, calls=0,
                            release_at=datetime.fromisoformat(item['releaseAt']) if item.get('releaseAt') else None)
                db.add(task)
                db.flush()
                self.tasks.event(db, task, 'submitted', batch_id=identity, position=position)
                db.add(BatchItem(batch_id=identity, task_id=task.id, position=position))
        return batch.id, bool(created)

    def task_ids(self, identity):
        with self.sessions() as db:
            if db.get(Batch, identity) is None:
                raise NotFound('BATCH_NOT_FOUND')
            return list(db.scalars(select(BatchItem.task_id).where(BatchItem.batch_id == identity)
                                   .order_by(BatchItem.position)))

    def view(self, identity):
        items = [self.tasks.view(task_id) for task_id in self.task_ids(identity)]
        states = {item['status'] for item in items}
        if states == {'SUCCEEDED'}:
            state = 'SUCCEEDED'
        elif states == {'STOPPED'}:
            state = 'STOPPED'
        elif states == {'QUEUED'}:
            state = 'QUEUED'
        elif states & {'QUEUED', 'RUNNING', 'WAITING_RELEASE', 'STOP_REQUESTED'}:
            state = 'IN_PROGRESS'
        else:
            state = 'COMPLETED_WITH_ERRORS'
        return {'id': identity, 'status': state, 'items': items}

    def stop(self, identity):
        # Per-task durable stop: if interrupted, repeating this request completes the remainder.
        # No resume/replay and no claim that several external stop effects are one transaction.
        for task_id in self.task_ids(identity):
            self.tasks.stop(task_id)
        return self.view(identity)
