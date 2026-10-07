/** Bounded data projection, not a new observation or GUI authority. */
import assert from 'node:assert/strict'

export function handoffObservation(state: any, used: number): object {
  assert.ok(state && typeof state === 'object' && !Array.isArray(state))
  assert.ok(Number.isInteger(used) && used >= 1 && used <= 30)
  assert.ok(Number.isInteger(state.pid) && state.pid > 0 && Number.isInteger(state.window_id) && state.window_id > 0)
  assert.ok(typeof state.snapshot_id === 'string' && state.snapshot_id.length > 0 && state.snapshot_id.length <= 256)
  assert.equal(state.app_name, 'TextEdit'); assert.equal(state.screenshot_frame_valid, true)
  assert.ok(!state.degraded_reason && typeof state.window_title === 'string'
    && /^handoff-p2-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}\.txt$/u.test(state.window_title))
  assert.ok(Array.isArray(state.elements) && state.elements.length > 0 && state.elements.length <= 4096)
  const byIndex = new Map<number, any>()
  for (const element of state.elements) {
    assert.ok(element && typeof element === 'object' && !Array.isArray(element)
      && Number.isInteger(element.element_index) && element.element_index >= 0 && !byIndex.has(element.element_index))
    assert.ok(!['AXSheet', 'AXDialog'].includes(element.role), 'unreviewed dialog present')
    byIndex.set(element.element_index, element)
  }
  const candidates: any[][] = []
  for (const element of state.elements.filter((e: any) => e.role === 'AXTextArea')) {
    const chain: any[] = [], seen = new Set(); let current = element
    while (current && chain.length < 16 && !seen.has(current.element_index)) {
      seen.add(current.element_index); chain.push(current)
      if (current.role === 'AXWindow') {
        if (current.label === state.window_title) candidates.push(chain.reverse())
        break
      }
      current = byIndex.get(current.parent_index)
    }
  }
  assert.equal(candidates.length, 1, 'unique task body required')
  const chain = candidates[0], body = chain.at(-1)
  const hasValue = Object.hasOwn(body, 'value')
  assert.ok(!hasValue || (typeof body.value === 'string' && Buffer.byteLength(body.value, 'utf8') <= 4096 && !body.value.includes('\0')))
  assert.ok(typeof body.element_token === 'string' && body.element_token.length > 0 && body.element_token.length <= 256)
  assert.ok(body.enabled === undefined || body.enabled === true)
  const elements = chain.map((element, index) => {
    assert.ok(typeof element.role === 'string' && element.role.length <= 64)
    if (index > 0) assert.ok(Number.isInteger(element.parent_index) && element.parent_index === chain[index - 1].element_index)
    return { element_index: element.element_index, role: element.role,
      ...(index > 0 ? { parent_index: element.parent_index } : { label: element.label }),
      ...(index === chain.length - 1 ? { element_token: body.element_token, enabled: true,
        ...(hasValue ? { value: body.value } : { bodyValueStatus: 'unavailable' }) } : {}) }
  })
  const value = { projection: 'handoff-body-v1', snapshot_id: state.snapshot_id, pid: state.pid,
    window_id: state.window_id, app_name: state.app_name, window_title: state.window_title,
    screenshot_frame_valid: true, used, elements }
  assert.ok(Buffer.byteLength(JSON.stringify(value), 'utf8') <= 8192, 'bounded complete body required')
  return value
}
