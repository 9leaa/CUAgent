"""Composed P6 adapter. Deployment/cutover acceptance is mandatory and external.

No implicit activation: the operator supplies a live execution gate
that verifies the approved cutover, VM readiness and current quota >=40%.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import uuid

from backend.desktop_bootstrap import bootstrap_guest
from backend.desktop_client import DesktopControlClient
from backend.desktop_collect import collect_guest_bundle, private_path, run_bounded, save_exclusive
from backend.desktop_contract import DesktopSubmission
from backend.desktop_session import DesktopSessionClient
from backend.desktop_ssh import create_ssh_wrapper
from backend.desktop_tunnel import GuestControlTunnel, select_tunnel_port
from backend.desktop_verify import verify_desktop_session
from backend.desktop_usage import desktop_usage
from backend.desktop_prepare_cleanup import cleanup_prepared_guest
from backend.desktop_preparation import confirm_preparation_closed
from backend.desktop_worker import PreparedDesktop


@dataclass(frozen=True)
class DesktopAdapterSettings:
    node: Path
    official_home: Path
    cookie: Path
    build_tools: Path
    base_tasks: Path
    known_hosts: Path
    askpass: Path
    guest_commit: str
    guest_manifest_sha: str
    tunnel_port: int
    cutover_authorized: bool = False


class DesktopTaskAdapter:
    def submission(self, payload):
        return DesktopSubmission.model_validate(payload)

    def session_client(self, **kwargs):
        return DesktopSessionClient(**kwargs)

    def control_client(self, **kwargs):
        return DesktopControlClient(**kwargs)

    def profile_mode(self):
        return 'prepare'

    def app_mode(self):
        return 'start-p6'

    def connection(self, root, ready, submission):
        return {'runId': root.name, 'caseId': 'real_textedit', 'url': ready['modelUrl'], 'token': ready['modelToken']}

    def provision(self, prepared, context):
        pass  # P6 fixed lines have no materials provisioning step.

    def __init__(self, service, settings, *, execution_gate):
        if not isinstance(settings, DesktopAdapterSettings) or not callable(execution_gate):
            raise ValueError('explicit settings and live execution gate required')
        self.service, self.settings, self.execution_gate = service, settings, execution_gate
        self.contexts = {}
        self.cleaned_preparations = {}

    def gate(self, task):
        if self.settings.cutover_authorized is not True:
            raise RuntimeError('DESKTOP_CUTOVER_NOT_AUTHORIZED')
        if self.execution_gate(task) is not True:
            raise RuntimeError('DESKTOP_LIVE_EXECUTION_GATE_FAILED')
        self.service.desktop_authority(task.id, task.owner, task.epoch)

    def command(self, root, group, mode):
        settings = self.settings
        script = Path(__file__).resolve().parents[1] / 'agent/harness' / ('desktop-' + group + '-command.mjs')
        if group == 'profile':
            args = [str(settings.node), str(script), mode, str(root), str(settings.official_home), str(settings.build_tools)]
            expected = {'prepare': 'prepared', 'prepare-handoff': 'prepared', 'apply': 'applied', 'restore': 'restored'}[mode]
        elif group == 'app':
            launch = settings.base_tasks if mode == 'start-restore' else root / 'c0-connection.json'
            args = [str(settings.node), str(script), mode, str(root), str(settings.official_home), str(settings.cookie), str(launch)]
            expected = 'stopped' if mode.startswith('stop-') else 'started'
        else:
            raise ValueError('reviewed lifecycle command required')
        result = json.loads(run_bounded(args, b'', limit=65536, timeout=90))
        if not isinstance(result, dict) or result.get(expected) is not True:
            raise RuntimeError('DESKTOP_LIFECYCLE_COMMAND_UNCONFIRMED')
        return result

    def prepare(self, task):
        self.gate(task)
        submission = self.submission(task.payload)
        root = private_path(self.service.settings.root, directory=True) / ('p2-' + task.id)
        root.mkdir(mode=0o700)
        stage = ['local-preparation']
        resources = {}
        try:
            return self.prepare_at_root(task, submission, root, stage, resources)
        except Exception as error:
            guest_not_started = (stage[0] == 'tunnel-port-preflight'
                                 and resources.get('bootstrap_attempted') is False)
            cleanup_confirmed = False
            try:
                if 'tunnel' in resources:
                    resources['tunnel'].close()
                if 'ready' in resources:
                    cleanup_prepared_guest(root=root, ssh_wrapper=resources['wrapper'],
                                           ready=resources['ready'], owner=task.owner, epoch=task.epoch)
                    cleanup_confirmed = True
            except Exception:
                pass  # Unknown cleanup is never retried and remains quarantined.
            # Never serialize exception text/args: external errors may contain
            # credentials, URLs or process command lines.
            record = {'taskId': task.id, 'runId': root.name, 'stage': stage[0],
                      'category': 'OS_ERROR' if isinstance(error, OSError) else 'PREPARATION_ERROR',
                      'errno': error.errno if isinstance(error, OSError) and type(error.errno) is int else None,
                      'guestStartAttempted': os.path.lexists(root / 'desktop-guest-start-intent.json'),
                      'guestReceiptPresent': os.path.lexists(root / 'guest-private-receipt.json'),
                      'guestNotStarted': guest_not_started,
                      'binding': {'version': 1, 'runId': root.name, 'owner': task.owner, 'epoch': task.epoch},
                      'cleanupConfirmed': cleanup_confirmed}
            save_exclusive(root / 'desktop-prepare-failure.json', json.dumps(record).encode())
            if cleanup_confirmed or guest_not_started:
                self.cleaned_preparations[task.id] = (task, root, 'not-started' if guest_not_started else 'closed')
            raise

    def confirm_prepare_failure(self, task):
        original, root, guest_state = self.cleaned_preparations[task.id]
        if original is not task:
            raise ValueError('current preparation invocation required')
        return confirm_preparation_closed(root=root, home=self.settings.official_home, task=task, guest_state=guest_state)

    def prepare_at_root(self, task, submission, root, stage, resources):
        (root / 'workspace').mkdir(mode=0o700)
        wrapper = create_ssh_wrapper(root=root, known_hosts=self.settings.known_hosts, askpass=self.settings.askpass)
        resources['wrapper'] = wrapper
        session_id = 'session-' + str(uuid.uuid4())
        session = self.session_client(root=root, session_id=session_id, node=self.settings.node,
                                       official_home=self.settings.official_home, cookie=self.settings.cookie)
        session.prepare(submission)
        stage[0] = 'profile-prepare'
        self.command(root, 'profile', self.profile_mode())
        resources['bootstrap_attempted'] = False
        stage[0] = 'tunnel-port-preflight'
        tunnel_port = select_tunnel_port(self.settings.tunnel_port)
        save_exclusive(root / 'desktop-tunnel-selection.json', json.dumps({
            'binding': {'version': 1, 'runId': root.name, 'owner': task.owner, 'epoch': task.epoch},
            'preferredPort': self.settings.tunnel_port, 'hostPort': tunnel_port}).encode())
        stage[0] = 'guest-bootstrap'
        resources['bootstrap_attempted'] = True
        ready = bootstrap_guest(root=root, ssh_wrapper=wrapper,
                                commit=self.settings.guest_commit, manifest_sha=self.settings.guest_manifest_sha,
                                owner=task.owner, epoch=task.epoch)
        resources['ready'] = ready
        stage[0] = 'control-client'
        client = self.control_client(port=tunnel_port, token=ready['controlToken'],
                                      run_id=root.name, owner=task.owner, epoch=task.epoch)
        tunnel = GuestControlTunnel(root=root, ssh_wrapper=wrapper,
                                    guest_port=ready['controlPort'], client=client)
        resources['tunnel'] = tunnel
        stage[0] = 'tunnel-start'
        tunnel.start()
        stage[0] = 'connection-record'
        save_exclusive(root / 'c0-connection.json', json.dumps(self.connection(root, ready, submission)).encode())
        prepared = PreparedDesktop(root, session_id, client)
        self.contexts[root] = {'prepared': prepared, 'task': task, 'submission': submission,
                               'session': session, 'tunnel': tunnel, 'ssh_wrapper': wrapper, 'started': False}
        return prepared

    def context(self, prepared):
        context = self.contexts.get(prepared.run)
        if context is None or context['prepared'] is not prepared:
            raise ValueError('original prepared context required')
        return context

    def start(self, prepared):
        context = self.context(prepared)
        if context['started']:
            raise RuntimeError('DESKTOP_ADAPTER_START_ALREADY_ATTEMPTED')
        context['started'] = True
        self.gate(context['task'])
        self.provision(prepared, context)
        self.command(prepared.run, 'app', 'stop-activate')
        self.command(prepared.run, 'profile', 'apply')
        self.command(prepared.run, 'app', self.app_mode())
        task = context['task']
        prepared.control_client.activate(lambda: self.service.desktop_authority(
            task.id, task.owner, task.epoch, clock=prepared.control_client.clock))
        self.gate(task)  # Recheck quota/ownership immediately before official prompt.
        context['session'].start()

    def poll(self, prepared):
        return self.context(prepared)['session'].poll(prepared.control_client)

    def cancel(self, prepared):
        return self.context(prepared)['session'].cancel()

    def usage(self, prepared):
        self.context(prepared)
        return desktop_usage(prepared.run, prepared.session_id)

    def verify(self, prepared):
        context = self.context(prepared)
        bundle = collect_guest_bundle(root=prepared.run, ssh_wrapper=context['ssh_wrapper'],
            deployment='/Users/mvpagent/CUAgent-p6-' + self.settings.guest_commit,
            client=prepared.control_client, submission=context['submission'])
        report = verify_desktop_session(prepared.run, session_id=prepared.session_id,
                                       submission=context['submission'], guest_bundle=bundle)
        if report.get('sessionVerified') is not True:
            raise ValueError('independent session verification required')
        output = private_path(prepared.run / 'workspace', directory=True)
        files = {'document.txt': bundle['files']['artifacts/handoff-' + prepared.run.name + '.txt'],
                 'result.txt': bundle['files']['result.txt']}
        artifacts = {}
        for name, data in files.items():
            save_exclusive(output / name, data)  # Copy only verified VM bytes.
            artifacts[name] = hashlib.sha256(data).hexdigest()
        result = {'status': 'SUCCEEDED', 'kind': 'desktop-textedit', 'sessionId': prepared.session_id,
                  'artifacts': artifacts, 'session': report, 'rawCalls': bundle['guest']['rawCalls']}
        save_exclusive(prepared.run / 'desktop-verification.json', json.dumps(result).encode())
        context['verified_cleanup_hashes'] = {
            'document': artifacts['document.txt'], 'result': artifacts['result.txt'],
            'trace': hashlib.sha256(bundle['files']['trace.jsonl']).hexdigest()}
        return result

    def restore(self, prepared):
        context = self.context(prepared)
        self.command(prepared.run, 'app', 'stop-restore')
        self.command(prepared.run, 'profile', 'restore')
        self.command(prepared.run, 'app', 'start-restore')
        hashes = context.get('verified_cleanup_hashes')
        if hashes is None:
            save_exclusive(prepared.run / 'desktop-app-cleanup-skipped.json', json.dumps({
                'runId': prepared.run.name, 'status': 'SKIPPED',
                'reason': 'NO_INDEPENDENT_VERIFICATION', 'applicationMayRemain': True}).encode())
        else:
            save_exclusive(prepared.run / 'desktop-app-cleanup-intent.json', json.dumps({
                'runId': prepared.run.name, 'sessionId': prepared.session_id, 'hashes': hashes}).encode())
            try:
                receipt = prepared.control_client.cleanup_application(hashes)
                save_exclusive(prepared.run / 'desktop-app-cleanup-receipt.json', json.dumps(receipt).encode())
                if receipt['status'] != 'EXITED':
                    raise RuntimeError('DESKTOP_APP_CLEANUP_UNCONFIRMED')
            except Exception:
                save_exclusive(prepared.run / 'desktop-app-cleanup-warning.json', json.dumps({
                    'runId': prepared.run.name, 'reason': 'DESKTOP_APP_CLEANUP_UNCONFIRMED',
                    'retryAllowed': False}).encode())
                raise
        prepared.control_client.shutdown()
        context['tunnel'].close()
