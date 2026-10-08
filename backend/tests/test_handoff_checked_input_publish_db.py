"""Isolated test database and synthetic business evidence, not live publication."""
import json
import pytest
from sqlalchemy import select
from backend.models import Event
from backend.handoff_publication import publish_reviewed_task
from backend.tests.test_handoff_publish_db import ready
from backend.tests.test_handoff_operator import operator
from backend.tests.test_handoff_verify import evidence
from backend.tests.test_handoff_review import context

source,report=context()


@pytest.mark.parametrize('evidence',[dict(source=source,report=report,protocol='p7-tool-submit-v1',
    inputMode='checked-draft-v1')],indirect=True)
def test_mode_survives_publication_intent_and_database_event(service,ready):
    root,digest,identity,prepared=ready
    assert prepared['inputMode']=='checked-draft-v1'
    assert publish_reviewed_task(service,identity,digest)['status']=='SUCCEEDED'
    intent=json.loads((root/'handoff-publication-intent.json').read_bytes())
    assert intent['inputMode']=='checked-draft-v1'
    with service.sessions() as db:
        event=db.scalar(select(Event).where(Event.task_id==identity,Event.kind=='handoff_published'))
        assert event.data['inputMode']=='checked-draft-v1'
    assert service.view(identity)['status']=='SUCCEEDED'


@pytest.mark.parametrize('kind,protocol,mode',[('desktop-textedit','p7-tool-submit-v1','checked-draft-v1'),
    ('project-handoff','legacy-final-json','checked-draft-v1'),('project-handoff','p7-tool-submit-v1','auto')])
def test_operator_mode_rejected_before_any_io(kind,protocol,mode):
    from backend.desktop_operator import worker_once
    with pytest.raises(ValueError,match='UNSUPPORTED_HANDOFF_INPUT_MODE'):
        worker_once(profile_path='/missing',execution_path='/missing',quota_path='/missing',
            task_id='invalid',kind=kind,handoff_protocol=protocol,handoff_input_mode=mode)
