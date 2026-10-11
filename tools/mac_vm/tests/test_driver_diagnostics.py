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


@pytest.mark.parametrize('detail', ['', 'exact target window did not become focused', '文'*2000])
def test_foreground_code_and_separate_cause_are_private_and_bounded(detail):
    out='{"code":"foreground_unavailable"}'
    with patch('driver_smoke.subprocess.run',return_value=SimpleNamespace(
            returncode=1,stdout=out,stderr=detail)) as run:
        with pytest.raises(DriverCallError) as caught:
            Calls.cli('click',{'pid':10,'window_id':20,'x':410,'y':40,'delivery_mode':'foreground'})
    assert run.call_count==1
    d=caught.value.diagnostic
    assert d['stdout']['preview']==out and d['returncode']==1
    raw=detail.encode()
    assert d['stderr']['preview']==raw[:4096].decode('utf-8',errors='replace')
    assert d['stderr']['sha256']==hashlib.sha256(raw).hexdigest()
    assert d['stderr']['truncated']==(len(raw)>4096)
    assert str(caught.value)=='Driver call failed: nonzero_exit'
