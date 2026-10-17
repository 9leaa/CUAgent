"""Trusted, opt-in fallback for truncated Calc name-box evidence."""
import base64
import hashlib

from calc_targeting import _state, _elements, _in_window
from image_text_verify import dimensions, recognize_png, verify_region_text

RECOGNIZER_SHA256 = '5a24d206e34b5b80f920ffd94f35aba9a78ddf9b6da145bf7e3decb3a5204698'
RECOGNIZER = '/Users/mvpagent/CUAgentImageText-' + RECOGNIZER_SHA256 + '/native-image-text'


def confirm_visual_selection(state, *, region, cache, **context):
    """No caller-supplied OCR. Existing contradictory AX evidence is not ignored."""
    _state(state, **{k:context[k] for k in ('pid','window_id','title','observed_at','now')})
    if (not isinstance(context['previous_snapshot_id'],str) or not context['previous_snapshot_id']
            or state['snapshot_id'] == context['previous_snapshot_id']):
        raise ValueError('new visual selection snapshot required')
    if state.get('elements_complete') is not False:
        raise ValueError('visual fallback requires explicitly partial AX evidence')
    indexed = _elements(state)
    if indexed is None:
        raise ValueError('malformed AX evidence cannot be silently replaced')
    index = context['name_box_index']
    box = indexed.get(index)
    if box is not None:
        if box.get('role') != 'AXComboBox' or not _in_window(box,indexed,context['title']):
            raise ValueError('name box identity conflict')
        related = [box] + [e for e in indexed.values() if e.get('parent_index') == index
                          and e.get('role') == 'AXTextArea']
        if any(e.get('value') not in (None,context['cell']) or e.get('enabled') is False for e in related):
            raise ValueError('AX selection contradicts visual fallback')
        children = related[1:]
        if len(children) > 1:
            raise ValueError('ambiguous AX name box')
    encoded = state.get('screenshot_png_b64')
    if not isinstance(encoded,str) or len(encoded) > 12*1024*1024:
        raise ValueError('bounded original screenshot required')
    png = base64.b64decode(encoded,validate=True)
    if dimensions(png) != (state['screenshot_width'],state['screenshot_height']):
        raise ValueError('screenshot metadata mismatch')
    key = (state['snapshot_id'],hashlib.sha256(png).hexdigest())
    if cache.get('key') != key:
        report = recognize_png(png,executable=RECOGNIZER,executable_sha256=RECOGNIZER_SHA256)
        cache.clear();cache.update(key=key,report=report)
    proof = verify_region_text(png,cache['report'],region=region,expected=context['cell'])
    return dict(status='SELECTION_OBSERVED',cell=context['cell'],snapshot_id=state['snapshot_id'],
                route='screenshot-text',visualEvidence=proof,inputPermitted=False,inputEffectVerified=False)
