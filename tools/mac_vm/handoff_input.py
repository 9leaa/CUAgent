"""Trusted one-shot input provisioning. No arbitrary paths or GUI writes."""
import base64
import hashlib
import json
import os
import re
from desktop_lease import LeaseGate
from handoff_task import unique_object, reject_constant


def verify_provision(runtime, digest):
    if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('original input digest required')
    gate = runtime.controller.gate
    binding = dict(version=1, runId=gate.run_id, owner=gate.owner, epoch=gate.epoch)
    records = []
    for name, status in [('handoff-input-intent.json', 'INTENT'), ('handoff-input-receipt.json', 'STORED')]:
        path = runtime.directory / name
        if path.parent.resolve(strict=True) != path.parent:
            raise ValueError('canonical provision root required')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            LeaseGate.private(info)
            if info.st_nlink != 1 or info.st_size > 4096:
                raise ValueError('private bounded provision record required')
            raw = stream.read(4097)
        if len(raw) > 4096:
            raise ValueError('oversized provision record')
        record = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
        if (type(record) is not dict or set(record) != {'status', 'binding', 'inputSha256', 'bytes'}
                or record['status'] != status or type(record['binding']) is not dict or record['binding'] != binding
                or type(record['binding'].get('version')) is not int or type(record['binding'].get('epoch')) is not int
                or record['inputSha256'] != digest or type(record['bytes']) is not int
                or not 0 < record['bytes'] <= 256 * 1024):
            raise ValueError('provision record mismatch')
        records.append(record)
    if records[0]['bytes'] != records[1]['bytes']:
        raise ValueError('provision size changed')
    return records[1]


def provision(runtime, body):
    with runtime.lock:
        if runtime.closed or runtime.task is not None or runtime.thread is not None:
            raise ValueError('fresh runtime required')
        gate = runtime.controller.gate
        binding = dict(version=1, runId=gate.run_id, owner=gate.owner, epoch=gate.epoch)
        if (type(body) is not dict or set(body) != {'binding', 'inputSha256', 'inputBase64'}
                or type(body['binding']) is not dict or body['binding'] != binding
                or type(body['binding'].get('version')) is not int or type(body['binding'].get('epoch')) is not int
                or not isinstance(body['inputSha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', body['inputSha256'])
                or not isinstance(body['inputBase64'], str) or len(body['inputBase64']) > 349528):
            raise ValueError('bound input envelope required')
        gate.check()
        raw = base64.b64decode(body['inputBase64'], validate=True)
        if not 0 < len(raw) <= 256 * 1024 or hashlib.sha256(raw).hexdigest() != body['inputSha256']:
            raise ValueError('input bytes or digest invalid')
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
        if (type(value) is not dict or set(value) != {'kind', 'project', 'asOf', 'notes', 'tasksCsv', 'previousReport'}
                or value['kind'] != 'project-handoff'):
            raise ValueError('validated project handoff input required')
        directory = runtime.directory
        if directory.resolve(strict=True) != directory:
            raise ValueError('canonical input root required')
        root = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            LeaseGate.private(os.fstat(root), directory=True)
            if os.path.lexists(directory / 'guest-activation-intent.json'):
                raise ValueError('activation already attempted')
            def write(name, data):
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data); stream.flush(); os.fsync(stream.fileno())
                os.fsync(root)
            receipt = dict(status='STORED', binding=binding, inputSha256=body['inputSha256'], bytes=len(raw))
            gate.check()
            write('handoff-input-intent.json', json.dumps(dict(receipt, status='INTENT')).encode())
            write('handoff-input.json', raw)
            gate.check()
            write('handoff-input-receipt.json', json.dumps(receipt).encode())
            gate.check()
            return receipt
        finally:
            os.close(root)
