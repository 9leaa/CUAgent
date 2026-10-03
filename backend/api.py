import hashlib
import hmac
from pathlib import Path
import re
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select, text
from backend.config import Settings
from backend.db import database
from backend.models import Artifact, Event, Schedule, Task
from backend.schemas import BatchSubmission, ScheduleSubmission, Submission
from backend.desktop_contract import DesktopSubmission
from backend.batches import BatchService
from backend.notifications import Inbox
from backend.schedule_runtime import runtime_service
from backend.service import Conflict, NotFound, TaskService


def create_app(settings):
    engine, sessions = database(settings.database_url)
    service = TaskService(sessions, settings)
    batches = BatchService(service)
    inbox = Inbox(sessions)
    schedules = runtime_service(service)
    app = FastAPI(title='CUAgent Tasks', docs_url=None, redoc_url=None)
    app.state.service = service

    def authenticated(authorization: str = Header(default='')):
        if not hmac.compare_digest(authorization, 'Bearer ' + settings.api_token):
            raise HTTPException(401, 'AUTH_REQUIRED')

    @app.middleware('http')
    async def body_limit(request: Request, call_next):
        if request.method == 'POST':
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                if size > 262144:
                    return JSONResponse({'detail': 'REQUEST_TOO_LARGE'}, status_code=413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        return await call_next(request)

    @app.exception_handler(Conflict)
    async def conflict(_request, error):
        return JSONResponse({'detail': str(error)}, status_code=409)

    @app.exception_handler(NotFound)
    async def missing(_request, error):
        return JSONResponse({'detail': str(error)}, status_code=404)

    @app.get('/health')
    def health():
        with sessions() as db:
            db.execute(text('SELECT 1'))
        return {'status': 'ready'}

    @app.post('/tasks', dependencies=[Depends(authenticated)])
    def submit(body: Submission, idempotency_key: str = Header()):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', idempotency_key):
            raise HTTPException(422, 'INVALID_IDEMPOTENCY_KEY')
        task_id, created = service.submit(body.model_dump(mode='json', exclude_none=True), idempotency_key)
        return JSONResponse({'id': task_id, 'created': created}, status_code=201 if created else 200)

    @app.post('/desktop-tasks', dependencies=[Depends(authenticated)])
    def submit_desktop(body: DesktopSubmission, idempotency_key: str = Header()):
        if not settings.desktop_tasks_enabled:
            raise HTTPException(503, 'DESKTOP_TASK_EXECUTION_NOT_ENABLED')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', idempotency_key):
            raise HTTPException(422, 'INVALID_IDEMPOTENCY_KEY')
        task_id, created = service.submit(body.model_dump(mode='json'), idempotency_key)
        return JSONResponse({'id': task_id, 'created': created}, status_code=201 if created else 200)

    @app.get('/tasks', dependencies=[Depends(authenticated)])
    def listing(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
        with sessions() as db:
            ids = list(db.scalars(select(Task.id).order_by(Task.created_at, Task.id).offset(offset).limit(limit)))
        return {'items': [service.view(task_id) for task_id in ids]}

    @app.post('/schedules', dependencies=[Depends(authenticated)])
    def create_schedule(body: ScheduleSubmission, idempotency_key: str = Header()):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', idempotency_key):
            raise HTTPException(422, 'INVALID_IDEMPOTENCY_KEY')
        try:
            identity, created = schedules.create(body.model_dump(mode='json'), idempotency_key)
        except Conflict:
            raise
        except ValueError:
            raise HTTPException(422, 'INVALID_SCHEDULE_WINDOW')
        return JSONResponse({'id': identity, 'created': created}, status_code=201 if created else 200)

    @app.get('/schedules', dependencies=[Depends(authenticated)])
    def list_schedules(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
        with sessions() as db:
            ids = list(db.scalars(select(Schedule.id).order_by(Schedule.created_at, Schedule.id).offset(offset).limit(limit)))
        return {'items': [schedules.view(identity) for identity in ids]}

    @app.get('/schedules/{schedule_id}', dependencies=[Depends(authenticated)])
    def view_schedule(schedule_id: str):
        return schedules.view(schedule_id)

    @app.post('/schedules/{schedule_id}/pause', dependencies=[Depends(authenticated)])
    def pause_schedule(schedule_id: str):
        return schedules.pause(schedule_id)

    @app.get('/notifications', dependencies=[Depends(authenticated)])
    def notifications(after: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), unread_only: bool = False):
        return inbox.listing(after, limit, unread_only)

    @app.post('/notifications/{notification_id}/read', dependencies=[Depends(authenticated)])
    def read_notification(notification_id: int):
        return inbox.mark_read(notification_id)

    @app.post('/batches', dependencies=[Depends(authenticated)])
    def submit_batch(body: BatchSubmission, idempotency_key: str = Header()):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', idempotency_key):
            raise HTTPException(422, 'INVALID_IDEMPOTENCY_KEY')
        identity, created = batches.submit(body.model_dump(mode='json', exclude_none=True), idempotency_key)
        return JSONResponse({'id': identity, 'created': created}, status_code=201 if created else 200)

    @app.get('/batches/{batch_id}', dependencies=[Depends(authenticated)])
    def view_batch(batch_id: str):
        return batches.view(batch_id)

    @app.post('/batches/{batch_id}/stop', dependencies=[Depends(authenticated)])
    def stop_batch(batch_id: str):
        return batches.stop(batch_id)

    @app.get('/tasks/{task_id}', dependencies=[Depends(authenticated)])
    def view(task_id: str):
        return service.view(task_id)

    @app.post('/tasks/{task_id}/stop', dependencies=[Depends(authenticated)])
    def stop(task_id: str):
        return {'status': service.stop(task_id)}

    @app.post('/tasks/{task_id}/resume', dependencies=[Depends(authenticated)])
    def resume(task_id: str):
        return {'status': service.resume(task_id)}

    @app.get('/tasks/{task_id}/events', dependencies=[Depends(authenticated)])
    def events(task_id: str, after: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        service.view(task_id)
        with sessions() as db:
            rows = list(db.scalars(select(Event).where(Event.task_id == task_id, Event.id > after).order_by(Event.id).limit(limit)))
            return {'items': [{'id': row.id, 'kind': row.kind, 'data': row.data, 'at': row.created_at.isoformat()} for row in rows],
                    'next_cursor': rows[-1].id if rows else after}

    @app.get('/tasks/{task_id}/artifacts/{name}', dependencies=[Depends(authenticated)])
    def artifact(task_id: str, name: str):
        if name not in ('report.json', 'report.md'):
            raise NotFound('ARTIFACT_NOT_FOUND')
        with sessions() as db:
            task = db.get(Task, task_id)
            record = db.scalar(select(Artifact).where(Artifact.task_id == task_id, Artifact.name == name))
            if task is None or task.status != 'SUCCEEDED' or record is None:
                raise NotFound('VERIFIED_ARTIFACT_NOT_FOUND')
            path = Path(task.run_dir) / 'workspace' / name
            if path.is_symlink() or not path.resolve().is_relative_to(settings.root):
                raise Conflict('ARTIFACT_PATH_CHANGED')
            data = path.read_bytes()
            if len(data) != record.bytes or hashlib.sha256(data).hexdigest() != record.sha256:
                raise Conflict('ARTIFACT_CHANGED')
            return Response(data, media_type='application/json' if name.endswith('.json') else 'text/markdown',
                            headers={'Content-Disposition': f'attachment; filename="{name}"', 'ETag': '"' + record.sha256 + '"'})

    return app


def production_app():
    return create_app(Settings.from_env())
