/** Installed official registry, simulated VM response. No model or GUI. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { Context } from '@deepseek-ai/cordis'
import { ToolCallId } from '@deepseek-ai/dsh-llm'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import ToolRuntime from '@deepseek-ai/dsh-tools'
import { registerHandoffSubmit } from './handoff-submit.ts'

const binding = { runId: 'p2-11111111-1111-1111-1111-111111111111',
  sessionId: 'session-22222222-2222-2222-2222-222222222222', inputSha256: 'a'.repeat(64) }
const receipt = () => ({ ...binding, status: 'HANDOFF_SUBMITTED', protocol: 'p7-tool-submit-v1',
  reportSha256: 'b'.repeat(64), documentSha256: 'c'.repeat(64), used: 18,
  semanticVerified: false, guiVerified: false })
async function fixture(t: any, respond = async (_args: unknown) => receipt()) {
  const ctx = new Context()
  await ctx.plugin(SystemPrompt, {}); await ctx.plugin(ToolRuntime)
  t.after(() => ctx.fiber.dispose())
  let requests = 0, stops = 0, other = 0, serial = 0
  const gate = registerHandoffSubmit(ctx, binding, async args => { requests++; return respond(args) }, async () => { stops++ })
  ctx.tools.register({ name: 'after_submit', description: 'test only', parameters: { type: 'object', properties: {} },
    output: { schema: { type: 'object', properties: {} }, render: () => [] },
    execute: async () => { other++; return {} } })
  const call = (name = 'vm_submit_handoff', args: unknown = { report: { unchanged: true } },
    signal = new AbortController().signal, sessionId = binding.sessionId) => ctx.tools.execute({
    callId: ToolCallId(`s-${++serial}`), name, arguments: args, signal,
    agent: { id: sessionId, session: { id: sessionId } } as any,
  })
  return { ctx, gate, call, counts: () => ({ requests, stops, other }) }
}

test('official successful result commits and concludes; subsequent calls never dispatch', async t => {
  const f = await fixture(t)
  const result = await f.call()
  assert.equal(result.isError, false, JSON.stringify(result))
  assert.equal(result.concludesTurn, true)
  assert.equal(f.gate.state(), 'committed')
  assert.equal((await f.call('after_submit')).isError, true)
  assert.equal((await f.call()).isError, true)
  assert.deepEqual(f.counts(), { requests: 1, stops: 0, other: 0 })
})

test('pending HTTP locks concurrent and later tool bodies before response', async t => {
  let release!: () => void, started!: () => void
  const ready = new Promise<void>(resolve => { started = resolve })
  const pending = new Promise<void>(resolve => { release = resolve })
  const f = await fixture(t, async () => { started(); await pending; return receipt() })
  const first = f.call(); await ready
  assert.equal(f.gate.state(), 'pending')
  assert.equal((await f.call()).isError, true)
  assert.equal((await f.call('after_submit')).isError, true)
  release(); assert.equal((await first).isError, false)
  assert.deepEqual(f.counts(), { requests: 1, stops: 0, other: 0 })
})

for (const fault of ['lost', 'status', 'session', 'protocol', 'used', 'hash', 'semantic', 'extra']) {
  test(`unconfirmed ${fault} locks original attempt without retry or terminal success`, async t => {
    const f = await fixture(t, async () => {
      if (fault === 'lost') throw new Error('response lost')
      const r: any = receipt()
      if (fault === 'status') r.status = 'DRAFT_REJECTED'
      if (fault === 'session') r.sessionId = 'other'
      if (fault === 'protocol') r.protocol = 'legacy-final-json'
      if (fault === 'used') r.used = true
      if (fault === 'hash') r.reportSha256 = 'wrong'
      if (fault === 'semantic') r.semanticVerified = true
      if (fault === 'extra') r.extra = 1
      return r
    })
    const result = await f.call()
    assert.equal(result.isError, true); assert.equal(result.concludesTurn, undefined)
    assert.equal(f.gate.state(), 'failed')
    assert.equal((await f.call()).isError, true)
    assert.deepEqual(f.counts(), { requests: 1, stops: 1, other: 0 })
  })
}

test('wrong session and already aborted requests never reach VM', async t => {
  const f = await fixture(t)
  assert.equal((await f.call(undefined, {}, undefined, 'other')).isError, true)
  assert.equal((await f.call(undefined, {}, AbortSignal.abort())).isError, true)
  assert.deepEqual(f.counts(), { requests: 0, stops: 0, other: 0 })
})

test('abort while pending cannot commit a late HTTP success', async t => {
  const controller = new AbortController()
  const f = await fixture(t, async () => { controller.abort(); return receipt() })
  const result = await f.call(undefined, {}, controller.signal)
  assert.equal(result.isError, true); assert.notEqual(f.gate.state(), 'committed')
  assert.equal((await f.call()).isError, true)
  assert.equal(f.counts().requests, 1)
})

test('outer pipeline failure cannot commit a successful VM response', async t => {
  const f = await fixture(t)
  f.ctx.on('tools/execute', async (_exec, next) => { await next(); throw new Error('outer failure') })
  const result = await f.call()
  assert.equal(result.isError, true); assert.equal(result.concludesTurn, undefined)
  assert.equal(f.gate.state(), 'failed')
  assert.deepEqual(f.counts(), { requests: 1, stops: 1, other: 0 })
})

test('post-execute output replacement is not an authoritative original receipt', async t => {
  const f = await fixture(t)
  f.ctx.on('tools/post-execute', async () => ({ decision: 'accept', value: { result: 'changed' } }))
  await f.call()
  assert.equal(f.gate.state(), 'failed')
  assert.equal((await f.call('after_submit')).isError, true)
  assert.deepEqual(f.counts(), { requests: 1, stops: 1, other: 0 })
})
