"""Pure single-cell input planning; no Driver calls or execution authority."""
import re
import unicodedata

from calc_targeting import _state, _elements, _in_window, _number, confirm_selected_cell


def validate_cell_payload(text, kind):
    """Preserve bytes; reject ambiguous/formula-capable payloads before typing.

    This does not prove Calc's resulting storage type or locale interpretation.
    """
    if (not isinstance(text, str) or not text or len(text.encode('utf8')) > 256
            or text != text.strip() or any(unicodedata.category(c).startswith('C')
            or c in '\u2028\u2029' for c in text)):
        raise ValueError('bounded single-line literal required')
    if kind == 'text':
        if text[0] in "=+-@'":
            raise ValueError('formula-like or quoting prefix unverified')
    elif kind == 'decimal':
        if not re.fullmatch(r'-?(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,2})?', text):
            raise ValueError('canonical bounded decimal required')
    else:
        raise ValueError('explicit text or decimal type required')
    return text


def plan_cell_input(state, *, cell, pid, window_id, title, observed_at, now,
                    previous_snapshot_id, name_box_index, grid,
                    approved, overwrite_disposable, text, kind, approved_text, approved_kind,
                    formula_region=None):
    """Caller owns approval, name-box identity, region, and prior snapshot.

    Absence of AX value is NOT emptiness. Explicit disposable overwrite approval
    is required. Returned arguments must still pass an execution-layer lease,
    stop/UNKNOWN, budget, identity and single-attempt gate before dispatch.
    """
    if approved is not True or overwrite_disposable is not True:
        raise ValueError('explicit disposable target overwrite approval required')
    validate_cell_payload(approved_text, approved_kind)
    if text != approved_text or kind != approved_kind:
        raise ValueError('payload differs from trusted input binding')
    context=dict(pid=pid,window_id=window_id,title=title,observed_at=observed_at,now=now)
    width,height,scale,bounds=_state(state,**context)
    confirm_selected_cell(state,cell=cell,previous_snapshot_id=previous_snapshot_id,
                          name_box_index=name_box_index,**context)
    if (not isinstance(grid,(list,tuple)) or len(grid)!=4 or not all(_number(v) for v in grid)
            or not 0<=grid[0]<grid[2]<=width or not 0<=grid[1]<grid[3]<=height):
        raise ValueError('reviewed target region required')
    indexed=_elements(state)
    if indexed is None:
        raise ValueError('malformed AX evidence')
    if any(e.get('role')=='AXButton' and e.get('label') in ('Cancel','Accept')
           and e.get('enabled') is True and _in_window(e,indexed,title)
           for e in indexed.values()):
        raise ValueError('pending edit must be resolved first')
    # Fail ambiguous duplicate labels, even when one duplicate has a bad token.
    candidates=[e for e in indexed.values() if e.get('role')=='AXTextField'
                and e.get('label')==cell and e.get('enabled') is True
                and _in_window(e,indexed,title)]
    if len(candidates)!=1:
        raise ValueError('unique grounded cell required for input')
    target=candidates[0]; frame=target.get('frame',{})
    if (not isinstance(frame,dict) or not all(_number(frame.get(k)) for k in ('x','y','w','h'))
            or frame['w']<=0 or frame['h']<=0
            or target.get('element_token')!=state['snapshot_id']+':'+str(target['element_index'])):
        raise ValueError('fresh target token and finite frame required')
    x=(frame['x']+frame['w']/2-bounds['x'])*scale
    y=(frame['y']+frame['h']/2-bounds['y'])*scale
    if not grid[0]<=x<grid[2] or not grid[1]<=y<grid[3]:
        raise ValueError('cell outside reviewed target region')
    if formula_region is not None:
        r=formula_region
        if (not isinstance(r,(list,tuple)) or len(r)!=4 or not all(_number(v) for v in r)
                or not 0<=r[0]<r[2]<=width or not 0<=r[1]<r[3]<=height):
            raise ValueError('reviewed formula editor region required')
        editors=[]
        for e in indexed.values():
            if e.get('role')!='AXTextArea' or e.get('enabled') is not True or not _in_window(e,indexed,title):continue
            f=e.get('frame',{})
            if not isinstance(f,dict) or not all(_number(f.get(k)) for k in ('x','y','w','h')) or f['w']<=0 or f['h']<=0:continue
            left=(f['x']-bounds['x'])*scale;top=(f['y']-bounds['y'])*scale
            if r[0]<=left and r[1]<=top and left+f['w']*scale<=r[2] and top+f['h']*scale<=r[3]:editors.append(e)
        if len(editors)!=1:raise ValueError('unique grounded formula editor required')
        target=editors[0]
        if target.get('element_token')!=state['snapshot_id']+':'+str(target['element_index']):
            raise ValueError('fresh formula editor token required')
    return dict(status='CELL_INPUT_PLANNED',snapshot_id=state['snapshot_id'],cell=cell,
                target=dict(element_token=target['element_token']),text=text,kind=kind,
                delivery_mode='foreground',requiresPostActionObservation=True,
                inputPermitted=False,inputEffectVerified=False,businessStatus='UNVERIFIED')
