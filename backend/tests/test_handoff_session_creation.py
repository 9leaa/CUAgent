import json
import sys
from pathlib import Path
import pytest
from backend.handoff_session_client import HandoffSessionClient
from backend.tests.test_handoff_result import fixture, RUN, SESSION


@pytest.mark.parametrize('protocol', ['legacy-final-json', 'p7-tool-submit-v1', 'unknown'])
def test_explicit_creation_protocol_preserves_original_request(tmp_path, protocol):
    root = tmp_path / RUN; root.mkdir(mode=0o700)
    (root / 'workspace').mkdir(mode=0o700)
    home = tmp_path / 'home'; home.mkdir(mode=0o700)
    cookie = tmp_path / 'cookie'; cookie.write_bytes(b'{}'); cookie.chmod(0o600)
    client = HandoffSessionClient(root=root, session_id=SESSION, node=Path(sys.executable).resolve(),
        official_home=home, cookie=cookie)
    source, _ = fixture()
    path = root / 'desktop-request.json'
    if protocol == 'unknown':
        with pytest.raises(ValueError): client.prepare(source, protocol=protocol)
        assert not path.exists()
        return
    client.prepare(source, protocol=protocol)
    original = path.read_bytes(); value = json.loads(original)
    assert value['sessionId'] == SESSION
    assert path.stat().st_mode & 0o777 == 0o600
    if protocol == 'p7-tool-submit-v1': assert value['protocol'] == protocol
    else: assert 'protocol' not in value
    with pytest.raises(FileExistsError): client.prepare(source, protocol='p7-tool-submit-v1')
    assert path.read_bytes() == original
