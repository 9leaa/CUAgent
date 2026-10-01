"""Offline proof for the one closed/reopened-window diagnostic, not C2 release."""
import argparse
import json
from pathlib import Path


def audit_window(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('Evidence directory symlink')
    def read(name):
        path=directory/name
        if path.is_symlink():raise ValueError('Evidence file symlink')
        return path.read_text()
    rows=[json.loads(line) for line in read('trace.jsonl').splitlines()]
    def unique(event):
        found=[r for r in rows if r['event']==event]
        if len(found)!=1:raise ValueError('Need one '+event)
        return found[0]
    dispatches=[r for r in rows if r['event']=='dispatch']
    results=[r for r in rows if r['event']=='result' and r.get('call_id')]
    if (not 0<len(dispatches)<=30 or any(type(r.get('used')) is not int for r in dispatches) or [r['used'] for r in dispatches]!=list(range(1,len(dispatches)+1))
        or len({r['call_id'] for r in dispatches})!=len(dispatches)
        or len({r['call_id'] for r in results})!=len(results)
        or {r['call_id'] for r in dispatches}!={r['call_id'] for r in results}
        or any(r['event']=='UNKNOWN' for r in rows)):raise ValueError('Incomplete continuous original budget')
    attempted=unique('c2_window_close_attempt');closed=unique('c2_window_closed')
    injected=unique('c2_fault_injected');reopened=unique('c2_window_reopen_requested')
    if (injected.get('fault')!='window_close_after_observe'
        or injected.get('layer')!='actual_driver_close_and_fresh_inventory'
        or not rows.index(attempted)<rows.index(closed)<rows.index(reopened)
        or attempted['pid']!=closed['pid'] or attempted['window_id']!=closed['window_id']
        or reopened['pid']!=closed['pid'] or reopened['old_window_id']!=closed['window_id']):
        raise ValueError('Different original target or missing actual fault')
    before=[r for r in results if r.get('tool')=='get_window_state' and r.get('value',{}).get('snapshot_id')==attempted['snapshot_id']]
    if len(before)!=1 or rows.index(before[0])>=rows.index(attempted):raise ValueError('Fresh original close observation missing')
    state=before[0]['value'];bounds=state.get('window_bounds',{})
    roots={e['element_index'] for e in state.get('elements',[]) if e.get('role')=='AXWindow' and e.get('label')=='CUAgent Correction'}
    buttons=[e for e in state.get('elements',[]) if e.get('element_index')==attempted['element_index'] and e.get('element_token')==attempted['element_token']]
    if len(buttons)!=1:raise ValueError('Close target not grounded in actual observation')
    button=buttons[0];frame=button.get('frame',{})
    if (state.get('pid')!=closed['pid'] or state.get('window_id')!=closed['window_id'] or not state.get('screenshot_frame_valid')
        or button.get('role')!='AXButton' or button.get('label') or button.get('parent_index') not in roots
        or button.get('enabled') is not True or 'AXPress' not in button.get('actions',[])
        or not all(k in frame for k in ('x','y','w','h')) or not all(k in bounds for k in ('x','y'))
        or not 0<frame['w']<=22 or not 0<frame['h']<=22 or not 0<=frame['x']-bounds['x']<=28 or not 0<=frame['y']-bounds['y']<=28):
        raise ValueError('Close is not the original observed title-bar button')
    closing=rows[rows.index(attempted)+1:rows.index(closed)]
    clicks=[r for r in closing if r['event']=='dispatch' and r['tool']=='click']
    inventories=[r['value'].get('windows',[]) for r in closing if r['event']=='result' and r.get('tool')=='list_windows']
    if len(clicks)!=1 or not inventories or any(w.get('pid')==closed['pid'] and w.get('window_id')==closed['window_id'] and w.get('is_on_screen') for w in inventories[-1]):
        raise ValueError('Actual close or old-window disappearance missing')
    activations=[r for r in dispatches if r['tool']=='reopen_task_application']
    if len(activations)!=1 or not rows.index(closed)<rows.index(activations[0])<rows.index(reopened):
        raise ValueError('Need one budgeted native reopen request')
    states=[r for r in results if r.get('tool')=='get_window_state' and rows.index(r)>rows.index(reopened)]
    if not states or any(r['value'].get('pid')!=closed['pid'] or r['value'].get('window_id')==closed['window_id'] or not r['value'].get('screenshot_frame_valid') for r in states):
        raise ValueError('Need actual fresh different-window observation in original process')
    resumes=[r for r in rows if r['event']=='c2_control' and r.get('reason')=='explicit_resume']
    if len(resumes)!=1 or rows.index(states[0])>rows.index(resumes[0]):raise ValueError('Resume before new window proof')
    owner='model';epoch=0
    for row in rows:
        if row['event']=='stop':owner='paused'
        if row['event']=='c2_control':
            if (type(row['epoch']) is not int or row['epoch']!=epoch+1 or row['owner'] not in ('model','human','paused')
                or row.get('policy')!='c2-ownership-v1'):
                raise ValueError('Invalid control epoch')
            owner=row['owner'];epoch=row['epoch']
        if row['event']=='dispatch' and owner!='model':
            observation=row.get('recovery_observation') and row['tool'] in ('list_windows','get_window_state')
            developer=owner=='human' and row.get('developer_control') and row['tool'] in ('list_windows','click','reopen_task_application')
            if row.get('control_epoch')!=epoch or not (observation or developer):raise ValueError('Uncontrolled paused dispatch')
    rejected=[r for r in results if r.get('tool')=='rejected_click' and r.get('value',{}).get('reason')=='Fresh observation required']
    if not rejected or not any(rows.index(r)>rows.index(resumes[0]) for r in rejected):raise ValueError('Old observation refusal missing')
    effects=json.loads(read('c1-effects.json'))['effects']
    verification=json.loads(read('verification.json'))
    expected='Submitted cedar-42'
    if (effects!=['initial-value:cedra-42','corrected-value:cedar-42','submit']
        or verification.get('status')!='SUCCEEDED' or verification.get('case_id')!='input_correction'
        or verification.get('raw_calls')!=len(dispatches) or verification.get('actions')!=['Submit']
        or not verification.get('fresh_display')==verification.get('file_readback')==verification.get('expected')==read('result.txt').strip()==expected):
        raise ValueError('Original task effect or independent business proof differs')
    return {'gateStatus':'PASS','fault':'window_closed','rawCalls':len(dispatches),
        'originalPID':closed['pid'],'closedWindow':closed['window_id'],'newWindow':states[0]['value']['window_id'],
        'oldObservationRefused':True,'originalBudget':True,'submitEffects':1,
        'scope':'one window-close diagnostic, not complete C2 release'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    print(json.dumps(audit_window(parser.parse_args().directory)))
