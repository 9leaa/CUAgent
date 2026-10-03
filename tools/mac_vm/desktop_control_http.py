"""Loopback-only trusted control channel; separate from model/verification tools.

No production launcher until worker authority and guest transport are integrated.
"""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re


def control_server(controller, token, *, port=0):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', token):
        raise ValueError('independent URL-safe control token required')

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(2)

        def log_message(self, *_):
            pass

        def reply(self, status, value):
            encoded = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(encoded)

        def authorized(self):
            headers = self.headers.get_all('Authorization', [])
            return (self.client_address[0] == '127.0.0.1' and len(headers) == 1
                    and hmac.compare_digest(headers[0].encode(), ('Bearer ' + token).encode()))

        def do_GET(self):
            if not self.authorized():
                return self.reply(403, {'error': 'CONTROL_AUTH_REQUIRED'})
            if self.path != '/lease':
                return self.reply(404, {'error': 'CONTROL_OPERATION_NOT_ALLOWED'})
            try:
                return self.reply(200, {'lease': controller.existing(), 'clockMs': int(controller.gate.clock() * 1000),
                    'binding': {'version': 1, 'runId': controller.gate.run_id,
                                'owner': controller.gate.owner, 'epoch': controller.gate.epoch}})
            except (OSError, ValueError, TypeError):
                return self.reply(409, {'error': 'CONTROL_RECORD_UNAVAILABLE'})

        def do_POST(self):
            if not self.authorized():
                return self.reply(403, {'error': 'CONTROL_AUTH_REQUIRED'})
            if self.path not in ('/renew', '/revoke'):
                return self.reply(404, {'error': 'CONTROL_OPERATION_NOT_ALLOWED'})
            try:
                sizes = self.headers.get_all('Content-Length', [])
                if self.headers.get('Transfer-Encoding') or len(sizes) != 1 or not sizes[0].isdigit():
                    raise ValueError('invalid framing')
                size = int(sizes[0])
                if not 0 < size <= 4096:
                    raise ValueError('invalid size')
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError('incomplete body')
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise ValueError('object required')
                if self.path == '/renew':
                    if set(body) != {'sequence', 'ttlMs', 'notAfterMs'} or type(body['notAfterMs']) is not int:
                        raise ValueError('invalid renewal fields')
                    result = controller.renew(body['sequence'], body['ttlMs'], not_after_ms=body['notAfterMs'])
                else:
                    if body:
                        raise ValueError('revoke requires empty body')
                    result = controller.revoke()
                return self.reply(200, {'lease': result})
            except (OSError, ValueError, TypeError):
                return self.reply(409, {'error': 'CONTROL_REQUEST_REJECTED'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server
