import json
from pathlib import Path
import sys
from unittest.mock import Mock, patch
import pytest
from backend.desktop_contract import DesktopSubmission
from backend.desktop_session import DesktopSessionClient, MODEL, COMMAND
from backend.handoff_session_client import HandoffSessionClient
from backend.handoff_result import input_digest
from backend.tests.test_handoff_result import fixture, RUN, SESSION


@pytest.fixture
def client(tmp_path):
    root = tmp_path / RUN; root.mkdir(mode=0o700)
    (root / 'workspace').mkdir(mode=0o700)
    home = tmp_path / 'home'; home.mkdir(mode=0o700)
    cookie = tmp_path / 'cookie'; cookie.write_bytes(b'synthetic'); cookie.chmod(0o600)
    return HandoffSessionClient(root=root, session_id=SESSION, node=Path(sys.executable).resolve(),
                                official_home=home, cookie=cookie)


def test_prepare_only_binds_valid_original_materials_without_start(client):
    source, _ = fixture()
    with patch('backend.desktop_session.run_bounded') as run:
        client.prepare(source)
        value = json.loads((client.root / 'desktop-request.json').read_bytes())
        assert value == dict(kind='project-handoff', runId=RUN, sessionId=SESSION,
                             cwd=str(client.root / 'workspace'), inputSha256=input_digest(source))
        assert (client.root / 'desktop-request.json').stat().st_mode & 0o077 == 0
        with pytest.raises(FileExistsError): client.prepare(source)
        run.assert_not_called()


@pytest.mark.parametrize('bad', ['p6', 'extra', 'unsafe-copy'])
def test_invalid_or_foreign_submission_never_writes_request(client, bad):
    source, _ = fixture()
    value = (DesktopSubmission(kind='desktop-textedit', lines=['x']) if bad == 'p6' else
             dict(source.model_dump(), shell=True) if bad == 'extra' else source.model_copy(update={'asOf': 'invalid'}))
    with pytest.raises(ValueError): client.prepare(value)
    assert not (client.root / 'desktop-request.json').exists()
    with pytest.raises(ValueError): DesktopSessionClient.prepare(client, source)


@pytest.mark.parametrize('fault', [None, 'model', 'session', 'timeout'])
def test_start_uses_existing_official_command_and_never_replays(client, fault):
    client.prepare(fixture()[0])
    response = dict(sessionId=SESSION, accepted=True, model=MODEL)
    if fault == 'model': response['model'] = dict(MODEL, reasoningEffort='high')
    if fault == 'session': response['sessionId'] = 'other'
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps(response).encode(),
               side_effect=RuntimeError('unknown') if fault == 'timeout' else None) as run:
        if fault:
            with pytest.raises((RuntimeError, ValueError)): client.start()
        else: assert client.start() == response
        assert run.call_args.args[0][1:3] == [str(COMMAND), 'start']
        with pytest.raises(FileExistsError): client.start()
        run.assert_called_once()


def test_poll_original_guest_budget_and_cancel_remain_separate(client):
    client.prepare(fixture()[0])
    guest = Mock(identity=dict(runId=RUN))
    guest.status.return_value = dict(rawCalls=15, pendingCalls=0, stopped=True)
    response = dict(sessionId=SESSION, exists=True, running=False, terminal=True, promptObserved=True, userMessages=1, calls=10)
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps(response).encode()):
        result = client.poll(guest)
        assert result['rawCalls'] == 15 and result['session']['calls'] == 10
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps(dict(sessionId=SESSION, cancelRequested=True)).encode()) as run:
        assert client.cancel()['cancelRequested'] is True
        with pytest.raises(FileExistsError): client.cancel()
        run.assert_called_once()
