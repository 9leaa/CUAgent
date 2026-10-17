"""Original bindings and real ODS files; no GUI completion assertion."""
import json
import pytest
import calc_saved_artifact as module
from test_calc_workbook_verify import workbook, identity

RUN='calc-select-11111111-2222-3333-4444-555555555555'


@pytest.fixture
def task(tmp_path,monkeypatch):
    root=tmp_path/RUN;root.mkdir(mode=0o700)
    output=tmp_path/'saved.ods';output.write_bytes(workbook())
    data={'lease.json':dict(runId=RUN,stopped=True),
          'save-binding.json':dict(destination=str(output),parentIdentity=identity(tmp_path)),
          'input-binding.json':dict(cell='A2',approvedKind='text',approvedText='AbZ中文',
                                    inputApproved=True,commitApproved=True)}
    for name,value in data.items():
        path=root/name;path.write_text(json.dumps(value));path.chmod(0o600)
    original=module.workbook_destination
    def destination(run):
        original(run)
        return str(output)
    monkeypatch.setattr(module,'workbook_destination',destination)
    return root,output,data


def test_original_binding_readback_is_not_business_success(task):
    root,output,_=task
    before=output.read_bytes()
    report=module.verify_saved_artifact(root)
    assert report['runId']==RUN and report['text']=='AbZ中文'
    assert len(report['bindingSha256'])==3
    assert report['businessStatus']=='UNVERIFIED' and not report['reopenedVerified']
    assert output.read_bytes()==before


@pytest.mark.parametrize('fault',['active','wrong_run','wrong_path','wrong_text','missing_file','shared_binding','symlink'])
def test_reject_changed_scope_or_missing_artifact(task,fault):
    root,output,data=task
    if fault=='active':data['lease.json']['stopped']=False
    elif fault=='wrong_run':data['lease.json']['runId']='another'
    elif fault=='wrong_path':data['save-binding.json']['destination']='/tmp/other.ods'
    elif fault=='wrong_text':data['input-binding.json']['approvedText']='other'
    elif fault=='missing_file':output.unlink()
    for name,value in data.items():(root/name).write_text(json.dumps(value))
    if fault=='shared_binding':(root/'save-binding.json').chmod(0o644)
    elif fault=='symlink':
        p=root/'save-binding.json';p.rename(root/'original.json');p.symlink_to(root/'original.json')
    with pytest.raises((ValueError,OSError)):module.verify_saved_artifact(root)


def test_cli_refuses_host_before_reading(monkeypatch,capsys):
    def refuse():raise ValueError('host')
    monkeypatch.setattr(module,'require_vm',refuse)
    assert module.main(['--run',RUN])==1
    assert capsys.readouterr().err=='CALC_ARTIFACT_UNVERIFIED\n'
