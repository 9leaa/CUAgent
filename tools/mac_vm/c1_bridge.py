"""Reviewed C1 execution extension; reuses C0 admission/audit/HTTP, not a model loop."""
from dataclasses import replace
import json
import os
import re
import time
from types import MappingProxyType
from c0_bridge import Task, StopRun, Calls, main as serve
from c0_cases import UICase
from c0_identity import app_identity
from driver_smoke import display_value
from c1_cases import C1_CASES

CALC_ACTIONS=('All Clear','7','Add','8','Equals')
REGISTRY=MappingProxyType({key:UICase(value.mode,value.applications[0].title,value.expected,
    value.fields,value.buttons,bundle=value.applications[0].bundle,
    app_name='Calculator' if value.applications[0].bundle=='com.apple.calculator' else 'CUAgentFixtures',
    executable=value.applications[0].executable) for key,value in C1_CASES.items()})

class C1Task(Task):
    def record(self,row):
        # A returned GUI input is an attempt, not proof of an effect. Keep the
        # Calculator's independently verified full sequence as in C0.
        if row.get('event')=='completed_action' and row.get('label') not in CALC_ACTIONS and not row.get('effect_proven'):
            row={**row,'event':'attempted_action'}
        super().record(row)

    def __init__(self,directory,transport=Calls.cli,identity=None,*,approved=False,case_id):
        option=os.environ.get('CUAGENT_C1_OBSERVATION_HINTS','0')
        if option not in ('0','1'):raise StopRun('BLOCKED','Invalid developer observation option')
        self.observation_hints=option=='1'
        super().__init__(directory,transport,identity,approved=approved,case_id=case_id,registry=REGISTRY)
        self.spec=C1_CASES[case_id]
        self.active=self.spec.applications[0]
        self.known_pids={}
        self.transfer_value=None
        self.failure_injected=False
        self.bound=set()
        self.launch_args=self.launch_for(self.active)
        self.allowed=frozenset(self.spec.buttons+(CALC_ACTIONS if case_id=='cross_app' else ()))
        self.record({'event':'c1_scope','targets':[a.title for a in self.spec.applications],
                     'applications':[a.bundle for a in self.spec.applications]})

    def launch_for(self,application):
        args={'bundle_id':application.bundle}
        if application.bundle!='com.apple.calculator':
            args.update(creates_new_application_instance=True,
                additional_arguments=['--task',self.spec.mode,'--output',str(self.directory)])
        return args

    def observe(self):
        result=super().observe()
        result['state']['reviewed_targets']=[a.title for a in self.spec.applications]
        self.known_pids[self.active.bundle]=self.pid
        binding=(self.active.title,self.pid,self.window)
        if binding not in self.bound:
            self.bound.add(binding)
            self.record({'event':'target_bound','target':self.active.title,'pid':self.pid,'window_id':self.window})
        tree=self.snapshot.get('tree_markdown','').split('\n- ',1)[0]
        if self.active.title=='CUAgent Confirmation':self.confirm_effect('Open Confirmation','fresh owned confirmation window')
        if self.active.title=='CUAgent Destination':self.confirm_effect('Open Destination','fresh different destination window')
        if 'Stage 2' in tree:self.confirm_effect('Next','fresh second workflow page')
        if 'Stage 3' in tree:self.confirm_effect('Review','fresh third workflow page')
        if 'Confirmed cedar-42' in tree:self.confirm_effect('Confirm','fresh confirmed popup status')
        if re.search(r'AXStaticText = "(?:Submitted|Transferred|Recovered) ',tree):
            data_path=self.task_file('c1-submission.json')
            if data_path.is_file():self.confirm_effect('Confirm Submission' if self.case_id=='long_workflow' else 'Submit','fresh submitted status and actual submission file')
        self.add_observation_hint(result)
        return result

    def add_observation_hint(self,result):
        if (not self.observation_hints or self.case_id!='popup'
            or self.active.title!=self.spec.applications[0].title or self.used>=28):return
        rows=[json.loads(line) for line in self.ledger.read_text().splitlines()]
        if (not any(r['event']=='attempted_action' and r.get('label')=='Open Confirmation' for r in rows)
            or any(r['event']=='completed_action' and r.get('label')=='Open Confirmation' for r in rows)):return
        inventory=self.raw('list_windows',{'pid':self.pid})
        title=self.spec.applications[1].title
        panels=[w for w in inventory.get('windows',[]) if w.get('pid')==self.pid
                and w.get('app_name')==self.case.app_name and w.get('title')==title
                and w.get('is_on_screen') is True and type(w.get('window_id')) is int and w['window_id']>0]
        if len(panels)!=1:return
        result['state']['observation_hint']={
            'reviewed_visible_target':title,'source':'fresh owned window inventory',
            'instruction':'This confirmation window is already visible. Select its exact title with vm_select_target, then vm_observe before acting. This is not a snapshot of that window; do not reuse the main-window token or open it again.'}
        self.record({'event':'observation_hint','snapshot_id':self.snapshot['snapshot_id'],
                     'target':title,'pid':self.pid,'window_id':panels[0]['window_id']})

    def confirm_effect(self,label,proof):
        rows=[json.loads(line) for line in self.ledger.read_text().splitlines()]
        if any(r['event']=='completed_action' and r.get('label')==label for r in rows):return
        attempts=[r for r in rows if r['event']=='attempted_action' and r.get('label')==label]
        if not attempts:return
        self.record({'event':'completed_action','label':label,'snapshot_id':attempts[-1]['snapshot_id'],
                     'effect_snapshot_id':self.snapshot['snapshot_id'],'effect_proven':True,'proof':proof})

    def select_target(self,args):
        if set(args)!={'target'} or args['target'] not in [a.title for a in self.spec.applications]:
            raise StopRun('BLOCKED','Unreviewed C1 application/window target')
        application=next(a for a in self.spec.applications if a.title==args['target'])
        if self.case_id=='cross_app' and self.active.bundle=='com.apple.calculator' and application.bundle!=self.active.bundle:
            if not self.snapshot or time.monotonic()-self.observed_at>30:
                raise StopRun('BLOCKED','Fresh Calculator result required before transfer')
            self.transfer_value=display_value(self.snapshot)
            self.record({'event':'calculator_transfer_source','snapshot_id':self.snapshot['snapshot_id'],
                         'value':self.transfer_value,'pid':self.pid,'window_id':self.window})
        if self.pid:self.identity(self.pid)
        self.active=application
        self.case=replace(self.case,bundle=application.bundle,title=application.title,executable=application.executable,
                          app_name='Calculator' if application.bundle=='com.apple.calculator' else 'CUAgentFixtures')
        self.launch_args=self.launch_for(application)
        self.pid=self.known_pids.get(application.bundle)
        self.window=None;self.snapshot=None
        if self.pid is None:
            launched=self.raw('launch_app',self.launch_args)
            if launched.get('bundle_id')!=application.bundle or type(launched.get('pid')) is not int:
                raise StopRun('BLOCKED','C1 launch identity mismatch')
            self.pid=launched['pid'];self.known_pids[application.bundle]=self.pid
        windows=self.raw('list_windows',{'pid':self.pid})
        found=[w for w in windows.get('windows',[]) if w.get('pid')==self.pid and w.get('title')==application.title
               and w.get('app_name')==self.case.app_name and w.get('is_on_screen') is True]
        if len(found)!=1:raise StopRun('UNVERIFIED','Need one visible reviewed C1 target; observe actual UI')
        self.window=found[0]['window_id']
        self.record({'event':'target_selected','target':application.title,'pid':self.pid,'window_id':self.window})
        return {'selected':application.title,'requires_new_observation':True,'used':self.used}

    def click(self,args):
        button=self.ui_element(args,('AXButton',))
        if self.case_id=='reobserve_failure' and button.get('label')=='Submit' and not self.failure_injected:
            self.failure_injected=True
            snapshot=self.snapshot['snapshot_id'];self.snapshot=None
            self.charge_rejection('click',self.used,'Controlled stale-target refusal; no side effect')
            self.record({'event':'controlled_stale_refusal','snapshot_id':snapshot,'effect':'none'})
            raise StopRun('BLOCKED','Controlled stale target; observe again and use a new snapshot')
        return super().click(args)

    def type_text(self,args):
        if self.active.bundle=='com.apple.calculator':raise StopRun('BLOCKED','Calculator requires actual buttons')
        if self.case_id=='cross_app':
            if self.transfer_value is None:raise StopRun('BLOCKED','No observed Calculator source')
            self.case=replace(self.case,fields=(('Value',self.transfer_value),))
        return super().type_text(args)

    def observed_value(self):
        if not self.snapshot or time.monotonic()-self.observed_at>30:
            raise StopRun('UNVERIFIED','Fresh C1 status required')
        if self.active.bundle=='com.apple.calculator':raise StopRun('UNVERIFIED','Transfer must finish in receiver application')
        tree=self.snapshot.get('tree_markdown','').split('\n- ',1)[0]
        values=re.findall(r'^\s+- AXStaticText = "((?:Transferred|Submitted|Confirmed|Recovered) [^"\n]+)"\s*$',tree,re.M)
        if len(values)!=1:raise StopRun('UNVERIFIED','No unique fresh completed C1 status')
        return values[0]

    def verify_ui_trajectory(self,rows,actions):
        effects=json.loads(self.task_file('c1-effects.json').read_text()).get('effects',[])
        inputs=[(r.get('label'),r.get('text')) for r in rows if r['event']=='completed_input']
        bindings=[r for r in rows if r['event'] in ('target_bound','target_selected')]
        if self.case_id=='cross_app':
            sources=[r for r in rows if r['event']=='calculator_transfer_source']
            data=json.loads(self.task_file('c1-submission.json').read_text())
            return (actions==list(CALC_ACTIONS)+['Submit'] and len(sources)==1 and sources[0]['value']=='15'
                    and inputs==[('Value','15')] and data=={'value':'15','submitted':True,'task':'cross_app'}
                    and 'transfer-submit' in effects and len({r['pid'] for r in bindings})==2)
        if self.case_id=='popup':
            return (actions==['Open Confirmation','Confirm'] and not inputs
                    and effects==['popup-opened','owned-popup-confirmed']
                    and len({r['window_id'] for r in bindings})==2)
        if self.case_id=='long_workflow':
            data=json.loads(self.task_file('c1-submission.json').read_text())
            return (actions==['Next','Review','Confirm Submission'] and inputs==list(self.spec.fields)
                    and effects==['stage:1','stage:2','stage:3','workflow-submit']
                    and data=={'code':'cedar-42','marker':'harbor-729','confirmed':True})
        data=json.loads(self.task_file('c1-submission.json').read_text())
        expected_actions=['Open Destination','Submit'] if self.case_id=='window_change' else ['Submit']
        passed=(actions==expected_actions and inputs==list(self.spec.fields)
                and data=={'value':'cedar-42','submitted':True,'task':self.case_id})
        if self.case_id=='window_change':
            return passed and effects==['destination-opened','destination-submit'] and len({r['window_id'] for r in bindings})==2
        if self.case_id=='input_correction':
            states=[r['value'] for r in rows if r['event']=='result' and r.get('tool')=='get_window_state']
            return passed and bool(states) and 'cedra-42' in states[0].get('tree_markdown','') and effects==['initial-value:cedra-42','corrected-value:cedar-42','submit']
        failures=[i for i,r in enumerate(rows) if r['event']=='controlled_stale_refusal']
        if len(failures)!=1:return False
        failure=rows[failures[0]]
        later=rows[failures[0]+1:]
        observation=next((i for i,r in enumerate(later) if r['event']=='result' and r.get('tool')=='get_window_state'
                          and r['value'].get('snapshot_id')!=failure['snapshot_id']),None)
        submission=next((i for i,r in enumerate(later) if r['event']=='completed_action' and r.get('label')=='Submit'),None)
        return passed and effects==['submit'] and observation is not None and submission is not None and observation<submission

if __name__=='__main__':serve(task_class=C1Task,registry=REGISTRY,stage='C1')
