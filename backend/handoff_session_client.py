"""P7 binding to the official session lifecycle; no model loop or implicit start."""
from backend.desktop_collect import private_path, save_exclusive
from backend.desktop_session import DesktopSessionClient
from backend.handoff_contract import HandoffSubmission
from backend.handoff_result import canonical, input_digest
from backend.handoff_session import handoff_tools


class HandoffSessionClient(DesktopSessionClient):
    def prepare(self, submission, *, protocol='legacy-final-json', draft_input_mode='literal-text'):
        handoff_tools(protocol, draft_input_mode)
        submission = HandoffSubmission.model_validate(submission)
        workspace = private_path(self.root / 'workspace', directory=True)
        request = dict(kind='project-handoff', runId=self.root.name, sessionId=self.session_id,
                       cwd=str(workspace), inputSha256=input_digest(submission))
        if protocol == 'p7-tool-submit-v1':
            request['protocol'] = protocol
        if draft_input_mode == 'checked-draft-v1':
            request['inputMode'] = draft_input_mode
        save_exclusive(self.root / 'desktop-request.json', canonical(request))
