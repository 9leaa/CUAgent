import json
from pathlib import Path
import sys
from unittest.mock import Mock, patch
import pytest
from backend.desktop_contract import DesktopSubmission
from backend.desktop_session import DesktopSessionClient, MODEL, COMMAND

RUN = 'p2-11111111-1111-1111-1111-111111111111'
SESSION = 'session-22222222-2222-2222-2222-222222222222'


@pytest.fixture
def session(tmp_path):
    root = tmp_path / RUN
    root.mkdir(mode=0o700)
    (root / 'workspace').mkdir(mode=0o700)
    home = tmp_path / 'home'
    home.mkdir(mode=0o700)
    cookie = tmp_path / 'cookie.json'
    cookie.write_text('{"cookie":"synthetic-secret"}')
    cookie.chmod(0o600)
    client = DesktopSessionClient(root=root, session_id=SESSION, node=Path(sys.executable).resolve(),
                                  official_home=home, cookie=cookie)
    client.prepare(DesktopSubmission(kind='desktop-textedit', lines=['交接', 'ok']))
    return client


def test_prepare_freezes_identity_and_lines_without_model_calls(session):
    request = json.loads((session.root / 'desktop-request.json').read_bytes())
    assert request == {'runId': RUN, 'sessionId': SESSION, 'cwd': str(session.root / 'workspace'), 'lines': ['交接', 'ok']}
    with pytest.raises(FileExistsError):
        session.prepare(DesktopSubmission(kind='desktop-textedit', lines=['changed']))


def test_start_fixed_entrypoint_flash_off_single_attempt(session):
    response = {'sessionId': SESSION, 'accepted': True, 'model': MODEL}
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps(response).encode()) as run:
        assert session.start() == response
        args, payload = run.call_args.args
        assert args[1:3] == [str(COMMAND), 'start']
        assert payload == b'' and 'synthetic-secret' not in str(args)
        with pytest.raises(FileExistsError): session.start()
        run.assert_called_once()


@pytest.mark.parametrize('response', [None, {'sessionId': 'other'},
    {'sessionId': SESSION, 'accepted': True, 'model': {**MODEL, 'reasoningEffort': 'high'}}])
def test_failed_start_is_not_replayed(session, response):
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps(response).encode()) as run:
        with pytest.raises(ValueError): session.start()
        with pytest.raises(FileExistsError): session.start()
        run.assert_called_once()


def observation(**changes):
    return dict(sessionId=SESSION, exists=True, running=False, terminal=True,
                promptObserved=True, userMessages=1, calls=3, **changes)


def test_poll_uses_guest_raw_budget_not_official_tool_count(session):
    guest = Mock(identity={'runId': RUN})
    guest.status.return_value = {'rawCalls': 12, 'pendingCalls': 0, 'stopped': False}
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps(observation()).encode()):
        result = session.poll(guest)
        assert result['terminal'] and result['rawCalls'] == 12
        assert result['session']['calls'] == 3


@pytest.mark.parametrize('change', [{'exists': False}, {'terminal': 1}, {'running': True},
                                    {'promptObserved': False}, {'userMessages': 2}, {'userMessages': True}])
def test_unconfirmed_session_not_terminal_success(session, change):
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps({**observation(), **change}).encode()):
        with pytest.raises(ValueError): session.inspect()


def test_cancel_only_reports_request_and_cannot_replay(session):
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps({'sessionId': SESSION, 'cancelRequested': True}).encode()) as run:
        assert session.cancel() == {'sessionId': SESSION, 'cancelRequested': True}
        with pytest.raises(FileExistsError): session.cancel()
        run.assert_called_once()


def live_observation():
    return dict(sessionId=SESSION, exists=True, running=True, terminal=False,
        evidencePending=True, events=None, calls=None, userMessages=None,
        rawUserMessages=None, frameworkNotices=None, promptObserved=False)


def test_live_pending_evidence_keeps_original_guest_budget(session):
    guest = Mock(identity={'runId': RUN})
    guest.status.return_value = dict(rawCalls=9, pendingCalls=1, stopped=False)
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps(live_observation()).encode()):
        value=session.poll(guest)
    assert value['terminal'] is False and value['rawCalls']==9 and value['pendingCalls']==1
    assert value['session']['userMessages'] is None


@pytest.mark.parametrize('change',[{'terminal':True},{'running':False},{'userMessages':0},
    {'promptObserved':True},{'evidencePending':False},{'running':1},{'exists':1},{'reason':'completed'}])
def test_pending_evidence_cannot_claim_known_or_terminal_result(session,change):
    with patch('backend.desktop_session.run_bounded', return_value=json.dumps({**live_observation(),**change}).encode()):
        with pytest.raises(ValueError):session.inspect()
