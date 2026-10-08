"""P7 binding to the official session lifecycle; no model loop or implicit start."""
from backend.desktop_collect import private_path, save_exclusive
from backend.desktop_session import DesktopSessionClient
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import canonical, input_digest


class HandoffSessionClient(DesktopSessionClient):
    def prepare(self, submission, *, protocol='legacy-final-json'):
        if protocol not in ('legacy-final-json', 'p7-tool-submit-v1'):
            raise ValueError('explicit supported handoff protocol required')
        submission = HandoffSubmission.model_validate(submission)
        workspace = private_path(self.root / 'workspace', directory=True)
        request = dict(kind='project-handoff', runId=self.root.name, sessionId=self.session_id,
                       cwd=str(workspace), inputSha256=input_digest(submission))
        if protocol == 'p7-tool-submit-v1':
            request['protocol'] = protocol
        save_exclusive(self.root / 'desktop-request.json', canonical(request))
