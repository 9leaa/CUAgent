"""Independent recomputation of the bounded P7 model-facing AX projection."""
import json
import re


def require(value):
    if not value: raise ValueError('HANDOFF_OBSERVATION_UNVERIFIED')


def project_handoff_observation(state, used):
    require(type(state) is dict and type(used) is int and 1 <= used <= 30)
    require(all(type(state.get(k)) is int and state[k] > 0 for k in ('pid', 'window_id')))
    require(type(state.get('snapshot_id')) is str and 0 < len(state['snapshot_id'].encode('utf-16-le')) // 2 <= 256)
    require(state.get('app_name') == 'TextEdit' and state.get('screenshot_frame_valid') is True
            and not state.get('degraded_reason') and type(state.get('window_title')) is str
            and re.fullmatch(r'handoff-p2-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\.txt', state['window_title']))
    elements = state.get('elements')
    require(type(elements) is list and 0 < len(elements) <= 4096)
    indexed = {}
    for element in elements:
        require(type(element) is dict and type(element.get('element_index')) is int
                and element['element_index'] >= 0 and element['element_index'] not in indexed
                and element.get('role') not in ('AXSheet', 'AXDialog'))
        indexed[element['element_index']] = element
    candidates = []
    for element in elements:
        if element.get('role') != 'AXTextArea': continue
        chain, seen, current = [], set(), element
        while current and len(chain) < 16 and current['element_index'] not in seen:
            seen.add(current['element_index']); chain.append(current)
            if current.get('role') == 'AXWindow':
                if current.get('label') == state['window_title']: candidates.append(list(reversed(chain)))
                break
            parent = current.get('parent_index')
            current = indexed.get(parent) if type(parent) is int else None
    require(len(candidates) == 1)
    chain = candidates[0]; body = chain[-1]
    has_value = 'value' in body
    require(not has_value or (type(body['value']) is str and len(body['value'].encode()) <= 4096 and '\0' not in body['value']))
    require(type(body.get('element_token')) is str and 0 < len(body['element_token'].encode('utf-16-le')) // 2 <= 256
            and body.get('enabled', True) is True)
    projected = []
    for index, element in enumerate(chain):
        require(type(element.get('role')) is str and len(element['role'].encode('utf-16-le')) // 2 <= 64)
        row = dict(element_index=element['element_index'], role=element['role'])
        if index:
            require(type(element.get('parent_index')) is int and element['parent_index'] == chain[index-1]['element_index'])
            row['parent_index'] = element['parent_index']
        else: row['label'] = element['label']
        if index == len(chain)-1:
            row.update(element_token=body['element_token'], enabled=True)
            row.update({'value': body['value']} if has_value else {'bodyValueStatus': 'unavailable'})
        projected.append(row)
    value = dict(projection='handoff-body-v1', snapshot_id=state['snapshot_id'], pid=state['pid'],
        window_id=state['window_id'], app_name=state['app_name'], window_title=state['window_title'],
        screenshot_frame_valid=True, used=used, elements=projected)
    require(len(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()) <= 8192)
    return value
