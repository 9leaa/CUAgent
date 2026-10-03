from dataclasses import replace
import json
import os
import sys
from unittest.mock import Mock

from fastapi.testclient import TestClient
import httpx
import pytest

from backend import client
from backend.api import create_app


def invoke(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, 'argv', ['cuagent-client', *map(str, args)])
    client.main()
    return json.loads(capsys.readouterr().out)


def configured_api(service, monkeypatch, *, enabled):
    app = create_app(replace(service.settings, desktop_tasks_enabled=enabled))
    def connect(**options):
        assert options['base_url'] == 'http://127.0.0.1:18089'
        assert options['trust_env'] is False
        return TestClient(app, headers=options['headers'])
    monkeypatch.setattr(client, 'load_env', lambda: {'CUAGENT_BACKEND_TOKEN': service.settings.api_token})
    monkeypatch.setattr(client.httpx, 'Client', connect)
    return app


def test_cli_real_api_pg_submit_idempotency_conflict_and_stop(service, tmp_path, monkeypatch, capsys):
    configured_api(service, monkeypatch, enabled=True)
    spec = tmp_path / 'desktop.json'
    spec.write_text(json.dumps({'kind': 'desktop-textedit', 'lines': ['项目：交接', '状态：待核对']}))
    one = invoke(monkeypatch, capsys, 'desktop-submit', '--spec', spec, '--key', 'same-request')
    two = invoke(monkeypatch, capsys, 'desktop-submit', '--spec', spec, '--key', 'same-request')
    assert one['created'] and not two['created'] and one['id'] == two['id']
    state = invoke(monkeypatch, capsys, 'status', '--task', one['id'])
    assert state['status'] == 'QUEUED' and state['kind'] == 'desktop-textedit'
    spec.write_text(json.dumps({'kind': 'desktop-textedit', 'lines': ['changed']}))
    with pytest.raises(httpx.HTTPStatusError) as error:
        invoke(monkeypatch, capsys, 'desktop-submit', '--spec', spec, '--key', 'same-request')
    assert error.value.response.status_code == 409
    invoke(monkeypatch, capsys, 'stop', '--task', one['id'])
    state = service.view(one['id'])
    assert state['status'] == 'STOPPED' and state['budget']['used'] == 0 and state['session_id'] is None


def test_cli_does_not_enable_default_api(service, tmp_path, monkeypatch, capsys):
    configured_api(service, monkeypatch, enabled=False)
    spec = tmp_path / 'desktop.json'
    spec.write_text('{"kind":"desktop-textedit","lines":["test"]}')
    with pytest.raises(httpx.HTTPStatusError) as error:
        invoke(monkeypatch, capsys, 'desktop-submit', '--spec', spec, '--key', 'disabled')
    assert error.value.response.status_code == 503
    assert service.claim('not-a-model-worker', kind='desktop-textedit') is None


@pytest.mark.parametrize('raw', [
    b'{"kind":"desktop-textedit","lines":["ok"],"lines":["replaced"]}',
    b'{"kind":"desktop-textedit","lines":["ok"],"budget":300}',
    b'{"kind":"desktop-textedit","lines":["a\\nb"]}',
    b'{"kind":"desktop-textedit","lines":[1]}',
    b'{"kind":"desktop-textedit","lines":[]}',
    b'[]', b'\xff', b' ' * 32769,
])
def test_invalid_spec_never_posts(tmp_path, monkeypatch, capsys, raw):
    spec = tmp_path / 'desktop.json'; spec.write_bytes(raw)
    transport = Mock(); transport.__enter__ = Mock(return_value=transport)
    transport.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(client, 'load_env', lambda: {'CUAGENT_BACKEND_TOKEN': 'private'})
    monkeypatch.setattr(client.httpx, 'Client', lambda **_: transport)
    with pytest.raises(ValueError):
        invoke(monkeypatch, capsys, 'desktop-submit', '--spec', spec, '--key', 'valid')
    transport.post.assert_not_called()


def test_spec_refuses_symlink_directory_and_fifo(tmp_path):
    spec = tmp_path / 'desktop.json'; spec.write_text('{"kind":"desktop-textedit","lines":["ok"]}')
    link = tmp_path / 'link'; link.symlink_to(spec)
    fifo = tmp_path / 'fifo'; os.mkfifo(fifo)
    for path in (link, tmp_path, fifo):
        with pytest.raises((ValueError, OSError)):
            client.desktop_spec(path)


def test_unknown_post_outcome_is_not_retried(tmp_path, monkeypatch, capsys):
    spec = tmp_path / 'desktop.json'; spec.write_text('{"kind":"desktop-textedit","lines":["ok"]}')
    transport = Mock(); transport.__enter__ = Mock(return_value=transport)
    transport.__exit__ = Mock(return_value=False)
    transport.post.side_effect = httpx.ReadTimeout('response unknown')
    monkeypatch.setattr(client, 'load_env', lambda: {'CUAGENT_BACKEND_TOKEN': 'private'})
    monkeypatch.setattr(client.httpx, 'Client', lambda **_: transport)
    with pytest.raises(httpx.ReadTimeout):
        invoke(monkeypatch, capsys, 'desktop-submit', '--spec', spec, '--key', 'preserve-key')
    transport.post.assert_called_once_with('/desktop-tasks', json={'kind': 'desktop-textedit', 'lines': ['ok']},
                                           headers={'Idempotency-Key': 'preserve-key'})


@pytest.mark.parametrize('extra', [[], ['--key', ''], ['--key', 'a/b'], ['--key', 'x' * 81]])
def test_invalid_or_missing_key_never_posts(tmp_path, monkeypatch, capsys, extra):
    spec = tmp_path / 'desktop.json'
    spec.write_text('{"kind":"desktop-textedit","lines":["ok"]}')
    transport = Mock(); transport.__enter__ = Mock(return_value=transport)
    transport.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(client, 'load_env', lambda: {'CUAGENT_BACKEND_TOKEN': 'private'})
    monkeypatch.setattr(client.httpx, 'Client', lambda **_: transport)
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, capsys, 'desktop-submit', '--spec', spec, *extra)
    assert error.value.code == 2
    transport.post.assert_not_called()
