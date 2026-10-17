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
    if point is not None:
        if (not isinstance(point,dict) or set(point)!={'snapshot_id','x','y'}
                or point['snapshot_id']!=state['snapshot_id'] or not all(_number(point[k]) for k in ('x','y'))):
            raise ValueError('same-snapshot finite model Save point required')
        if not r[0]<point['x']<r[2] or not r[1]<point['y']<r[3]:
            raise ValueError('Save point outside reviewed toolbar region')
        target=dict(x=point['x'],y=point['y']);route='screenshot'
    else:
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
    return dict(status='SAVE_DIALOG_OPEN_PLANNED',snapshot_id=state['snapshot_id'],
        target=target,route=route,destination=destination,
        commitEvidence=proof,requiresPostActionObservation=True,
        filesystemAdmissionVerified=False,savePermitted=False,saved=False,businessStatus='UNVERIFIED')


def discover_new_panel(before, after, *, pid, document_window, title='Save'):
    """Select a read-only candidate; never grants input authority from a title."""
    if type(pid) is not int or pid <= 0 or type(document_window) is not int or document_window <= 0:
        raise ValueError('valid original document identity required')
    old,new=panel_inventory(before,pid=pid,document_window=document_window),panel_inventory(after,pid=pid,document_window=document_window)
    document=old[document_window]
    if new[document_window]!=document:
        # Stacking order may change when the panel opens; identity/geometry may not.
        for key in ('pid','title','bounds'):
            if new[document_window].get(key)!=document.get(key):
                raise ValueError('original document changed during panel discovery')
    b=document['bounds'];found=[]
    for wid,row in new.items():
        if wid in old or row.get('title')!=title:continue
        r=row['bounds']
        if (b['x']<=r['x'] and b['y']<=r['y'] and r['x']+r['width']<=b['x']+b['width']
                and r['y']+r['height']<=b['y']+b['height']):
            found.append(row)
    if len(found)!=1:
        raise ValueError('unique newly opened owned panel required')
    return dict(found[0])


def panel_inventory(value, *, pid, document_window):
    rows=value.get('windows') if isinstance(value,dict) else None
    if not isinstance(rows,list) or len(rows)>1024:
        raise ValueError('bounded window inventory required')
    result={}
    for row in rows:
        if not isinstance(row,dict) or type(row.get('window_id')) is not int or row['window_id']<=0:
            raise ValueError('valid window identity required')
        wid=row['window_id']
        if wid in result or type(row.get('pid')) is not int or row['pid']!=pid or row.get('is_on_screen') is not True:
            raise ValueError('unique visible original-process windows required')
        b=row.get('bounds')
        if not isinstance(b,dict) or not all(_number(b.get(k)) for k in ('x','y','width','height')) or b['width']<=0 or b['height']<=0:
            raise ValueError('valid window geometry required')
        result[wid]=row
    if document_window not in result:
        raise ValueError('original document disappeared')
    return result
