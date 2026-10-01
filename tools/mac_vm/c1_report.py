"""Offline C1 report validation; never executes VM/model actions.

Reports remain evidence summaries, not replacements for the underlying traces.
Missing before/after attempts are errors, not filtered-out failures.
"""
import argparse
import json
import statistics
import subprocess
from pathlib import Path
from c1_cases import C1_CASES, PHASES, REPETITIONS, RAW_BUDGET

MODEL='deepseek-account/deepseek-flash'
TOKEN_FIELDS=('inputTokens','outputTokens','cacheReadTokens','cacheWriteTokens','totalTokens')

def measured_usage(events):
    messages=[event.get('data',{}) for event in events if event.get('type')=='assistant/message']
    complete=bool(messages) and all(isinstance(message.get('usage'),dict)
        and all(type(message['usage'].get(key)) is int and message['usage'][key]>=0 for key in TOKEN_FIELDS)
        for message in messages)
    return {'available':complete,'assistantMessages':len(messages),
        **{key:sum(message['usage'][key] for message in messages) if complete else None for key in TOKEN_FIELDS},
        'currencyCost':None,'costNote':'Official session token usage only; no currency price inferred'}

def validate_session(events, row):
    endings=[event for event in events if event.get('type')=='turn/end']
    starts=[event for event in events if event.get('type')=='turn/start']
    if len(endings)!=1 or len(starts)!=1:
        raise ValueError('Expected one actual terminal model turn per fixed trial')
    if endings[0].get('data',{}).get('reason')!=row.get('terminalReason'):
        raise ValueError('Reported terminal state differs from official session')
    calls=sum(event.get('type')=='tool/call' for event in events)
    if calls!=row.get('modelToolCalls'):
        raise ValueError('Model tool count differs from actual session')

def session_events(runtime, session_id):
    if not session_id.startswith('session-') or '/' in session_id or '..' in session_id:
        raise ValueError('Invalid session identity')
    files=list((Path(runtime)/'desktop-home'/'sessions').glob(f'*/{session_id}/session.v4.jsonl.zstd'))
    if len(files)!=1 or files[0].is_symlink():
        raise ValueError('Missing or ambiguous official session evidence')
    output=subprocess.run(['zstd','-dc',str(files[0])],check=True,capture_output=True,text=True).stdout
    return [json.loads(line) for line in output.splitlines()]

def promotion_review(reports, *, safety_passed=False):
    """Apply the criteria declared before implementation; no implicit promotion.

    Safety results must come from the separate regression run, not trial success.
    """
    before=reports['baseline'];after=reports['after']
    baseline=before['perCase']['popup']['rawCalls']
    candidate=after['perCase']['popup']['rawCalls']
    if len(baseline)!=REPETITIONS or len(candidate)!=REPETITIONS:
        raise ValueError('Promotion requires all fixed popup repetitions')
    median=statistics.median(baseline)
    lower=sum(value<median for value in candidate)
    no_regression=all(after['perCase'][case]['passed']>=before['perCase'][case]['passed'] for case in C1_CASES)
    cost_passed=lower>=2 and statistics.mean(candidate)<statistics.mean(baseline)
    return {'baselinePopupMedian':median,'baselinePopupMean':statistics.mean(baseline),
        'candidatePopupMean':statistics.mean(candidate),'candidateBelowBaselineMedian':lower,
        'repeatableCostGain':cost_passed,'noSuccessRegression':no_regression,
        'safetyRegressionPassed':safety_passed is True,
        'eligibleForDefault':cost_passed and no_regression and safety_passed is True}

def validate_attempt(row, phase, case_id, source_hashes):
    if row.get('phase')!=phase or row.get('caseId')!=case_id or row.get('stage')!='c1':
        raise ValueError('Attempt identity differs from fixed schedule')
    if row.get('hashes')!=source_hashes:
        raise ValueError('Attempt source differs from frozen phase')
    if type(row.get('manualInterventions')) is not int or row['manualInterventions']<0:
        raise ValueError('Manual intervention count missing')
    if type(row.get('elapsedMs')) is not int or row['elapsedMs']<0:
        raise ValueError('Measured elapsed time missing')
    if type(row.get('rawCalls')) is not int or not 0<=row['rawCalls']<=RAW_BUDGET:
        raise ValueError('Actual request budget violated or unknown')
    verification=row.get('verification',{})
    proof=verification.get('independentGuestReport',{})
    if row.get('status')=='SUCCEEDED':
        expected=C1_CASES[case_id].expected
        if (row.get('terminalReason',{}).get('kind')!='completed' or proof.get('status')!='SUCCEEDED'
            or proof.get('case_id')!=case_id or proof.get('expected')!=expected
            or proof.get('fresh_display')!=expected or proof.get('file_readback')!=expected
            or proof.get('raw_calls')!=row['rawCalls'] or verification.get('modelRoutes')!=[MODEL]
            or type(verification.get('imageRequests')) is not int or verification['imageRequests']<1):
            raise ValueError('Success lacks matching independent GUI/file/model proof')
    elif row.get('status') not in ('FAILED','BLOCKED','UNVERIFIED'):
        raise ValueError('Attempt not terminal or invalid status')
    return row

def phase_report(rows, phase):
    if len(rows)!=len(C1_CASES)*REPETITIONS:raise ValueError('Incomplete phase')
    return {'phase':phase,'attempts':len(rows),'passed':sum(r['status']=='SUCCEEDED' for r in rows),
            'manualInterventions':sum(r['manualInterventions'] for r in rows),
            'rawCalls':sum(r['rawCalls'] for r in rows),'elapsedMs':sum(r['elapsedMs'] for r in rows),
            'tokenUsage':{key:sum(r['measuredUsage'][key] for r in rows)
                if all(r.get('measuredUsage',{}).get('available') for r in rows) else None for key in TOKEN_FIELDS},
            'perCase':{case:{'attempts':REPETITIONS,
                'passed':sum(r['status']=='SUCCEEDED' for r in rows if r['caseId']==case),
                'rawCalls':[r['rawCalls'] for r in rows if r['caseId']==case],
                'elapsedMs':[r['elapsedMs'] for r in rows if r['caseId']==case]}
                for case in C1_CASES}}

def load_report(runtime):
    directory=Path(runtime)/'runs'
    reports={};hashes={};seen_runs=set();seen_sessions=set()
    for phase in PHASES:
        hashes[phase]=json.loads((directory/f'c1-{phase}-sources.json').read_text())
        rows=[]
        for case_id in C1_CASES:
            for repetition in range(1,REPETITIONS+1):
                run=f'c1_{phase}_{case_id}_20261001_{repetition:03d}'
                row=json.loads((directory/run/'evaluation.json').read_text())
                if row.get('run')!=run or not row.get('sessionId'):raise ValueError('Run/session proof missing')
                if run in seen_runs or row['sessionId'] in seen_sessions:raise ValueError('Reused run or model session')
                seen_runs.add(run);seen_sessions.add(row['sessionId'])
                events=session_events(runtime,row['sessionId'])
                validate_session(events,row)
                row['measuredUsage']=measured_usage(events)
                audit=[json.loads(line) for line in (directory/run/'request-audit.jsonl').read_text().splitlines()]
                routes={a.get('provider','')+'/'+a.get('model','') for a in audit}
                allowed={'vm_observe','vm_click','vm_write_result','vm_read_result','vm_select_target'}
                if case_id!='popup':allowed.add('vm_type')
                if routes!={MODEL} or any(set(a.get('toolNames',[]))-allowed for a in audit):
                    raise ValueError('Actual model route or tool boundary differs across trials')
                if row['status']=='SUCCEEDED' and sum(a.get('imageBlocks',0)>0 for a in audit)!=row['verification']['imageRequests']:
                    raise ValueError('Reported images differ from actual model request audit')
                rows.append(validate_attempt(row,phase,case_id,hashes[phase]))
        reports[phase]=phase_report(rows,phase)
    # Task/fixture/transport implementation must remain the same; only an
    # explicitly evaluated observation/behaviour component can differ.
    variable={'tools/mac_vm/c1_bridge.py','agent/harness/cordis.desktop.c1.patch.yml'}
    changed={key for key in set(hashes['baseline'])|set(hashes['after'])
             if hashes['baseline'].get(key)!=hashes['after'].get(key)}
    if changed-variable:raise ValueError('Task/environment/permission source changed between phases')
    all_classes=all(reports['baseline']['perCase'][case]['passed']+reports['after']['perCase'][case]['passed']>0 for case in C1_CASES)
    return {'status':'SUCCEEDED' if all_classes else 'UNVERIFIED','model':MODEL,'budget':RAW_BUDGET,
            'changedSources':sorted(changed),'phases':reports,
            'promotionReview':promotion_review(reports),
            'note':'36 fixed before/after trials; component default promotion needs separate repeatable-gain review'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();report=load_report(args.runtime)
    with Path(args.output).open('x') as stream:json.dump(report,stream,indent=2)
    print(json.dumps(report))

if __name__=='__main__':main()
