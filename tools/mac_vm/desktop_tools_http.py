"""Opt-in model protocol for an already authorized DesktopTask; no launcher."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re

from desktop_lease import DesktopTask
from handoff_task import HandoffDesktopTask


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate field')
        result[key] = value
    return result


def tools_server(task, token, *, control_token, port=8766, loopback_test=False):
    if not isinstance(task, DesktopTask):
        raise ValueError('lease-guarded DesktopTask required')
    for credential in (token, control_token):
        if not isinstance(credential, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', credential):
            raise ValueError('independent URL-safe tokens required')
    if hmac.compare_digest(token, control_token):
        raise ValueError('model and control credentials must differ')
    if type(loopback_test) is not bool:
        raise ValueError('explicit test mode required')
    address, peer = ('127.0.0.1', '127.0.0.1') if loopback_test else ('192.168.64.3', '192.168.64.1')
    operations = {'observe', 'type_text', 'save', 'write_result', 'read_result'}
    if isinstance(task, HandoffDesktopTask):
        operations.update({'read_materials', 'reopen', 'locate_quote', 'check_draft'})
        if task.submission_protocol == 'p7-tool-submit-v1':
            operations.add('submit_handoff')
        if task.draft_input_mode == 'checked-draft-v1':
            operations.remove('type_text')
            operations.add('type_checked_draft')
    no_args = {'observe', 'read_result', 'read_materials'}

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(2)

        def log_message(self, *_):
            pass

        def reply(self, code, value):
            encoded = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except OSError:
                # Delivery uncertainty never causes another tool dispatch.
                pass

        def do_GET(self):
            self.reply(405, {'error': 'DESKTOP_POST_REQUIRED'})

        def do_POST(self):
            headers = self.headers.get_all('Authorization', [])
            if (self.client_address[0] != peer or len(headers) != 1
                    or not hmac.compare_digest(headers[0].encode(), ('Bearer ' + token).encode())):
                return self.reply(403, {'error': 'DESKTOP_MODEL_AUTH_REQUIRED'})
            try:
                if self.path != '/':
                    raise ValueError('path denied')
                sizes = self.headers.get_all('Content-Length', [])
                if self.headers.get_all('Transfer-Encoding') or len(sizes) != 1 or not sizes[0].isdigit():
                    raise ValueError('framing denied')
                size = int(sizes[0])
                if not 0 < size <= (512 * 1024 if isinstance(task, HandoffDesktopTask) else 32768):
                    raise ValueError('size denied')
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError('incomplete body')
                body = json.loads(raw, object_pairs_hook=unique_object)
                if not isinstance(body, dict) or set(body) != {'op', 'args'}:
                    raise ValueError('envelope denied')
                op, args = body['op'], body['args']
                if size > 32768 and op not in ('check_draft', 'submit_handoff'):
                    raise ValueError('size denied')
                if not isinstance(op, str) or not isinstance(args, dict):
                    raise ValueError('types denied')
                if op == 'stop' and args == {}:
                    # Do not acquire task.lock: a Driver request may be in flight.
                    return self.reply(200, task.stop())
            except Exception:
                return self.reject('request')

            with task.lock:
                prior_used = task.used
                try:
                    if op not in operations or (op in no_args and args):
                        raise ValueError('operation denied')
                    method = getattr(task, op)
                    result = method() if op in no_args else method(args)
                except Exception:
                    return self.reject_locked(op if op in operations else 'request', prior_used)
            self.reply(200, result)

        def reject(self, op):
            with task.lock:
                return self.reject_locked(op, task.used)

        def reject_locked(self, op, prior_used):
            try:
                task.charge_rejection(op, prior_used, 'DESKTOP_REQUEST_REJECTED')
                task.record({'event': 'denied', 'error': 'DESKTOP_REQUEST_REJECTED'})
            except Exception:
                # Lease or audit failure cannot reopen execution.
                task.stopped.set()
            self.reply(409, {'error': 'DESKTOP_REQUEST_REJECTED', 'used': task.used})

    server = ThreadingHTTPServer((address, port), Handler)
    server.daemon_threads = True
    return server
