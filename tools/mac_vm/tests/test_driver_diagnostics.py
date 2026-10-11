"""Simulated subprocess only; no GUI or model invocation."""
import hashlib
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from driver_smoke import Calls, DriverCallError


@pytest.mark.parametrize('code,out,reason', [(1,'{}','nonzero_exit'),
    (0,'not-json','invalid_json'), (0,'[]','invalid_shape')])
def test_structured_private_error(code,out,reason):
    with patch('driver_smoke.subprocess.run',return_value=SimpleNamespace(
            returncode=code,stdout=out,stderr='driver detail')) as run:
        with pytest.raises(DriverCallError) as caught: Calls.cli('type_text',{'text':'private argument'})
    assert run.call_count==1
    e=caught.value
    assert e.diagnostic['reason']==reason and e.diagnostic['returncode']==code
    assert e.diagnostic['stderr']['preview']=='driver detail'
    assert 'driver detail' not in str(e) and 'private argument' not in str(e.diagnostic)


def test_timeout_bytes_bounded_and_not_retried():
    raw=('文'*2000).encode()
    with patch('driver_smoke.subprocess.run',side_effect=subprocess.TimeoutExpired(
            'driver',35,output=raw,stderr=b'partial')) as run:
        with pytest.raises(DriverCallError) as caught: Calls.cli('type_text',{})
    d=caught.value.diagnostic
    assert run.call_count==1 and d['reason']=='timeout' and d['returncode'] is None
    assert d['stdout']['bytes']==6000 and d['stdout']['truncated']
    assert d['stdout']['sha256']==hashlib.sha256(raw).hexdigest()
    assert d['stdout']['preview']==raw[:4096].decode('utf-8',errors='replace')


def test_success_unchanged():
    with patch('driver_smoke.subprocess.run',return_value=SimpleNamespace(
            returncode=0,stdout='{"ok":true}',stderr='')):
        assert Calls.cli('get_window_state',{})=={'ok':True}
