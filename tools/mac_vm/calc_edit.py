"""Pure planning for cancelling explicitly disposable Calc test input.

No GUI calls, inferred consent, keyboard fallback, or business success claim.
Reviewed regions and expected text must come from the trusted task binding.
"""
from calc_targeting import _state, _elements, _in_window, _number


def plan_edit_cancel(state, *, pid, window_id, title, observed_at, now,
                     approved, expected_text, controls_region, editor_regions):
    width,height,scale,bounds=_state(state,pid=pid,window_id=window_id,
                                   title=title,observed_at=observed_at,now=now)
    if approved is not True or not isinstance(expected_text,str) or not expected_text or len(expected_text.encode())>256:
        raise ValueError('explicit disposable test text approval required')
    if not isinstance(editor_regions,(list,tuple)) or len(editor_regions)!=2:
        raise ValueError('two reviewed independent editor regions required')
    regions=[controls_region,*editor_regions]
    for r in regions:
        if (not isinstance(r,(list,tuple)) or len(r)!=4 or not all(_number(v) for v in r)
                or not 0<=r[0]<r[2]<=width or not 0<=r[1]<r[3]<=height):
            raise ValueError('reviewed screenshot region required')
    a,b=editor_regions
    if not (a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1]):
        raise ValueError('editor regions must be disjoint')
    indexed=_elements(state)
    if indexed is None:raise ValueError('malformed elements')
    def inside(e,region):
        frame=e.get('frame',{})
        if (not isinstance(frame,dict) or not all(_number(frame.get(k)) for k in ('x','y','w','h'))
                or frame['w']<=0 or frame['h']<=0):return False
        x=(frame['x']-bounds['x'])*scale;y=(frame['y']-bounds['y'])*scale
        return region[0]<=x and region[1]<=y and x+frame['w']*scale<=region[2] and y+frame['h']*scale<=region[3]
    def matches(role,region,label=None):
        return [e for e in indexed.values() if e.get('role')==role and e.get('enabled') is True
                and _in_window(e,indexed,title) and inside(e,region) and (label is None or e.get('label')==label)]
    buttons=[]
    for label in ('Cancel','Accept'):
        found=matches('AXButton',controls_region,label)
        if len(found)!=1 or 'AXPress' not in found[0].get('actions',[]):
            raise ValueError('unique enabled edit controls required')
        e=found[0]
        if e.get('element_token')!=state['snapshot_id']+':'+str(e['element_index']):
            raise ValueError('current snapshot token required')
        buttons.append(e)
    editors=[]
    for region in editor_regions:
        found=matches('AXTextArea',region)
        if len(found)!=1 or found[0].get('value')!=expected_text:
            raise ValueError('pending input differs from approved disposable text')
        editors.append(found[0]['element_index'])
    if len(set(editors))!=2:raise ValueError('two independent editor observations required')
    return dict(status='EDIT_CANCEL_PLANNED',snapshot_id=state['snapshot_id'],
                target=dict(element_index=buttons[0]['element_index'],element_token=buttons[0]['element_token']),
                requiresPostActionObservation=True,inputPermitted=False,businessStatus='UNVERIFIED')
