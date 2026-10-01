/** No VM, model or credentials: adapter boundary tests only. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { mkdtempSync, writeFileSync, rmSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { apply } from './c0-vm-tools.ts'

test('C0 fixed tools, ownership, fresh image attachment, cancellation and no retry', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'cuagent-c0-test-'))
  const old = { connection: process.env.CUAGENT_C0_CONNECTION, audit: process.env.CUAGENT_C0_AUDIT_PATH, fetch: globalThis.fetch }
  t.after(() => {
    globalThis.fetch = old.fetch
    if (old.connection === undefined) delete process.env.CUAGENT_C0_CONNECTION
    else process.env.CUAGENT_C0_CONNECTION = old.connection
    if (old.audit === undefined) delete process.env.CUAGENT_C0_AUDIT_PATH
    else process.env.CUAGENT_C0_AUDIT_PATH = old.audit
    rmSync(dir, { recursive: true, force: true })
  })
  process.env.CUAGENT_C0_CONNECTION = join(dir, 'connection.json')
  process.env.CUAGENT_C0_AUDIT_PATH = join(dir, 'audit.jsonl')
  writeFileSync(process.env.CUAGENT_C0_CONNECTION, JSON.stringify({ url: 'http://192.168.64.3:8766', token: 'x'.repeat(43) }), { mode: 0o600 })
  const tools: any[] = [], handlers = new Map(), calls: string[] = []
  let guard: any, failed = false
  const attachment = { attachmentId: 'image-1', mediaType: 'image/png', bytes: 8, width: 1, height: 1 }
  const ctx: any = {
    inject() {},
    tools: { register: (tool: any) => tools.push(tool), guard: (fn: any) => { guard = fn } },
    on: (name: string, fn: any) => handlers.set(name, fn), logger: { error() {} },
    get: (name: string) => name === 'llm' ? { resolveModelInfo: async () => ({ inputModalities: ['image'] }) }
      : { saveImage: async ({ data }: any) => { assert.equal(data.length, 8); return attachment } },
  }
  globalThis.fetch = (async (url: any, options: any) => {
    assert.equal(url, 'http://192.168.64.3:8766')
    const { op } = JSON.parse(options.body); calls.push(op)
    if (failed && op !== 'stop') throw new Error('timeout')
    return { ok: true, json: async () => ({ state: { snapshot_id: 's' }, png: Buffer.from([137,80,78,71,13,10,26,10]).toString('base64') }) }
  }) as any
  apply(ctx)
  assert.deepEqual(tools.map(t => t.name), ['vm_observe','vm_click','vm_write_result','vm_read_result'])
  const signal = new AbortController()
  assert.match(guard({ name: 'vm_observe', signal: signal.signal }), /not authorized/)
  const agent: any = { session: { id: 's1', requestHeader: () => undefined }, options: { provider: 'test', model: 'image' } }
  await handlers.get('agent/pre-step')({ agent, signal: signal.signal }, async () => ({}))
  assert.match(guard({ name: 'shell', agent, signal: signal.signal }), /not allowed/)
  assert.match(guard({ name: 'vm_observe', agent: { session: { id: 'other' } }, signal: signal.signal }), /not authorized/)
  const observed = await tools[0].execute({}, { agent, signal: signal.signal })
  assert.equal(tools[0].output.render({}, observed)[1].type, 'image')
  assert.equal(observed.image.attachmentId, 'image-1')
  failed = true
  await assert.rejects(tools[1].execute({ snapshot_id: 's', element_index: 1, element_token: 't' }, { signal: signal.signal }), /timeout/)
  assert.equal(calls.filter(c => c === 'click').length, 1)
  signal.abort('user stop')
  await Promise.resolve()
  assert.equal(calls.at(-1), 'stop')
  assert.match(guard({ name: 'vm_observe', agent, signal: new AbortController().signal }), /stopped/)
  await assert.rejects(tools[0].execute({}, { agent, signal: new AbortController().signal }), /stopped/)
  assert.equal(calls.filter(c => c === 'observe').length, 1)
})
