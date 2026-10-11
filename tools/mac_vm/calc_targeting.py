"""Side-effect-free Calc target planning. Not an execution or input permit.

Trusted caller binds identity, timestamps and a reviewed screenshot grid region.
Model coordinates describe screenshot pixels, never host/desktop coordinates.
The production adapter must still enforce lease, stop, budget and audit guards.
"""
import math
import re


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _cell(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,6}', value):
        raise ValueError('single canonical cell required')
    return value


def _state(state, *, pid, window_id, title, observed_at, now):
    if (type(pid) is not int or pid <= 0 or type(window_id) is not int or window_id <= 0
            or not isinstance(title, str) or not title
            or not isinstance(state, dict)
            or type(state.get('pid')) is not int or state['pid'] != pid
            or type(state.get('window_id')) is not int or state['window_id'] != window_id
            or state.get('app_name') != 'LibreOffice' or state.get('window_title') != title):
        raise ValueError('bound Calc window required')
    if not _number(now) or not _number(observed_at) or not 0 <= now - observed_at <= 30:
        raise ValueError('fresh observation required')
    if not isinstance(state.get('snapshot_id'), str) or not state['snapshot_id']:
        raise ValueError('snapshot identity required')
    if state.get('screenshot_frame_valid') is not True:
        raise ValueError('valid screenshot frame required')
    width, height, scale = (state.get(k) for k in ('screenshot_width', 'screenshot_height', 'screenshot_scale'))
    bounds = state.get('window_bounds', {})
    if (type(width) is not int or type(height) is not int or not 0 < width <= 16384
            or not 0 < height <= 16384 or not _number(scale) or scale <= 0
            or not isinstance(bounds, dict)
            or not all(_number(bounds.get(k)) for k in ('x', 'y', 'width', 'height'))
            or bounds['width'] <= 0 or bounds['height'] <= 0
            or abs(bounds['width'] * scale - width) > 1
            or abs(bounds['height'] * scale - height) > 1):
        raise ValueError('screenshot coordinate mapping invalid')
    return width, height, scale, bounds


def _elements(state):
    elements = state.get('elements', [])
    if not isinstance(elements, list) or len(elements) > 20000:
        return None
    indexed = {}
    for item in elements:
        if not isinstance(item, dict):
            return None
        index = item.get('element_index')
        if type(index) is not int or index < 0 or index in indexed:
            return None
        indexed[index] = item
    return indexed


def _in_window(element, indexed, title):
    visited = set()
    while element is not None:
        index = element['element_index']
        if index in visited or element.get('role') in ('AXMenu', 'AXMenuBar'):
            return False
        visited.add(index)
        if element.get('role') == 'AXWindow':
            return element.get('label') == title
        parent = element.get('parent_index')
        if type(parent) is not int:
            return False
        element = indexed.get(parent)
    return False


def plan_cell_target(state, *, cell, pid, window_id, title, observed_at, now, grid, point=None):
    """Prefer grounded AX; otherwise request/validate one same-snapshot point.

    grid is trusted (left, top, right, bottom) in window screenshot pixels.
    point is exactly {snapshot_id, x, y}, proposed by the screenshot consumer.
    Returned plans do not prove that a coordinate semantically denotes cell.
    """
    _cell(cell)
    width, height, scale, bounds = _state(state, pid=pid, window_id=window_id,
                                         title=title, observed_at=observed_at, now=now)
    if (not isinstance(grid, (tuple, list)) or len(grid) != 4
            or not all(_number(v) for v in grid)
            or not 0 <= grid[0] < grid[2] <= width
            or not 0 <= grid[1] < grid[3] <= height):
        raise ValueError('reviewed screenshot grid required')
    def within(x, y):
        return grid[0] <= x < grid[2] and grid[1] <= y < grid[3]
    base = dict(cell=cell, snapshot_id=state['snapshot_id'], pid=pid, window_id=window_id,
                title=title, inputPermitted=False, requiresPostClickObservation=True)
    indexed = _elements(state)
    candidates = []
    if indexed is not None and state.get('elements_complete') is True:
        for e in indexed.values():
            if (e.get('role') != 'AXTextField' or e.get('label') != cell
                    or e.get('enabled') is not True or not _in_window(e, indexed, title)):
                continue
            frame = e.get('frame', {})
            token = e.get('element_token')
            if (not isinstance(frame, dict) or not all(_number(frame.get(k)) for k in ('x','y','w','h'))
                    or frame['w'] <= 0 or frame['h'] <= 0
                    or not isinstance(token, str) or not token):
                continue
            x = (frame['x'] + frame['w']/2 - bounds['x']) * scale
            y = (frame['y'] + frame['h']/2 - bounds['y']) * scale
            if within(x, y):
                candidates.append(e)
    if len(candidates) == 1:
        e = candidates[0]
        return dict(base, status='TARGET_PLANNED', route='ax',
                    target=dict(element_index=e['element_index'], element_token=e['element_token']))
    if point is None:
        return dict(base, status='NEEDS_SCREENSHOT_POINT', route='screenshot')
    if (not isinstance(point, dict) or set(point) != {'snapshot_id','x','y'}
            or point['snapshot_id'] != state['snapshot_id']
            or not _number(point['x']) or not _number(point['y'])
            or not within(point['x'], point['y'])):
        raise ValueError('fresh grid-contained screenshot point required')
    return dict(base, status='TARGET_PLANNED', route='screenshot',
                target=dict(x=point['x'], y=point['y']), coordinateSpace='window_screenshot_pixels')


def confirm_selected_cell(state, *, cell, previous_snapshot_id, pid, window_id, title,
                          observed_at, now, name_box_index):
    """Read-only name-box confirmation; still NOT permission to type.

    Trusted adapter selects a name-box AXComboBox from the NEW observation.
    Incomplete trees may still supply this local pair; missing/ambiguous
    name-box evidence fails closed. Completeness is not inferred from counts.
    """
    _cell(cell)
    _state(state, pid=pid, window_id=window_id, title=title, observed_at=observed_at, now=now)
    if (not isinstance(previous_snapshot_id, str) or not previous_snapshot_id
            or previous_snapshot_id == state['snapshot_id']):
        raise ValueError('post-click new snapshot required')
    indexed = _elements(state)
    if indexed is None or type(name_box_index) is not int:
        raise ValueError('unambiguous name box required')
    box = indexed.get(name_box_index)
    if (not box or box.get('role') != 'AXComboBox' or box.get('enabled') is not True
            or not _in_window(box, indexed, title) or box.get('value') != cell):
        raise ValueError('selected cell mismatch or missing')
    children = [e for e in indexed.values() if type(e.get('parent_index')) is int
                and e['parent_index'] == name_box_index and e.get('role') == 'AXTextArea']
    if len(children) != 1 or children[0].get('enabled') is not True or children[0].get('value') != cell:
        raise ValueError('name box child mismatch or ambiguous')
    return dict(status='SELECTION_OBSERVED', cell=cell, snapshot_id=state['snapshot_id'],
                inputPermitted=False, inputEffectVerified=False)
