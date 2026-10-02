"""Local task client: reads private auth without putting it in command arguments."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import httpx
from agent.daily_report import text_file
from backend.manage import load_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['submit', 'list', 'status', 'events', 'stop', 'resume', 'download'])
    parser.add_argument('--spec')
    parser.add_argument('--key')
    parser.add_argument('--task')
    parser.add_argument('--output')
    parser.add_argument('--name', choices=['report.json', 'report.md'], default='report.md')
    args = parser.parse_args()
    env = load_env()
    with httpx.Client(base_url='http://127.0.0.1:18089', trust_env=False, timeout=20,
                      headers={'Authorization': 'Bearer ' + env['CUAGENT_BACKEND_TOKEN']}) as client:
        if args.command == 'submit':
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
