"""Offline proof for the applied-Submit/lost-response fault only.

No model, actions, control or verifier capability. This is not a C2 release
report: six other faults and the fixed 18 attempts remain separate gates.
"""
import argparse
import json
import re
from pathlib import Path
from c1_cases import C1_CASES

def audit_timeout(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('Evidence directory symlink')
    def read(name):
        path=directory/name
        if path.is_symlink():raise ValueError('Evidence file symlink')
        return path.read_text()
    rows=[json.loads(line) for line in read('trace.jsonl').splitlines()]
    verification=json.loads(read('verification.json'))
    case=verification['case_id']
    if case not in ('input_correction','window_change','cross_app'):raise ValueError('Unsupported fault case')
    dispatches=[r for r in rows if r['event']=='dispatch']
    calls={r['call_id'] for r in dispatches}
    if (len(calls)!=len(dispatches) or [r['used'] for r in dispatches]!=list(range(1,len(calls)+1))
        or not 0<len(calls)<=30 or len(calls)!=verification['raw_calls']):raise ValueError('Budget/call evidence differs')
    injected=[r for r in rows if r['event']=='c2_fault_injected']
    unknown=[r for r in rows if r['event']=='UNKNOWN']
    receipts=[r for r in rows if r['event']=='c2_reconciled_call']
    if len(injected)!=1 or injected[0].get('layer')!='after_actual_driver_response' or len(unknown)!=1 or len(receipts)!=1:
        raise ValueError('Need one genuine injected response loss and preserved UNKNOWN/receipt')
    lost=unknown[0];receipt=receipts[0]
    if lost['call_id']!=receipt['call_id'] or lost['tool']!='click' or receipt['verdict']!='applied':
        raise ValueError('Receipt does not match the uncertain input')
    original=next(r for r in dispatches if r['call_id']==lost['call_id'])
    if original.get('intent',{}).get('label')!='Submit' or original['intent']['snapshot_id']==receipt['snapshot_id']:
        raise ValueError('Need original Submit and different fresh proof')
    if (injected[0].get('fault')!='submit_response_timeout'
        or injected[0].get('intent')!=original['intent']
        or not rows.index(original)<rows.index(injected[0])<rows.index(lost)):
        raise ValueError('Injection does not match this original Submit')
    fresh=[r for r in rows if r['event']=='result' and r.get('tool')=='get_window_state'
           and r.get('value',{}).get('snapshot_id')==receipt['snapshot_id']]
    if len(fresh)!=1:raise ValueError('Receipt lacks one actual fresh Driver observation')
    state=fresh[0]['value'];expected=C1_CASES[case].expected
    displays=re.findall(r'^\s+- AXStaticText = "((?:Transferred|Submitted) [^"\n]+)"\s*$',state.get('tree_markdown','').split('\n- ',1)[0],re.M)
    if (state.get('pid')!=original['intent'].get('pid') or state.get('window_id')!=original['intent'].get('window_id')
        or receipt.get('pid')!=state.get('pid') or receipt.get('window_id')!=state.get('window_id')
        or not state.get('screenshot_frame_valid') or displays!=[expected]
        or not rows.index(original)<rows.index(lost)<rows.index(fresh[0])<rows.index(receipt)):
        raise ValueError('Fresh observation does not prove this original effect')
    effects=json.loads(read('c1-effects.json'))['effects']
    if sum(e in ('submit','destination-submit','transfer-submit') for e in effects)!=1:
        raise ValueError('Submit effect missing or duplicated')
    if sum(r['event']=='completed_action' and r.get('label')=='Submit' for r in rows)!=1:
        raise ValueError('Completed Submit missing or duplicated')
    actual_results={r['call_id'] for r in rows if r['event']=='result' and r.get('call_id')}
    if lost['call_id'] in actual_results:raise ValueError('Lost response cannot also be an ordinary success')
    if actual_results|{receipt['call_id']}!=calls:raise ValueError('Raw outcomes not fully accounted')
    owner='model';epoch=0;stop_seen=False;resumed=False
    for row in rows:
        if row['event']=='stop':owner='paused';stop_seen=True
        if row['event']=='c2_control':
            if (type(row['epoch']) is not int or row['epoch']!=epoch+1
                or row.get('policy')!='c2-ownership-v1'
                or row.get('owner') not in ('paused','human','model')):raise ValueError('Control epoch invalid')
            epoch=row['epoch'];owner=row['owner']
            if row['reason']=='explicit_resume':resumed=True
        if row['event']=='dispatch' and owner!='model':
            if (not row.get('recovery_observation') or row.get('control_epoch')!=epoch
                or row['tool'] not in ('list_windows','get_window_state')):raise ValueError('Dispatch while paused')
    if (not stop_seen or not resumed or verification['status']!='SUCCEEDED'
        or verification['fresh_display']!=verification['file_readback'] or verification['expected']!=expected
        or verification['fresh_display']!=expected or read('result.txt').strip()!=expected
        or verification.get('reconciled_calls')!=[receipt['call_id']]):raise ValueError('Final independent GUI/file proof missing')
    return {'gateStatus':'PASS','fault':'effect_then_timeout','caseId':case,'rawCalls':len(calls),
        'submitEffects':1,'unknownPreserved':True,'noBlindReplay':True,'originalBudget':True,
        'businessStatus':'SUCCEEDED','scope':'one applied Submit response-loss recovery, not C2 release'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    print(json.dumps(audit_timeout(parser.parse_args().directory)))
