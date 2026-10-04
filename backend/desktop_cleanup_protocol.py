"""Trusted, unactivated-only cleanup protocol; also sent over fixed SSH."""
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys


def cleanup_unactivated(client):
    before = client.status()
    if (before['active'] or before['rawCalls'] or before['pendingCalls']
            or before.get('modelPort') is not None):
        raise ValueError('inactive zero-call guest required')
    lease = client.inspect().get('lease')
    if lease is not None and lease['stopped'] is not True:
        raise ValueError('never granted or already revoked guest required')
    client.revoke()
    result = client.shutdown()
    after = result['status']
    if after['rawCalls'] != 0 or after.get('modelPort') is not None:
        raise ValueError('guest changed during cleanup')
    # Do not echo server-supplied extras, token, paths or exceptions.
    return {'binding': dict(client.identity), 'closed': True, 'stopped': True,
            'active': False, 'rawCalls': 0, 'pendingCalls': 0}


def cleanup_main(client_type):
    try:
        if (sys.platform != 'darwin' or getpass.getuser() != 'mvpagent'
                or os.geteuid() == 0 or Path.home() != Path('/Users/mvpagent')):
            raise ValueError('ordinary VM required')
        model = subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model'],
                                        text=True, timeout=5).strip()
        if not model.startswith('VirtualMac'):
            raise ValueError('VM required')
        raw = sys.stdin.buffer.read(4097)
        if len(raw) > 4096:
            raise ValueError('bounded request required')
        request = json.loads(raw)
        if not isinstance(request, dict) or set(request) != {'port', 'token', 'run_id', 'owner', 'epoch'}:
            raise ValueError('fixed cleanup request required')
        print(json.dumps(cleanup_unactivated(client_type(**request))))
        return 0
    except Exception:
        print('P6_PREPARE_CLEANUP_UNCONFIRMED', file=sys.stderr)
        return 1
