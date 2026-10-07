"""Authenticated loopback HTTP against original task, without GUI/model."""
from http.client import HTTPConnection
import json
import secrets
import threading
import pytest
from backend.tests.test_handoff_draft_task import task
from desktop_tools_http import tools_server


@pytest.fixture
def http(task):
    t, controller, report = task
    token = secrets.token_urlsafe(32)
    server = tools_server(t, token, control_token=secrets.token_urlsafe(32), port=0, loopback_test=True)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}); thread.start()
    def request(args, op='check_draft', credential=token):
        conn = HTTPConnection(*server.server_address, timeout=3)
        try:
            conn.request('POST', '/', json.dumps(dict(op=op, args=args)), {'Authorization': 'Bearer ' + credential})
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally: conn.close()
    try: yield t, controller, report, request
    finally: server.shutdown(); server.server_close(); thread.join(3)


def test_valid_and_bad_draft_use_original_budget_once(http):
    t, _, report, request = http
    assert request({'raw': '{broken'})[1]['used'] == 1
    code, response = request({'raw': json.dumps(report)})
    assert code == 200 and response['status'] == 'DRAFT_STRUCTURE_VALID' and response['used'] == 2
    assert request({'raw': '{}', 'sessionId': 'other'}) == (409, {'error': 'DESKTOP_REQUEST_REJECTED', 'used': 3})
    assert t.used == 3 and t.validated_draft is None


def test_larger_envelope_only_for_bounded_raw_draft(http):
    t, _, report, request = http
    raw = ' ' * 40000 + json.dumps(report)
    assert request({'raw': raw})[1]['status'] == 'DRAFT_STRUCTURE_VALID'
    assert request({'raw': 'x' * 65537})[0] == 409
    assert request({'text': 'x' * 40000}, op='type_text')[0] == 409
    assert t.used == 3


def test_unauthorized_stop_and_original_thirty_limit(http):
    t, _, _, request = http
    assert request({'raw': '{}'}, credential='wrong')[0] == 403 and t.used == 0
    for used in range(1, 31): assert request({'raw': '{}'})[1]['used'] == used
    assert request({'raw': '{}'})[0] == 409 and t.used == 30


def test_revoked_does_not_dispatch(http):
    t, controller, _, request = http
    request({'raw': '{}'}); controller.revoke()
    assert request({'raw': '{}'})[0] == 409 and t.used == 1


def test_input_gate_http_refusal_is_charged(http):
    t, _, _, request = http
    assert request({'text': 'not validated'}, op='type_text')[0] == 409
    assert t.used == 1 and not t.input_once
