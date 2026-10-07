"""Official Harness subprocess adapter, not another Agent loop or profile switch."""
import json
import os
from pathlib import Path
import re
import stat

from backend.desktop_collect import private_path, run_bounded, save_exclusive
from backend.desktop_contract import DesktopSubmission

MODEL = {'provider': 'deepseek-account', 'model': 'deepseek-flash', 'reasoningEffort': 'off'}
COMMAND = Path(__file__).resolve().parents[1] / 'agent/harness/desktop-session-command.mjs'
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


class DesktopSessionClient:
    def __init__(self, *, root, session_id, node, official_home, cookie):
        self.root = private_path(root, directory=True)
        self.home = private_path(official_home, directory=True)
        self.cookie = private_path(cookie, directory=False)
        self.node = Path(node).absolute()
        if (self.node.resolve(strict=True) != self.node or not self.node.is_file()
                or self.node.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                or not os.access(self.node, os.X_OK)):
            raise ValueError('canonical trusted Node executable required')
        if not re.fullmatch('p2-' + UUID, self.root.name) or not isinstance(session_id, str) or not re.fullmatch('session-' + UUID, session_id):
            raise ValueError('fixed run and session identities required')
        self.session_id = session_id

    def prepare(self, submission):
        if not isinstance(submission, DesktopSubmission):
            raise ValueError('typed submission required')
        workspace = private_path(self.root / 'workspace', directory=True)
        request = {'runId': self.root.name, 'sessionId': self.session_id, 'cwd': str(workspace),
                   'lines': list(submission.lines)}
        save_exclusive(self.root / 'desktop-request.json', json.dumps(request, ensure_ascii=False).encode())

    def command(self, mode):
        if mode not in ('start', 'inspect', 'cancel'):
            raise ValueError('reviewed session command required')
        args = [str(self.node), str(COMMAND), mode, str(self.root), str(self.home), str(self.cookie)]
        # start includes up to five bounded RPCs; no retries after ambiguous exit.
        raw = run_bounded(args, b'', limit=65536, timeout=75 if mode == 'start' else 40)
        result = json.loads(raw)
        if not isinstance(result, dict) or result.get('sessionId') != self.session_id:
            raise ValueError('official session response identity mismatch')
        return result

    def start(self):
        save_exclusive(self.root / 'desktop-session-start-intent.json', json.dumps({'sessionId': self.session_id}).encode())
        result = self.command('start')
        save_exclusive(self.root / 'desktop-session-start-response.json', json.dumps(result).encode())
        if result.get('accepted') is not True or result.get('model') != MODEL:
            raise ValueError('official session start/model unconfirmed')
        return result

    def inspect(self):
        result = self.command('inspect')
        if 'evidencePending' in result:
            expected = dict(sessionId=self.session_id, exists=True, running=True, terminal=False,
                evidencePending=True, events=None, calls=None, userMessages=None,
                rawUserMessages=None, frameworkNotices=None, promptObserved=False)
            if (result != expected or any(type(result.get(k)) is not bool for k in
                    ('exists', 'running', 'terminal', 'evidencePending', 'promptObserved'))):
                raise ValueError('live observation may not claim terminal evidence')
            return result
        if (result.get('exists') is not True or type(result.get('running')) is not bool
                or type(result.get('terminal')) is not bool or type(result.get('promptObserved')) is not bool
                or type(result.get('userMessages')) is not int or not 0 <= result['userMessages'] <= 1):
            raise ValueError('official session observation unconfirmed')
        if result['terminal'] and (result['running'] or not result['promptObserved'] or result['userMessages'] != 1):
            raise ValueError('original official prompt termination unconfirmed')
        return result

    def poll(self, control_client):
        if control_client.identity.get('runId') != self.root.name:
            raise ValueError('guest and session run mismatch')
        session = self.inspect()
        guest = control_client.status()
        return {'terminal': session['terminal'], 'rawCalls': guest['rawCalls'],
                'pendingCalls': guest['pendingCalls'], 'session': session, 'guestStopped': guest['stopped']}

    def cancel(self):
        save_exclusive(self.root / 'desktop-session-cancel-intent.json', json.dumps({'sessionId': self.session_id}).encode())
        result = self.command('cancel')
        save_exclusive(self.root / 'desktop-session-cancel-response.json', json.dumps(result).encode())
        if type(result.get('cancelRequested')) is not bool:
            raise ValueError('official cancellation unconfirmed')
        return result  # Never returns terminal or claims side effects rolled back.
