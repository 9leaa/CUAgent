"""P7 lifecycle composition. Semantic acceptance remains mandatory and pending."""
import os
import re
import stat
from backend.desktop_adapter import DesktopTaskAdapter
from backend.desktop_collect import private_path, save_exclusive
from backend.handoff_client import HandoffControlClient
from backend.handoff_session_client import HandoffSessionClient
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import canonical, input_digest
from backend.handoff_session import extract_handoff_result, strict_json, require
from backend.handoff_collect import collect_handoff_bundle
from backend.handoff_verify import verify_handoff_execution


class HandoffTaskAdapter(DesktopTaskAdapter):
    def __init__(self, service, settings, *, execution_gate, protocol='legacy-final-json'):
        if protocol not in ('legacy-final-json', 'p7-tool-submit-v1'):
            raise ValueError('UNSUPPORTED_HANDOFF_PROTOCOL')
        super().__init__(service, settings, execution_gate=execution_gate)
        self.protocol = protocol

    def prepare_session(self, session, submission):
        if self.protocol == 'legacy-final-json':
            session.prepare(submission)
        else:
            session.prepare(submission, protocol=self.protocol)

    def expected_binding(self, root, session_id, submission):
        value = dict(kind='project-handoff', runId=root.name, sessionId=session_id,
            cwd=str(root / 'workspace'), inputSha256=input_digest(submission))
        if self.protocol == 'p7-tool-submit-v1':
            value['protocol'] = self.protocol
        return value

    def submission(self, payload):
        return HandoffSubmission.model_validate(payload)

    def session_client(self, **kwargs):
        return HandoffSessionClient(**kwargs)

    def control_client(self, **kwargs):
        return HandoffControlClient(**kwargs)

    def profile_mode(self):
        return 'prepare-handoff'

    def app_mode(self):
        return 'start-p7'

    def connection(self, root, ready, submission):
        value = dict(runId=root.name, caseId='project_handoff', stage='p7', inputSha256=input_digest(submission),
                    url=ready['modelUrl'], token=ready['modelToken'])
        if self.protocol == 'p7-tool-submit-v1':
            from backend.desktop_service import read_private
            request = strict_json(read_private(root / 'desktop-request.json'))
            require(type(request) is dict and type(request.get('sessionId')) is str)
            require(re.fullmatch(r'session-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', request['sessionId']))
            require(request == self.expected_binding(root, request['sessionId'], submission))
            value.update(protocol=self.protocol, sessionId=request['sessionId'])
        return value

    def provision(self, prepared, context):
        task = context['task']
        if self.protocol == 'p7-tool-submit-v1':
            prepared.control_client.bind_draft_session(prepared.session_id, protocol=self.protocol)
        else:
            prepared.control_client.bind_draft_session(prepared.session_id)
        prepared.control_client.provision_handoff(context['submission'], lambda: self.service.desktop_authority(
            task.id, task.owner, task.epoch, clock=prepared.control_client.clock))

    def verify(self, prepared):
        context = self.context(prepared)
        def read(name, limit):
            path = private_path(prepared.run / name, directory=False)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as file:
                info = os.fstat(file.fileno())
                require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                        and not info.st_mode & 0o077 and 0 < info.st_size <= limit)
                raw = file.read(limit + 1)
                require(len(raw) == info.st_size)
                return raw
        submission = context['submission']
        binding = strict_json(read('desktop-session-binding.json', 32768).decode())
        require(binding == self.expected_binding(prepared.run, prepared.session_id, submission))
        if self.protocol == 'p7-tool-submit-v1':
            require(strict_json(read('desktop-request.json', 32768).decode()) == binding)
        raw = read('session.jsonl', 64*1024*1024)
        prompt = strict_json(read('prompt-request.json', 65536).decode())['request']
        extracted = extract_handoff_result(raw, submission=submission, run_id=prepared.run.name,
            session_id=prepared.session_id, cwd=binding['cwd'], prompt=prompt, protocol=self.protocol)
        directory = collect_handoff_bundle(root=prepared.run, ssh_wrapper=context['ssh_wrapper'],
            deployment='/Users/mvpagent/CUAgent-p6-' + self.settings.guest_commit, client=prepared.control_client,
            submission=submission, expected=extracted['document'])
        result = verify_handoff_execution(prepared.run, guest_directory=directory, home=self.settings.official_home,
            submission=submission, session_id=prepared.session_id, binding=prepared.control_client.identity, protocol=self.protocol)
        require(result['sessionSha256'] == extracted['sessionSha256'])
        require(directory == prepared.run / 'guest' / prepared.run.name)
        review = dict(version=1,
            submission=submission.model_dump(mode='json'), sessionId=prepared.session_id,
            binding=prepared.control_client.identity, home=str(self.settings.official_home))
        if self.protocol == 'p7-tool-submit-v1':
            review.update(version=2, protocol=self.protocol)
        save_exclusive(prepared.run / 'handoff-review-context.json', canonical(review))
        save_exclusive(prepared.run / 'handoff-execution-verification.json', canonical(result))
        # Saved-byte/session evidence permits a normal owned-app exit, not
        # semantic acceptance or publication. Guest rechecks these files.
        names = {'document': 'artifacts/handoff-' + prepared.run.name + '.txt',
                 'result': 'result.txt', 'trace': 'trace.jsonl'}
        context['verified_cleanup_hashes'] = {
            key: result['guest']['files'][name]['sha256'] for key, name in names.items()}
        # The Worker catches verification failures as UNVERIFIED. Never issue
        # success artifacts solely from execution evidence.
        raise ValueError('HANDOFF_SEMANTIC_REVIEW_REQUIRED')
