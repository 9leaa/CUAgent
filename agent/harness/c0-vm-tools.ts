/** Official Harness tools; no model loop, desktop or arbitrary URL passthrough. */
import { readFileSync, statSync, appendFileSync, writeFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'
import { AttachmentId } from '@deepseek-ai/dsh-attachment'
import { assertImageCapableRoute } from './image-probe.ts'

export const name = 'cuagent-c0-vm-tools'
export const inject = ['tools', 'attachments', 'llm']
const BASE_TOOLS = ['vm_observe', 'vm_click', 'vm_write_result', 'vm_read_result']
const URL = 'http://192.168.64.3:8766'

export function apply(ctx: Context): void {
  const configPath = process.env.CUAGENT_C0_CONNECTION
  if (!configPath || (statSync(configPath).mode & 0o077)) throw new Error('Private C0 connection file required')
  const connection = JSON.parse(readFileSync(configPath, 'utf8'))
  if (connection.url !== URL || typeof connection.token !== 'string' || !/^[\w-]{40,60}$/.test(connection.token)) {
    throw new Error('Invalid fixed VM connection')
  }
  const allowed = [...BASE_TOOLS,
    ...(['form', 'document'].includes(connection.caseId) ? ['vm_type'] : []),
    ...(connection.caseId === 'scroll' ? ['vm_scroll'] : [])]
  const auditPath = process.env.CUAGENT_C0_AUDIT_PATH
  if (!auditPath) throw new Error('C0 request audit required')
  // Developer-only standard RPC login, never included in tool output or model workspace.
  ctx.inject(['connection', 'webServer'], child => {
    writeFileSync(join(dirname(configPath), 'desktop-ready.json'), JSON.stringify({
      url: child.connection.authenticatedUrl(`http://127.0.0.1:${child.webServer.port}`),
    }), { mode: 0o600 })
  })
  let stopped = false
  let owner: string | undefined
  const watches = new WeakSet<AbortSignal>()
  async function stop(): Promise<void> {
    stopped = true
    // Separate request, not cancelled together with the action; never retry actions.
    await fetch(URL, { method: 'POST', headers: { Authorization: `Bearer ${connection.token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ op: 'stop', args: {} }), signal: AbortSignal.timeout(5000) })
  }
  function watch(signal: AbortSignal): void {
    if (watches.has(signal)) return
    watches.add(signal)
    signal.addEventListener('abort', () => { void stop().catch(() => ctx.logger.error('C0 stop delivery failed; local dispatch remains denied')) }, { once: true })
    if (signal.aborted) void stop().catch(() => {})
  }
  ctx.on('agent/pre-step', async ({ agent, signal }, next) => {
    if (owner === undefined) owner = agent.session.id
    if (owner !== agent.session.id || stopped) throw new Error('C0 run already owned or stopped')
    watch(signal)
    return next()
  }, { global: true })
  ctx.tools.guard(exec => stopped || exec.signal.aborted ? 'C0 stopped'
    : !allowed.includes(exec.name) ? 'C0 tool not allowed'
    : !owner || !exec.agent || exec.agent.session.id !== owner ? 'C0 session not authorized' : undefined)
  ctx.on('agent/error', () => { void stop().catch(() => {}) }, { global: true })
  ctx.on('llm/stream', async function* (options, next) {
    const toolNames = (options.tools ?? []).map(tool => tool.name).sort()
    if (toolNames.some(tool => !allowed.includes(tool))) throw new Error('Unreviewed tool in C0 model request')
    const imageBlocks = options.messages.reduce((n, m) => n + (Array.isArray(m.content) ? m.content.filter(b => b.type === 'image').length : 0), 0)
    appendFileSync(auditPath, JSON.stringify({ at: new Date().toISOString(), toolNames,
      provider: options.provider, model: options.model,
      imageBlocks })+'\n', { mode: 0o600 })
    yield* next()
  })
  async function request(op: string, args: unknown, signal: AbortSignal): Promise<any> {
    watch(signal)
    if (stopped || signal.aborted) throw new Error('C0 stopped')
    const response = await fetch(URL, { method: 'POST',
      headers: { Authorization: `Bearer ${connection.token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ op, args }), signal: AbortSignal.any([signal, AbortSignal.timeout(40000)]) })
    const value = await response.json()
    if (!response.ok) throw new Error(value.error ?? 'VM request denied')
    return value
  }
  ctx.tools.register(defineTool({
    name: 'vm_observe', description: 'Observe the approved VM task window. Returns its fresh screenshot and AX elements; use element_index and element_token for exactly one action, then observe again.',
    parameters: {}, output: { schema: { type: 'object', additionalProperties: false, properties: {
      state: { type: 'string' }, image: { type: 'object', additionalProperties: false, properties: {
        attachmentId: { type: 'string' }, mediaType: { type: 'string' }, bytes: { type: 'integer' }, width: { type: 'integer' }, height: { type: 'integer' },
      } },
    } }, render: (_args, value) => [{ type: 'text', text: value.state },
      { type: 'image', attachment: { ...value.image, attachmentId: AttachmentId(value.image.attachmentId), name: 'vm-calculator.png' } }] },
    isConcurrencySafe: () => false,
    async execute(_args, exec) {
      await assertImageCapableRoute(ctx, exec)
      const value = await request('observe', {}, exec.signal)
      const image = await ctx.get('attachments')!.saveImage({ data: new Uint8Array(Buffer.from(value.png, 'base64')), mediaType: 'image/png', name: 'vm-calculator.png' })
      return { state: JSON.stringify({ ...value.state, used: value.used }), image: {
        attachmentId: image.attachmentId, mediaType: image.mediaType, bytes: image.bytes, width: image.width, height: image.height,
      } }
    },
  }))
  const specifications = [
    { name: 'vm_click', op: 'click', description: 'Click one permitted task AX button from the latest observation. Never batch or reuse an observation.', parameters: {
      snapshot_id: { type: 'string', required: true }, element_index: { type: 'integer', required: true }, element_token: { type: 'string', required: true },
    } },
    { name: 'vm_write_result', op: 'write_result', description: 'Write result.txt inside this VM task only. Value must match the latest independently grounded task UI result; no overwrite.', parameters: {
      snapshot_id: { type: 'string', required: true }, value: { type: 'string', required: true },
    } },
    { name: 'vm_read_result', op: 'read_result', description: 'Read back this VM task result.txt. No arbitrary path.', parameters: {} },
  ] as const
  for (const spec of specifications) ctx.tools.register(defineTool({
    name: spec.name, description: spec.description, parameters: spec.parameters,
    output: { schema: { type: 'object', additionalProperties: false, properties: { result: { type: 'string' } } }, render: (_args, value) => [{ type: 'text', text: value.result }] },
    isConcurrencySafe: () => false,
    async execute(args, exec) { return { result: JSON.stringify(await request(spec.op, args, exec.signal)) } },
  }))
  if (allowed.includes('vm_type')) ctx.tools.register(defineTool({
    name: 'vm_type', description: 'Type the reviewed task text into an approved field from a fresh observation. Only this task field/text pair is permitted; no arbitrary input.',
    parameters: { snapshot_id: { type: 'string', required: true }, element_index: { type: 'integer', required: true },
      element_token: { type: 'string', required: true }, text: { type: 'string', required: true } },
    output: { schema: { type: 'object', additionalProperties: false, properties: { result: { type: 'string' } } }, render: (_args, value) => [{ type: 'text', text: value.result }] },
    isConcurrencySafe: () => false,
    async execute(args, exec) { return { result: JSON.stringify(await request('type_text', args, exec.signal)) } },
  }))
  if (allowed.includes('vm_scroll')) ctx.tools.register(defineTool({
    name: 'vm_scroll', description: 'Scroll at x/y screenshot pixels inside the approved task viewport from a fresh screenshot. AX containers are not indexed by this Driver. Read coordinates from the screenshot, never from desktop points. Direction up/down, amount 1–10. Observe effect before another action.',
    parameters: { snapshot_id: { type: 'string', required: true }, x: { type: 'number', required: true },
      y: { type: 'number', required: true }, direction: { type: 'string', required: true }, amount: { type: 'integer', required: true } },
    output: { schema: { type: 'object', additionalProperties: false, properties: { result: { type: 'string' } } }, render: (_args, value) => [{ type: 'text', text: value.result }] },
    isConcurrencySafe: () => false,
    async execute(args, exec) { return { result: JSON.stringify(await request('scroll', args, exec.signal)) } },
  }))
}
