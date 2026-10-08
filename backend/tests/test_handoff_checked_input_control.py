"""Real loopback activation, no GUI or model requests."""
import json
from unittest.mock import patch
import pytest
from backend.tests.test_handoff_client import transfer
from backend.desktop_client import ControlUnconfirmed
from backend.handoff_result import input_digest

SESSION = 'session-22222222-2222-2222-2222-222222222222'
MODE = 'checked-draft-v1'


def prepare(transfer):
    client, runtime, source, _ = transfer
    client.provision_handoff(source, lambda: 65.)
    client.bind_draft_session(SESSION, protocol='p7-tool-submit-v1', draft_input_mode=MODE)
    return client, runtime, source


def test_bound_mode_persisted_before_task_and_listener(transfer):
    client, runtime, source = prepare(transfer)
    expected = dict(version=1, inputMode=MODE, runId='task', sessionId=SESSION,
                    inputSha256=input_digest(source))
    factory = runtime.handoff_task_factory
    calls = []
    def checked(*args, **kwargs):
        path = runtime.directory / 'handoff-input-mode.json'
        assert json.loads(path.read_bytes()) == expected
        assert path.stat().st_mode & 0o777 == 0o600
        assert runtime.server is None
        assert kwargs['draft_input_mode'] == MODE
        calls.append(True)
        return factory(*args, **kwargs)
    runtime.handoff_task_factory = checked
    state = client.activate(lambda: 65.)
    assert calls == [True] and state['active'] and state['rawCalls'] == 0
    assert runtime.task.draft_input_mode == MODE
    with pytest.raises(ControlUnconfirmed): client.bind_draft_session(SESSION)
    with pytest.raises(ControlUnconfirmed): client.activate(lambda: 65.)


@pytest.mark.parametrize('mode,protocol', [(None,'p7-tool-submit-v1'), (True,'p7-tool-submit-v1'),
    ('unknown','p7-tool-submit-v1'), (MODE,'legacy-final-json')])
def test_invalid_client_mode_has_no_binding_or_activation(transfer, mode, protocol):
    client, runtime, _, _ = transfer
    with pytest.raises(ControlUnconfirmed):
        client.bind_draft_session(SESSION, protocol=protocol, draft_input_mode=mode)
    assert not hasattr(client, '_draft_session_id')
    assert not (runtime.directory / 'guest-activation-intent.json').exists()


@pytest.mark.parametrize('fault', ['session','protocol','mode','legacy','extra','model_token'])
def test_control_requires_complete_explicit_binding_and_control_credential(transfer, fault):
    client, runtime, _ = prepare(transfer)
    path, body = client.activation_request()
    if fault == 'session': del body['sessionId']
    if fault == 'protocol': del body['protocol']
    if fault == 'mode': body['inputMode'] = True
    if fault == 'legacy': body['inputMode'] = 'literal-text'
    if fault == 'extra': body['text'] = 'override'
    token = client.token
    if fault == 'model_token': client.token = transfer[3]
    try:
        with pytest.raises(ControlUnconfirmed): client.request('POST', path, body)
    finally: client.token = token
    assert runtime.task is None and runtime.server is None
    assert not (runtime.directory / 'guest-activation-intent.json').exists()


@pytest.mark.parametrize('fault', ['existing','symlink','write_failure','downgrade'])
def test_activation_failure_is_stopped_non_replayable_and_preserves_record(transfer, fault):
    client, runtime, _ = prepare(transfer)
    path = runtime.directory / 'handoff-input-mode.json'
    if fault in ('existing','downgrade'): path.write_bytes(b'original')
    if fault == 'symlink':
        original = runtime.directory / 'original-mode'; original.write_bytes(b'original')
        path.symlink_to(original)
    if fault == 'downgrade':
        route, body = client.activation_request(); del body['inputMode']
        with pytest.raises(ControlUnconfirmed): client.request('POST', route, body)
    elif fault == 'write_failure':
        import desktop_runtime
        dump = desktop_runtime.json.dump
        def fail(value, *args, **kwargs):
            if value.get('inputMode') == MODE: raise OSError('disk failure')
            return dump(value, *args, **kwargs)
        with patch.object(desktop_runtime.json, 'dump', side_effect=fail):
            with pytest.raises(ControlUnconfirmed): client.activate(lambda: 65.)
        assert path.exists() and path.read_bytes() == b''
    else:
        with pytest.raises(ControlUnconfirmed): client.activate(lambda: 65.)
    assert runtime.task is None and runtime.server is None
    assert runtime.controller.existing()['stopped'] is True
    assert (runtime.directory / 'guest-activation-intent.json').exists()
    if fault != 'write_failure': assert path.read_bytes() == b'original'
    with pytest.raises(ControlUnconfirmed): client.activate(lambda: 65.)


def test_unknown_activation_reply_never_replays(transfer):
    client, runtime, _ = prepare(transfer)
    original = client.request
    calls = []
    def lost(method, path, body=None):
        value = original(method, path, body)
        if path == '/activate-handoff':
            calls.append(path)
            raise ControlUnconfirmed('lost reply')
        return value
    client.request = lost
    with pytest.raises(ControlUnconfirmed): client.activate(lambda: 65.)
    before = (runtime.directory / 'handoff-input-mode.json').read_bytes()
    with pytest.raises(ControlUnconfirmed): client.activate(lambda: 65.)
    assert len(calls) == 1 and runtime.task.used == 0
    assert (runtime.directory / 'handoff-input-mode.json').read_bytes() == before


@pytest.mark.parametrize('kwargs', [{}, {'submission_protocol':'p7-tool-submit-v1'},
    {'submission_protocol':'p7-tool-submit-v1', 'draft_session_id':SESSION}])
def test_checked_mode_cannot_activate_p6_or_unbound_task(transfer, kwargs):
    _, runtime, _, _ = transfer
    with pytest.raises(ValueError): runtime.activate(draft_input_mode=MODE, **kwargs)
    assert runtime.task is None and runtime.server is None
    assert not (runtime.directory / 'guest-activation-intent.json').exists()


def test_directory_sync_failure_keeps_mode_but_never_constructs_task(transfer):
    client, runtime, _ = prepare(transfer)
    import desktop_runtime
    import stat
    original = desktop_runtime.os.fsync
    def fail(fd):
        if stat.S_ISDIR(desktop_runtime.os.fstat(fd).st_mode): raise OSError('directory sync failed')
        return original(fd)
    with patch.object(desktop_runtime.os, 'fsync', side_effect=fail):
        with pytest.raises(ControlUnconfirmed): client.activate(lambda: 65.)
    assert runtime.task is None and runtime.server is None
    assert json.loads((runtime.directory / 'handoff-input-mode.json').read_bytes())['inputMode'] == MODE
    assert runtime.controller.existing()['stopped'] is True


def test_loss_of_authority_after_binding_prevents_listener(transfer):
    client, runtime, _ = prepare(transfer)
    factory = runtime.handoff_task_factory
    def expired(*args, **kwargs):
        task = factory(*args, **kwargs)
        runtime.controller.revoke()
        return task
    runtime.handoff_task_factory = expired
    with pytest.raises(ControlUnconfirmed): client.activate(lambda: 65.)
    assert runtime.task.used == 0 and runtime.task.stopped.is_set()
    assert runtime.server is None and runtime.controller.existing()['stopped'] is True
    assert (runtime.directory / 'handoff-input-mode.json').exists()


def test_cleanup_reverification_uses_original_task_mode(transfer):
    client, runtime, _ = prepare(transfer)
    client.activate(lambda:65.)
    client.revoke()
    runtime.application = object()  # No native cleanup; only invoke its read-only verifier callback.
    (runtime.directory / 'artifacts' / 'handoff-task.txt').write_bytes(b'original document')
    report = dict(status='VM_EVIDENCE_VERIFIED',rawCalls=0,files={
        name:dict(sha256='a'*64) for name in ('artifacts/handoff-task.txt','result.txt','trace.jsonl')})
    with patch('desktop_runtime.inspect_handoff_evidence',return_value=report) as verify, \
            patch('desktop_runtime.ApplicationCleanup') as cleaner:
        def run(): return cleaner.call_args.kwargs['read_hashes']()
        cleaner.return_value.run.side_effect = run
        runtime.cleanup_application(dict(sessionTerminal=True,sessionVerified=True,hashes={}))
    assert verify.call_args.kwargs['draft_input_mode'] == MODE
    assert verify.call_args.kwargs['expected'] == b'original document'
