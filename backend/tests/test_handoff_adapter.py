from dataclasses import replace
import json
import shutil
from unittest.mock import Mock, patch
import pytest
from backend.handoff_adapter import HandoffTaskAdapter
from backend.desktop_worker import PreparedDesktop
from backend.handoff_result import input_digest
from backend.tests.test_desktop_adapter import assembled
from backend.tests.test_handoff_verify import evidence
from backend.tests.test_handoff_result import fixture


@pytest.fixture
def handoff(assembled):
    original, task, _, _, tunnel, gate = assembled
    task.payload = fixture()[0].model_dump(mode='json')
    adapter = HandoffTaskAdapter(original.service, original.settings, execution_gate=gate)
    adapter.command = Mock()
    with patch('backend.handoff_adapter.HandoffSessionClient') as session, patch('backend.handoff_adapter.HandoffControlClient') as client:
        yield adapter, task, session.return_value, client.return_value, tunnel, gate


def test_prepare_start_materials_before_app_and_prompt_once(handoff):
    adapter, task, session, client, _, gate = handoff
    prepared = adapter.prepare(task)
    session.start.assert_not_called(); client.provision_handoff.assert_not_called()
    connection = json.loads((prepared.run / 'c0-connection.json').read_bytes())
    assert connection['stage'] == 'p7' and connection['caseId'] == 'project_handoff'
    assert connection['inputSha256'] == input_digest(fixture()[0])
    sequence = []
    client.provision_handoff.side_effect = lambda *args: sequence.append('provision')
    adapter.command.side_effect = lambda *args: sequence.append(args[-1])
    client.activate.side_effect = lambda *args: sequence.append('activate')
    session.start.side_effect = lambda: sequence.append('prompt')
    adapter.start(prepared)
    assert sequence == ['provision', 'stop-activate', 'apply', 'start-p7', 'activate', 'prompt']
    assert gate.call_count == 3
    with pytest.raises(RuntimeError): adapter.start(prepared)
    client.provision_handoff.assert_called_once(); session.start.assert_called_once()
    authority = client.provision_handoff.call_args.args[1]; authority()
    assert adapter.service.desktop_authority.call_args.args == (task.id, task.owner, task.epoch)


def test_provision_unknown_cannot_switch_app_prompt_or_retry(handoff):
    adapter, task, session, client, _, _ = handoff
    prepared = adapter.prepare(task); adapter.command.reset_mock()
    client.provision_handoff.side_effect = RuntimeError('unknown')
    with pytest.raises(RuntimeError): adapter.start(prepared)
    with pytest.raises(RuntimeError): adapter.start(prepared)
    adapter.command.assert_not_called(); session.start.assert_not_called(); client.activate.assert_not_called()
    client.provision_handoff.assert_called_once()


def test_wrong_kind_is_rejected_before_guest_bootstrap(handoff):
    adapter, task, session, client, _, _ = handoff
    task.payload = dict(kind='desktop-textedit', lines=['x'])
    with pytest.raises(ValueError): adapter.prepare(task)
    session.prepare.assert_not_called(); client.activate.assert_not_called()


@pytest.mark.parametrize('evidence', ['with_draft', 'with_submit'], indirect=True)
def test_real_combined_evidence_allows_saved_app_cleanup_but_not_success(handoff, evidence):
    adapter, _, _, _, _, _ = handoff
    args, _, _ = evidence
    original_binding = json.loads((args['root'] / 'desktop-session-binding.json').read_bytes())
    adapter.protocol = original_binding.get('protocol', 'legacy-final-json')
    adapter.settings = replace(adapter.settings, official_home=args['home'])
    control = Mock(identity=args['binding'])
    prepared = PreparedDesktop(args['root'], args['session_id'], control)
    adapter.contexts[prepared.run] = dict(prepared=prepared, submission=args['submission'], ssh_wrapper='unused')
    directory = prepared.run / 'guest' / prepared.run.name
    directory.parent.mkdir(mode=0o700)
    shutil.copytree(args['guest_directory'], directory)
    with patch('backend.handoff_adapter.collect_handoff_bundle', return_value=directory):
        with pytest.raises(ValueError, match='HANDOFF_SEMANTIC_REVIEW_REQUIRED'): adapter.verify(prepared)
    result = json.loads((prepared.run / 'handoff-execution-verification.json').read_bytes())
    assert result['sessionVerified'] is True and result['semanticVerified'] is False
    assert json.loads((prepared.run / 'handoff-review-context.json').read_bytes())['binding'] == args['binding']
    review = json.loads((prepared.run / 'handoff-review-context.json').read_bytes())
    assert review['version'] == (2 if adapter.protocol == 'p7-tool-submit-v1' else 1)
    assert review.get('protocol', 'legacy-final-json') == adapter.protocol
    hashes = adapter.context(prepared)['verified_cleanup_hashes']
    assert hashes == {key: result['guest']['files'][name]['sha256'] for key, name in {
        'document': 'artifacts/handoff-' + prepared.run.name + '.txt',
        'result': 'result.txt', 'trace': 'trace.jsonl'}.items()}
    assert not (prepared.run / 'desktop-verification.json').exists()
    assert not (prepared.run / 'workspace/document.txt').exists()
    control.cleanup_application.assert_not_called()


def test_new_adapter_prepare_freezes_protocol_and_activation(handoff):
    adapter, task, session, client, _, _ = handoff
    adapter.protocol = 'p7-tool-submit-v1'
    # The session factory is mocked in this fixture; materialize exactly the
    # original request that the real session client's prepare writes.
    with patch('backend.handoff_adapter.HandoffSessionClient') as factory:
        factory.return_value = session
        def prepare(source, *, protocol):
            kwargs = factory.call_args.kwargs
            path = kwargs['root'] / 'desktop-request.json'
            path.write_text(json.dumps(adapter.expected_binding(kwargs['root'], kwargs['session_id'], source)))
            path.chmod(0o600)
        session.prepare.side_effect = prepare
        prepared = adapter.prepare(task)
    session.prepare.assert_called_once_with(fixture()[0], protocol='p7-tool-submit-v1')
    connection = json.loads((prepared.run / 'c0-connection.json').read_bytes())
    assert connection['sessionId'] == prepared.session_id and connection['protocol'] == adapter.protocol
    adapter.start(prepared)
    client.bind_draft_session.assert_called_once_with(prepared.session_id, protocol=adapter.protocol)
    with pytest.raises(RuntimeError): adapter.start(prepared)


@pytest.mark.parametrize('fault', ['missing', 'protocol', 'session', 'input', 'public'])
def test_new_connection_requires_original_private_creation(handoff, tmp_path, fault):
    adapter, _, _, _, _, _ = handoff
    adapter.protocol = 'p7-tool-submit-v1'
    source, _ = fixture()
    root = tmp_path / 'run'; root.mkdir(mode=0o700)
    data = adapter.expected_binding(root, 'session-22222222-2222-2222-2222-222222222222', source)
    if fault == 'protocol': data['protocol'] = 'legacy-final-json'
    if fault == 'session': data['sessionId'] = 'wrong'
    if fault == 'input': data['inputSha256'] = '0' * 64
    if fault != 'missing':
        path = root / 'desktop-request.json'; path.write_text(json.dumps(data)); path.chmod(0o644 if fault == 'public' else 0o600)
    with pytest.raises((ValueError, OSError)):
        adapter.connection(root, dict(modelUrl='unused', modelToken='unused'), source)


def test_bad_original_session_never_collects_guest(handoff, evidence):
    adapter, _, _, _, _, _ = handoff; args, _, _ = evidence
    prepared = PreparedDesktop(args['root'], args['session_id'], Mock(identity=args['binding']))
    adapter.contexts[prepared.run] = dict(prepared=prepared, submission=args['submission'], ssh_wrapper='unused')
    (prepared.run / 'session.jsonl').write_bytes(b'bad')
    with patch('backend.handoff_adapter.collect_handoff_bundle') as collect:
        with pytest.raises(ValueError): adapter.verify(prepared)
        collect.assert_not_called()
