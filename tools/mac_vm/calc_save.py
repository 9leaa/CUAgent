"""Pure save-entry planning; no filesystem mutation or Driver authority."""
import re

from calc_input import inspect_committed_cell
from calc_targeting import _state, _elements, _in_window, _number


def workbook_destination(run_id):
    if not isinstance(run_id,str) or not re.fullmatch(
            r'calc-select-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',run_id):
        raise ValueError('canonical bound run required')
    return '/Users/mvpagent/Documents/cuagent-'+run_id.removeprefix('calc-select-')+'.ods'


def plan_open_save(state, *, run_id, destination, save_approved, toolbar_region, point=None, **context):
    if save_approved is not True or destination!=workbook_destination(run_id):
        raise ValueError('explicit fixed save destination approval required')
    if context.get('title')!='Untitled 1':
        raise ValueError('only explicitly bound unsaved test workbook allowed')
    proof=inspect_committed_cell(state,**context)
    width,height,scale,bounds=_state(state,**{k:context[k] for k in
        ('pid','window_id','title','observed_at','now')})
    r=toolbar_region
    if (not isinstance(r,(list,tuple)) or len(r)!=4 or not all(_number(v) for v in r)
            or not 0<=r[0]<r[2]<=width or not 0<=r[1]<r[3]<=height):
        raise ValueError('reviewed Save toolbar region required')
    indexed=_elements(state)
    if any(e.get('role') in ('AXSheet','AXDialog') and _in_window(e,indexed,context['title'])
           for e in indexed.values()):
        raise ValueError('unexpected existing dialog')
    found=[]
    for e in indexed.values():
        if e.get('role')!='AXMenuButton' or e.get('label')!='Save' or not _in_window(e,indexed,context['title']):continue
        if e.get('enabled') is not True or 'AXPress' not in e.get('actions',[]):continue
        f=e.get('frame',{})
        if not isinstance(f,dict) or not all(_number(f.get(k)) for k in ('x','y','w','h')) or f['w']<=0 or f['h']<=0:continue
        x=(f['x']-bounds['x'])*scale;y=(f['y']-bounds['y'])*scale
        if r[0]<=x and r[1]<=y and x+f['w']*scale<=r[2] and y+f['h']*scale<=r[3]:found.append(e)
    if len(found)!=1:raise ValueError('unique grounded Save toolbar control required')
    e=found[0]
    if e.get('element_token')!=state['snapshot_id']+':'+str(e['element_index']):
        raise ValueError('fresh Save token required')
    target=dict(element_token=e['element_token']);route='ax'
    if point is not None:
        if (not isinstance(point,dict) or set(point)!={'snapshot_id','x','y'}
                or point['snapshot_id']!=state['snapshot_id'] or not all(_number(point[k]) for k in ('x','y'))):
            raise ValueError('same-snapshot finite model Save point required')
        f=e['frame'];left=(f['x']-bounds['x'])*scale;top=(f['y']-bounds['y'])*scale
        if not left<point['x']<left+f['w']*scale or not top<point['y']<top+f['h']*scale:
            raise ValueError('Save point outside grounded control')
        target=dict(x=point['x'],y=point['y']);route='screenshot'
    return dict(status='SAVE_DIALOG_OPEN_PLANNED',snapshot_id=state['snapshot_id'],
        target=target,route=route,destination=destination,
        commitEvidence=proof,requiresPostActionObservation=True,
        filesystemAdmissionVerified=False,savePermitted=False,saved=False,businessStatus='UNVERIFIED')
