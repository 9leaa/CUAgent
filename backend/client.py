"""Local task client: reads private auth without putting it in command arguments."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import httpx
from agent.daily_report import text_file
from backend.manage import load_env


def desktop_spec(path):
    """Read bounded data, never task-supplied authority or executable commands."""
    from backend.desktop_contract import DesktopSubmission
    path = Path(path).absolute()
    if path.resolve(strict=True) != path:
        raise ValueError('desktop spec must not traverse symbolic links')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 32768:
            raise ValueError('desktop spec must be a regular file of at most 32768 bytes')
        raw = stream.read(32769)
    if len(raw) > 32768 or len(raw) != info.st_size:
        raise ValueError('desktop spec changed or exceeds size limit')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate desktop spec field')
            value[key] = item
        return value
    body = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
    return DesktopSubmission.model_validate(body).model_dump(mode='json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['submit', 'desktop-submit', 'list', 'status', 'events', 'stop', 'resume', 'download',
                                           'batch-submit', 'batch-status', 'batch-stop', 'notifications', 'notification-read',
                                           'schedule-create', 'schedule-list', 'schedule-status', 'schedule-pause'])
    parser.add_argument('--spec')
    parser.add_argument('--key')
    parser.add_argument('--task')
    parser.add_argument('--batch')
    parser.add_argument('--schedule')
    parser.add_argument('--notification', type=int)
    parser.add_argument('--after', type=int, default=0)
    parser.add_argument('--unread-only', action='store_true')
    parser.add_argument('--output')
    parser.add_argument('--name', choices=['report.json', 'report.md', 'document.txt', 'result.txt'], default='report.md')
    args = parser.parse_args()
    env = load_env()
    with httpx.Client(base_url='http://127.0.0.1:18089', trust_env=False, timeout=20,
                      headers={'Authorization': 'Bearer ' + env['CUAGENT_BACKEND_TOKEN']}) as client:
        if args.command == 'desktop-submit':
            if not args.spec or not args.key or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.key):
                parser.error('desktop-submit requires --spec and a stable --key; reuse the key after an ambiguous request')
            body = desktop_spec(args.spec)
            response = client.post('/desktop-tasks', json=body, headers={'Idempotency-Key': args.key})
        elif args.command == 'schedule-create':
            if not args.spec or not args.key:
                parser.error('schedule-create requires --spec and --key; this does not grant execution quota')
            from backend.schemas import ScheduleSubmission
            path = Path(args.spec).resolve(strict=True)
            if path.stat().st_size > 4096: raise ValueError('schedule spec too large')
            body = ScheduleSubmission.model_validate_json(path.read_text()).model_dump(mode='json')
            response = client.post('/schedules', json=body, headers={'Idempotency-Key': args.key})
        elif args.command == 'schedule-list':
            response = client.get('/schedules')
        elif args.command in ('schedule-status', 'schedule-pause'):
            if not args.schedule or not re.fullmatch(r'[a-f0-9-]{36}', args.schedule):
                parser.error('a schedule UUID is required')
            url = '/schedules/' + args.schedule
            response = client.post(url + '/pause') if args.command == 'schedule-pause' else client.get(url)
        elif args.command == 'notifications':
            response = client.get('/notifications', params={'after': args.after, 'unread_only': args.unread_only})
        elif args.command == 'notification-read':
            if args.notification is None or args.notification < 1:
                parser.error('notification-read requires a positive --notification ID')
            response = client.post('/notifications/' + str(args.notification) + '/read')
        elif args.command == 'batch-submit':
            if not args.spec or not args.key:
                parser.error('batch-submit requires --spec (inline tasks JSON) and --key')
            from backend.schemas import BatchSubmission
            path = Path(args.spec).resolve(strict=True)
            if path.stat().st_size > 262144:
                raise ValueError('batch body too large')
            body = BatchSubmission.model_validate_json(path.read_text()).model_dump(mode='json', exclude_none=True)
            response = client.post('/batches', json=body, headers={'Idempotency-Key': args.key})
        elif args.command in ('batch-status', 'batch-stop'):
            if not args.batch or not re.fullmatch(r'[a-f0-9-]{36}', args.batch):
                parser.error('a batch UUID is required')
            url = '/batches/' + args.batch
            response = client.post(url + '/stop') if args.command == 'batch-stop' else client.get(url)
        elif args.command == 'submit':
            if not args.spec or not args.key:
                parser.error('submit requires --spec and --key; reuse the key after an ambiguous request')
            path = Path(args.spec).resolve(strict=True)
            spec = json.loads(path.read_text())
            def source(name, extension):
                if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+\.' + extension, name):
                    raise ValueError('simple input name required')
                return text_file(path.parent / name)[1]
            payload = {'date': spec['date'], 'notes': [{'name': name, 'content': source(name, 'md')} for name in spec['notes']],
                       'csv': [{'name': c['path'], 'content': source(c['path'], 'csv'), 'numericColumns': c['numericColumns']} for c in spec['csv']]}
            if spec.get('releaseAt') is not None:
                payload['releaseAt'] = spec['releaseAt']
            if spec.get('inputMode') is not None:
                payload['inputMode'] = spec['inputMode']
            response = client.post('/tasks', json=payload, headers={'Idempotency-Key': args.key})
        elif args.command == 'list':
            response = client.get('/tasks')
        else:
            if not args.task or not re.fullmatch(r'[a-f0-9-]{36}', args.task):
                parser.error('a task UUID is required')
            url = '/tasks/' + args.task
            if args.command in ('stop', 'resume'):
                response = client.post(url + '/' + args.command)
            elif args.command == 'download':
                if not args.output:
                    parser.error('download requires a new --output path')
                response = client.get(url + '/artifacts/' + args.name)
                response.raise_for_status()
                digest = hashlib.sha256(response.content).hexdigest()
                if response.headers.get('etag') != '"' + digest + '"':
                    raise ValueError('download hash mismatch')
                target = Path(args.output).absolute()
                with target.open('xb') as file:
                    target.chmod(0o600)
                    file.write(response.content)
                print(json.dumps({'path': str(target), 'bytes': len(response.content), 'sha256': digest}))
                return
            else:
                response = client.get(url + ('/events' if args.command == 'events' else ''))
        response.raise_for_status()
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
