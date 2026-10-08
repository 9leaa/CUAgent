"""One-shot trusted P7 collection. Never grants execution or business success."""
import base64
import json
import os
import re
import shlex
from backend.desktop_collect import GUEST_PYTHON, private_path, run_bounded, save_exclusive
from backend.handoff_client import HandoffControlClient
from backend.handoff_bundle import decode_handoff_bundle
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import canonical


def collect_handoff_bundle(*, root, ssh_wrapper, deployment, client, submission, expected, draft_input_mode='literal-text'):
    if draft_input_mode not in ('literal-text','checked-draft-v1'):
        raise ValueError('explicit input mode required')
    metadata = {'inputMode':draft_input_mode} if draft_input_mode == 'checked-draft-v1' else {}
    root = private_path(root, directory=True)
    wrapper = private_path(ssh_wrapper, directory=False)
    submission = HandoffSubmission.model_validate(submission)
    if (not os.access(wrapper, os.X_OK) or not isinstance(client, HandoffControlClient)
            or root.name != client.identity['runId'] or not isinstance(deployment, str)
            or not re.fullmatch(r'/Users/mvpagent/CUAgent-p6-[0-9a-f]{40}', deployment)
            or type(expected) is not bytes or not 0 < len(expected) <= 4096):
        raise ValueError('trusted P7 collection binding required')
    identity = client.identity.copy()
    uuid = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
    if not re.fullmatch('p2-' + uuid, identity['runId']) or not re.fullmatch(uuid, identity['owner']):
        raise ValueError('fixed UUID identities required')
    before = client.status()
    lease = client.inspect().get('lease')
    if (before['stopped'] is not True or before['pendingCalls'] != 0
            or type(before['rawCalls']) is not int or not 1 <= before['rawCalls'] <= 30
            or not lease or lease.get('stopped') is not True):
        raise ValueError('revoked idle guest required')
    materials = canonical(submission.model_dump(mode='json'))
    payload = json.dumps(dict(materialsBase64=base64.b64encode(materials).decode(),
                              expectedBase64=base64.b64encode(expected).decode())).encode()
    save_exclusive(root / 'handoff-collection-intent.json', canonical(dict(identity,**metadata)))
    command = shlex.join([GUEST_PYTHON, deployment + '/handoff_export.py', '--run', identity['runId'],
                          '--owner', identity['owner'], '--epoch', str(identity['epoch']),
                          *(['--draft-input-mode',draft_input_mode] if metadata else [])])
    args = [str(wrapper), '-F', '/dev/null', '-T', '-o', 'ClearAllForwardings=yes',
            '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no', '-o', 'ControlMaster=no', '-o', 'ControlPath=none', command]
    raw = run_bounded(args, payload, input_limit=512*1024)
    save_exclusive(root / 'handoff-guest-evidence.tar', raw)
    after = client.status()
    if (after['stopped'] is not True or after['pendingCalls'] != 0
            or type(after['rawCalls']) is not int or after['rawCalls'] != before['rawCalls']
            or client.inspect().get('lease') != lease):
        raise RuntimeError('HANDOFF_COLLECTION_STATE_CHANGED')
    bundle = decode_handoff_bundle(raw, binding=identity, materials=materials, expected=expected, draft_input_mode=draft_input_mode)
    if bundle['guest']['rawCalls'] != before['rawCalls']:
        raise ValueError('guest evidence budget differs from runtime')
    parent = root / 'guest'; parent.mkdir(mode=0o700)
    directory = parent / root.name; directory.mkdir(mode=0o700)
    (directory / 'artifacts').mkdir(mode=0o700)
    for name, data in bundle['files'].items():
        save_exclusive(directory / name, data)
    save_exclusive(root / 'handoff-collection-receipt.json', canonical(dict(
        status='TRANSPORT_VERIFIED', binding=identity, files=bundle['guest']['files'],
        sessionVerified=False, semanticVerified=False, **metadata)))
    return directory
