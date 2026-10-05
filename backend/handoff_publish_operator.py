"""Trusted local publication/inspection only; never dispatches model or VM work."""
import argparse
import json
from pathlib import Path
import re
import uuid
from sqlalchemy import select
from backend.db import database
from backend.desktop_service import load_profile
from backend.handoff_publication import publish_reviewed_task
from backend.models import Artifact, Event, Task
from backend.service import TaskService, NotFound


def inspect_publication(service, task_id):
    # A single read transaction gives one locked task identity; publication uses
    # the same task lock. Do not read/acknowledge notices or change file evidence.
    with service.sessions.begin() as db:
        task = db.get(Task, task_id, with_for_update=True)
        if task is None or task.payload.get('kind') != 'project-handoff':
            raise NotFound('HANDOFF_TASK_NOT_FOUND')
        event = db.scalar(select(Event).where(Event.task_id == task_id,
            Event.kind == 'handoff_published', Event.external_id == 'handoff-publication'))
        artifacts = {a.name: dict(sha256=a.sha256, bytes=a.bytes) for a in
                     db.scalars(select(Artifact).where(Artifact.task_id == task_id))}
        intent = None
        if task.run_dir:
            root = Path(task.run_dir)
            if (root.resolve(strict=True) != root or not root.is_relative_to(service.settings.root.resolve())
                    or root.name != 'p2-' + task.id):
                raise ValueError('ORIGINAL_RUN_PATH_REQUIRED')
            intent = (root / 'handoff-publication-intent.json').exists()
        return dict(taskId=task.id, status=task.status, sessionId=task.session_id, rawCalls=task.calls,
            publicationEventId=event.id if event else None,
            reviewFileSha256=event.data.get('reviewFileSha256') if event else None,
            databasePublicationRecorded=bool(event and task.status == 'SUCCEEDED'),
            publicationIntentPresent=intent, artifacts=artifacts,
            artifactBytesReverified=False, retryAuthorized=False)


def run(command, *, profile_path, task_id, review_sha256=None):
    if str(uuid.UUID(task_id)) != task_id or command not in ('publish', 'inspect'):
        raise ValueError('INVALID_PUBLICATION_COMMAND')
    if command == 'publish':
        if type(review_sha256) is not str or not re.fullmatch('[0-9a-f]{64}', review_sha256):
            raise ValueError('REVIEW_SHA256_REQUIRED')
    elif review_sha256 is not None:
        raise ValueError('INSPECT_DOES_NOT_ACCEPT_REVIEW')
    profile = load_profile(profile_path, kind='project-handoff')
    engine, sessions = database(profile.settings.database_url)
    try:
        service = TaskService(sessions, profile.settings)
        if command == 'inspect':
            return inspect_publication(service, task_id)
        return publish_reviewed_task(service, task_id, review_sha256)
    finally:
        engine.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['publish', 'inspect'])
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--task', required=True)
    parser.add_argument('--review-sha256')
    args = parser.parse_args(argv)
    try:
        result = run(args.command, profile_path=args.profile, task_id=args.task, review_sha256=args.review_sha256)
        print(json.dumps(result))
        return 0
    except Exception:
        print(json.dumps(dict(result='PUBLICATION_UNCONFIRMED' if args.command == 'publish' else 'INSPECTION_UNCONFIRMED',
            action='Inspect the original task and publication event; do not replay or overwrite.', retryAuthorized=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
