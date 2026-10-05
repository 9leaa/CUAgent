import io
import json
import secrets
from unittest.mock import Mock, patch
import pytest
from backend.handoff_client import HandoffControlClient
from backend.handoff_collect import collect_handoff_bundle
from backend.handoff_document import expected_document
from backend.handoff_verify import verify_handoff_execution
from backend.tests.test_handoff_verify import evidence
from backend.tests.test_handoff_result import fixture
from desktop_control import LeaseController
from desktop_export import write_bundle
from handoff_export import build_bundle


@pytest.fixture
def collector(evidence, tmp_path):
    args, _, _ = evidence
    binding = args['binding']; binding['owner'] = '11111111-1111-1111-1111-111111111111'
    guest = args['guest_directory']
    for name in ('handoff-input-intent.json', 'handoff-input-receipt.json'):
        path = guest / name; value = json.loads(path.read_bytes()); value['binding'] = binding
        path.write_text(json.dumps(value))
    controller = LeaseController(guest / 'lease.json', run_id=binding['runId'], owner=binding['owner'], epoch=1, clock=lambda: 100)
    controller.revoke()
    _, report = fixture()
    expected = expected_document(args['submission'], report, run_id=binding['runId'], session_id=args['session_id'])
    contents = build_bundle(guest, controller, (guest / 'handoff-input.json').read_bytes(), expected)
    out = io.BytesIO(); write_bundle(contents, out)
    wrapper = tmp_path / 'ssh'; wrapper.write_text('#!/bin/sh\nexit 1\n'); wrapper.chmod(0o700)
    client = HandoffControlClient(port=19001, token=secrets.token_urlsafe(32), run_id=binding['runId'], owner=binding['owner'], epoch=1)
    client.status = Mock(return_value=dict(stopped=True, pendingCalls=0, rawCalls=15))
    client.inspect = Mock(return_value=dict(lease=dict(binding, stopped=True)))
    yield dict(root=args['root'], ssh_wrapper=wrapper, deployment='/Users/mvpagent/CUAgent-p6-'+'a'*40,
               client=client, submission=args['submission'], expected=expected), out.getvalue(), args


def test_guest_export_host_decode_save_and_actual_combined_verification(collector):
    kwargs, raw, args = collector
    with patch('backend.handoff_collect.run_bounded', return_value=raw) as run:
        directory = collect_handoff_bundle(**kwargs)
        command, payload = run.call_args.args
        assert 'handoff_export.py' in command[-1] and 'ClearAllForwardings=yes' in command
        assert kwargs['client'].token not in str(command)
        assert set(json.loads(payload)) == {'materialsBase64', 'expectedBase64'}
        assert (kwargs['root'] / 'handoff-guest-evidence.tar').read_bytes() == raw
        assert all(p.stat().st_mode & 0o077 == 0 for p in directory.rglob('*'))
        result = verify_handoff_execution(**dict(args, guest_directory=directory))
        assert result['sessionVerified'] is True and result['semanticVerified'] is False
        with pytest.raises(FileExistsError): collect_handoff_bundle(**kwargs)
        run.assert_called_once()


@pytest.mark.parametrize('fault', ['active', 'pending', 'deployment', 'budget'])
def test_inadmissible_collection_never_starts_ssh(collector, fault):
    kwargs, _, _ = collector
    if fault == 'active': kwargs['client'].status.return_value['stopped'] = False
    if fault == 'pending': kwargs['client'].status.return_value['pendingCalls'] = 1
    if fault == 'budget': kwargs['client'].status.return_value['rawCalls'] = True
    if fault == 'deployment': kwargs['deployment'] += '; bad'
    with patch('backend.handoff_collect.run_bounded') as run:
        with pytest.raises(ValueError): collect_handoff_bundle(**kwargs)
        run.assert_not_called()


@pytest.mark.parametrize('fault', ['tar', 'state', 'lease', 'count', 'existing-directory', 'timeout'])
def test_failed_collection_retains_intent_and_never_retries(collector, fault):
    kwargs, raw, _ = collector
    if fault == 'tar': raw = b'bad archive'
    if fault == 'state': kwargs['client'].status.side_effect = [dict(stopped=True,pendingCalls=0,rawCalls=15), dict(stopped=True,pendingCalls=1,rawCalls=15)]
    if fault == 'lease': kwargs['client'].inspect.side_effect = [dict(lease=dict(stopped=True)),dict(lease=dict(stopped=False))]
    if fault == 'count': kwargs['client'].status.return_value['rawCalls'] = 16
    if fault == 'existing-directory': (kwargs['root'] / 'guest').mkdir(mode=0o700)
    with patch('backend.handoff_collect.run_bounded', return_value=raw, side_effect=RuntimeError('unknown') if fault=='timeout' else None) as run:
        with pytest.raises((ValueError, RuntimeError, FileExistsError)): collect_handoff_bundle(**kwargs)
        assert (kwargs['root'] / 'handoff-collection-intent.json').exists()
        assert not (kwargs['root'] / 'handoff-collection-receipt.json').exists()
        kwargs['client'].status.side_effect = None; kwargs['client'].inspect.side_effect = None
        with pytest.raises(FileExistsError): collect_handoff_bundle(**kwargs)
        run.assert_called_once()
