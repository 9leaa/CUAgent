/** Actual same-version Cordis, tool registry and local attachment service. No LLM. */
import assert from 'node:assert/strict'
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'
import { Context } from '@deepseek-ai/cordis'
import { ToolCallId } from '@deepseek-ai/dsh-llm'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import ToolRuntime from '@deepseek-ai/dsh-tools'
import LocalAttachmentStore from '@deepseek-ai/dsh-attachment-local'
import type { Agent } from '@deepseek-ai/dsh-agent'
import * as policyPlugin from './a1-policy-plugin.ts'
import * as toolsPlugin from './a1-tools.ts'
import * as fingerprintPlugin from './a1-example-fingerprint.ts'

async function fixture(t: any, options: { readOnly?: boolean, example?: boolean, dailyReport?: boolean, controlled?: boolean, publishNotBefore?: number, invalidApproval?: 'missing' | 'malformed' | 'duplicate' | 'public' } = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'cuagent-a1-registry-'))
  const previous = process.env.CUAGENT_A1_TASKS_PATH
  const tasks = ['one', 'two'].map(id => {
    const workspaceRoot = join(dir, `workspace-${id}`), audit = join(dir, `audit-${id}`)
    mkdirSync(workspaceRoot); mkdirSync(audit, { mode: 0o700 })
    writeFileSync(join(workspaceRoot, 'source.txt'), `ONLY_${id}`)
    writeFileSync(join(workspaceRoot, 'sales.csv'), 'units\n2\n4\n')
    const controlPath = join(audit, 'control.json')
    if (options.controlled) writeFileSync(controlPath, JSON.stringify({ version: 1, runId: `run-${id}`, epoch: 1, stopped: false, expiresAt: Date.now() + 30000 }), { mode: 0o600 })
    return { workspaceRoot, ledgerPath: join(audit, 'calls.jsonl'), runId: `run-${id}`, sessionId: `session-${id}`,
      ...(options.controlled ? { controlPath, controlEpoch: 1 } : {}),
      ...(options.publishNotBefore ? { publishNotBefore: options.publishNotBefore } : {}),
      allowedTools: options.dailyReport ? ['workspace_list', 'workspace_read', 'workspace_write', 'workspace_csv_stats', 'workspace_daily_report']
        : options.readOnly ? ['calculate', 'workspace_list', 'workspace_read', 'workspace_csv_stats']
        : ['calculate', 'workspace_image_probe', 'workspace_list', 'workspace_read', 'workspace_write', 'workspace_csv_stats', ...(options.example ? ['workspace_text_fingerprint'] : [])] }
  })
  const config = join(dir, 'tasks.json')
  writeFileSync(config, JSON.stringify({ version: 1, tasks }), { mode: 0o600 })
  process.env.CUAGENT_A1_TASKS_PATH = config
  if (options.invalidApproval === 'missing') process.env.CUAGENT_A1_TASKS_PATH = join(dir, 'missing.json')
  if (options.invalidApproval === 'malformed') writeFileSync(config, '{broken')
  if (options.invalidApproval === 'duplicate') writeFileSync(config, JSON.stringify({ version: 1, tasks: [tasks[0], { ...tasks[1], sessionId: tasks[0].sessionId }] }))
  if (options.invalidApproval === 'public') chmodSync(config, 0o644)
  const ctx = new Context()
  await ctx.plugin(SystemPrompt, {}); await ctx.plugin(ToolRuntime)
  await ctx.plugin(LocalAttachmentStore, { dshHome: join(dir, 'home') })
  const policyFiber = await ctx.plugin(policyPlugin)
  const toolsFiber = await ctx.plugin(toolsPlugin, { readOnly: options.readOnly ?? false, dailyReport: options.dailyReport ?? false })
  t.after(() => {
    ctx.fiber.dispose()
    if (previous === undefined) delete process.env.CUAGENT_A1_TASKS_PATH
    else process.env.CUAGENT_A1_TASKS_PATH = previous
    rmSync(dir, { recursive: true, force: true })
  })
  let serial = 0
  const call = (name: string, args: unknown, session = 'session-one', signal = new AbortController().signal) =>
    ctx.tools.execute({ name, arguments: args, callId: ToolCallId(`real-${++serial}`), signal,
      agent: { id: session, session: { id: session } } as unknown as Agent })
  const ledger = (n = 0) => readFileSync(tasks[n].ledgerPath, 'utf8').trim().split('\n').map(JSON.parse)
  return { ctx, tasks, config, call, ledger, policyFiber, toolsFiber }
}

const daily = { date: '2026-10-02', notes: [{ path: 'inputs/n.md', sha256: 'a'.repeat(64), title: 'A', progress: 'Done', blockers: 'None', next: 'Review' }],
  csv: [{ path: 'inputs/m.csv', sha256: 'b'.repeat(64), rowCount: 1, columnCount: 1, columns: ['n'], bytes: 4,
    numeric: { n: { count: 1, missing: 0, sum: 2, min: 2, max: 2, mean: 2 } } }] }

test('P3 actual registry rejects early publication and ordinary-write bypass', async t => {
  let now = Date.now()
  t.mock.method(Date, 'now', () => now)
  const { call, tasks, ledger } = await fixture(t, { dailyReport: true, publishNotBefore: now + 60000 })
  assert.equal((await call('workspace_write', { path: 'report.json', content: JSON.stringify(daily) })).isError, false)
  assert.equal((await call('workspace_daily_report', {})).isError, true)
  assert.equal((await call('workspace_write', { path: 'report.md', content: 'bypass' })).isError, true)
  assert.equal(existsSync(join(tasks[0].workspaceRoot, 'report.md')), false)
  assert.equal(ledger().filter(row => row.event === 'dispatch').length, 1)
  now += 60000
  assert.equal((await call('workspace_daily_report', {})).isError, false)
  assert.equal(ledger().filter(row => row.event === 'dispatch').length, 3)
})

test('P2 official registry denies stopped, expired and stale-epoch leases before dispatch', async t => {
  const { call, ledger, tasks, ctx } = await fixture(t, { controlled: true, dailyReport: true })
  assert.equal((await call('workspace_read', { path: 'source.txt' })).isError, false)
  const path = tasks[0].controlPath!
  const original = JSON.parse(readFileSync(path, 'utf8'))
  for (const change of [{ stopped: true }, { expiresAt: Date.now() - 1 }, { epoch: 2 }, { runId: 'other' }]) {
    writeFileSync(path, JSON.stringify({ ...original, ...change }))
    assert.equal((await call('workspace_write', { path: 'must-not-exist.txt', content: 'no' })).isError, true)
    assert.throws(() => ctx.get('cuagentA1Policy')!.request({ sessionId: 'session-one', tools: [{ name: 'workspace_read' }], messages: [] }))
  }
  writeFileSync(path, JSON.stringify(original)); chmodSync(path, 0o644)
  assert.equal((await call('workspace_daily_report', {})).isError, true)
  assert.equal(ledger().filter(row => row.event === 'dispatch').length, 1)
  assert.equal(existsSync(join(tasks[0].workspaceRoot, 'must-not-exist.txt')), false)
})

test('P1 renderer uses actual registry and counts internal read plus write; never overwrites', async t => {
  const { call, ledger, tasks } = await fixture(t, { dailyReport: true })
  writeFileSync(join(tasks[0].workspaceRoot, 'report.json'), JSON.stringify(daily))
  const result = await call('workspace_daily_report', {})
  assert.equal(result.isError, false, JSON.stringify(result.content))
  const original = readFileSync(join(tasks[0].workspaceRoot, 'report.md'), 'utf8')
  assert.ok(original.startsWith('# 日报 2026-10-02\n\n## A\n'))
  assert.ok(original.endsWith('| n | 1 | 0 | 2 | 2 | 2 | 2 |\n'))
  const dispatch = ledger().filter(row => row.event === 'dispatch')
  assert.deepEqual(dispatch.map(row => row.used), [1, 2])
  assert.equal(dispatch[1].callId, dispatch[0].callId + ':daily-source')
  assert.equal(ledger().filter(row => row.event === 'result').length, 2)
  assert.equal((await call('workspace_daily_report', {})).isError, true)
  assert.equal(readFileSync(join(tasks[0].workspaceRoot, 'report.md'), 'utf8'), original)
  assert.equal(ledger().filter(row => row.event === 'dispatch').length, 4)
})

test('P1 renderer cannot turn one remaining slot into two actual requests', async t => {
  const { call, ledger, tasks } = await fixture(t, { dailyReport: true })
  writeFileSync(join(tasks[0].workspaceRoot, 'report.json'), JSON.stringify(daily))
  for (let i = 0; i < 29; i++) assert.equal((await call('workspace_read', { path: 'source.txt' })).isError, false)
  assert.equal((await call('workspace_daily_report', {})).isError, true)
  assert.equal(existsSync(join(tasks[0].workspaceRoot, 'report.md')), false)
  assert.equal(ledger().filter(row => row.event === 'dispatch').length, 30)
  assert.equal(ledger().filter(row => row.event === 'result').length, 30)
})

test('P1 renderer is opt-in, rejects stopped requests and unavailable policy', async t => {
  const { call, tasks, policyFiber } = await fixture(t, { dailyReport: true })
  writeFileSync(join(tasks[0].workspaceRoot, 'report.json'), JSON.stringify(daily))
  const stop = new AbortController(); stop.abort()
  assert.equal((await call('workspace_daily_report', {}, 'session-one', stop.signal)).isError, true)
  assert.equal((await call('calculate', { expression: '1+1' })).isError, true)
  await policyFiber.dispose()
  assert.equal((await call('workspace_daily_report', {})).isError, true)
  assert.equal(existsSync(join(tasks[0].workspaceRoot, 'report.md')), false)
})

test('A1 official registry isolates two approved roots and rejects foreign session/path/stop', async t => {
  const { call, ledger } = await fixture(t)
  for (const id of ['one', 'two']) {
    const read = await call('workspace_read', { path: 'source.txt' }, `session-${id}`)
    assert.equal(read.isError, false)
    if (!read.isError) assert.equal((read.value as any).content, `ONLY_${id}`)
  }
  const escaping = await call('workspace_read', { path: '../workspace-two/source.txt' })
  assert.equal(escaping.isError, true)
  if (escaping.isError) assert.equal(escaping.error.info?.code, 'PARENT_PATH_DENIED')
  assert.equal((await call('workspace_read', { path: 'source.txt' }, 'not-approved')).isError, true)
  const stop = new AbortController(); stop.abort('stop')
  assert.equal((await call('workspace_write', { path: 'stopped.txt', content: 'no' }, 'session-one', stop.signal)).isError, true)
  assert.equal(ledger(0).filter(entry => entry.event === 'dispatch').length, 2)
  assert.equal(ledger(1).filter(entry => entry.event === 'dispatch').length, 1)
  assert.ok(ledger(0).some(entry => entry.event === 'result' && entry.outcome === 'error'))
})

test('A1 actual tool and policy unload/reload retains budget and denies orphaned tool bodies', async t => {
  const { ctx, call, ledger, tasks, toolsFiber, policyFiber } = await fixture(t)
  assert.equal((await call('workspace_write', { path: 'new.txt', content: 'hello' })).isError, false)
  await toolsFiber.dispose()
  assert.equal((await call('workspace_read', { path: 'new.txt' })).isError, true)
  await ctx.plugin(toolsPlugin)
  assert.equal((await call('workspace_read', { path: 'new.txt' })).isError, false)
  await policyFiber.dispose()
  assert.equal((await call('workspace_write', { path: 'orphan.txt', content: 'no' })).isError, true)
  assert.equal((await call('calculate', { expression: '1+1' })).isError, true)
  assert.equal(existsSync(join(tasks[0].workspaceRoot, 'orphan.txt')), false)
  await ctx.plugin(policyPlugin)
  const csv = await call('workspace_csv_stats', { path: 'sales.csv', numericColumns: ['units'] })
  assert.equal(csv.isError, false)
  if (!csv.isError) assert.equal(JSON.parse((csv.value as any).result).numeric.units.sum, 6)
  // Missing/unloaded tool requests count too: write, failed read, read, CSV.
  assert.equal(ledger().filter(entry => entry.event === 'dispatch').length, 4)
  assert.equal(ledger().filter(entry => entry.event === 'result').length, 4)
  assert.equal(ledger().filter(entry => entry.event === 'result' && entry.outcome === 'error').length, 1)
  assert.ok(!ledger().some(entry => entry.event === 'dispatch' && entry.used > 4))
})

test('A1 request-side guard rejects extra tools and unapproved sessions, logs no prompt', async t => {
  const { ctx, ledger } = await fixture(t)
  const service = ctx.get('cuagentA1Policy')!
  const options = { sessionId: 'session-one', provider: 'test-provider', model: 'test-model',
    tools: [{ name: 'workspace_read' }], messages: [{ content: 'SECRET_PROMPT' }] }
  service.request(options)
  assert.equal(ledger().filter(entry => entry.event === 'request').length, 1)
  assert.ok(!JSON.stringify(ledger()).includes('SECRET_PROMPT'))
  assert.throws(() => service.request({ ...options, tools: [{ name: 'bash' }] }), /unapproved tool/)
  assert.throws(() => service.request({ ...options, sessionId: 'other' }), /approved task/)
  assert.equal(ledger().filter(entry => entry.event === 'dispatch').length, 0)
})

test('A1 read-only subset cannot gain writes/images from preset registration or request list', async t => {
  const { ctx, call, tasks, ledger } = await fixture(t, { readOnly: true })
  assert.equal((await call('workspace_read', { path: 'source.txt' })).isError, false)
  assert.equal((await call('workspace_write', { path: 'forbidden.txt', content: 'no' })).isError, true)
  assert.equal((await call('workspace_image_probe', {})).isError, true)
  assert.equal(existsSync(join(tasks[0].workspaceRoot, 'forbidden.txt')), false)
  assert.equal(ledger().filter(event => event.event === 'dispatch').length, 1)
  assert.throws(() => ctx.get('cuagentA1Policy')!.request({ sessionId: 'session-one', messages: [], tools: [{ name: 'workspace_write' }] }), /unapproved tool/)
})

test('A1 opt-in fingerprint example returns exact metadata, stable path error and cancellation', async t => {
  const { ctx, call, ledger, tasks } = await fixture(t, { example: true })
  await ctx.plugin(fingerprintPlugin)
  const result = await call('workspace_text_fingerprint', { path: 'source.txt' })
  assert.equal(result.isError, false)
  if (!result.isError) assert.deepEqual(result.value, { path: 'source.txt', bytes: 8, sha256: (await import('node:crypto')).createHash('sha256').update('ONLY_one').digest('hex') })
  const denied = await call('workspace_text_fingerprint', { path: '../outside.txt' })
  assert.equal(denied.isError, true)
  if (denied.isError) assert.equal(denied.error.info?.code, 'PARENT_PATH_DENIED')
  for (const args of [{ path: 1 }, {}, { path: 'source.txt', workspaceRoot: '/arbitrary' }]) {
    const invalid = await call('workspace_text_fingerprint', args)
    assert.equal(invalid.isError, true)
    if (invalid.isError) assert.equal(invalid.error.info?.code, 'INVALID_ARGS')
  }
  const stopped = new AbortController(); stopped.abort('stop')
  assert.equal((await call('workspace_text_fingerprint', { path: 'source.txt' }, 'session-one', stopped.signal)).isError, true)
  assert.equal(ledger().filter(event => event.event === 'dispatch').length, 5)
  assert.equal(readFileSync(join(tasks[0].workspaceRoot, 'source.txt'), 'utf8'), 'ONLY_one')
})

test('fingerprint registration without explicit task approval remains denied', async t => {
  const { ctx, call, ledger } = await fixture(t)
  await ctx.plugin(fingerprintPlugin)
  assert.equal((await call('workspace_text_fingerprint', { path: 'source.txt' })).isError, true)
  assert.equal(ledger().filter(event => event.event === 'dispatch').length, 0)
})

test('A1 missing or invalid approval denies every task and model request without dispatch or effects', async t => {
  for (const invalidApproval of ['missing', 'malformed', 'duplicate', 'public'] as const) {
    const { ctx, call, tasks } = await fixture(t, { invalidApproval })
    for (const task of tasks) {
      assert.equal((await call('workspace_read', { path: 'source.txt' }, task.sessionId)).isError, true)
      assert.equal((await call('workspace_write', { path: 'forbidden.txt', content: 'no' }, task.sessionId)).isError, true)
      assert.equal((await call('calculate', { expression: '1+1' }, task.sessionId)).isError, true)
      assert.equal(existsSync(task.ledgerPath), false)
      assert.equal(existsSync(join(task.workspaceRoot, 'forbidden.txt')), false)
      assert.throws(() => ctx.get('cuagentA1Policy')!.request({ sessionId: task.sessionId, messages: [], tools: [] }), /approved task/)
    }
    await ctx.fiber.dispose()
  }
})

test('approved fingerprint tool remains blocked after actual policy unload', async t => {
  const { ctx, call, ledger, policyFiber } = await fixture(t, { example: true })
  await ctx.plugin(fingerprintPlugin)
  assert.equal((await call('workspace_text_fingerprint', { path: 'source.txt' })).isError, false)
  await policyFiber.dispose()
  assert.equal((await call('workspace_text_fingerprint', { path: 'source.txt' })).isError, true)
  assert.equal(ledger().filter(event => event.event === 'dispatch').length, 1)
})

test('A1 actual parallel dispatch respects persistent 30 calls and configuration override fails closed', async t => {
  const { call, ledger, config, tasks } = await fixture(t)
  const results = await Promise.all(Array.from({ length: 31 }, () => call('calculate', { expression: '1+1' })))
  assert.equal(results.filter(result => !result.isError).length, 30)
  assert.equal(ledger().filter(entry => entry.event === 'dispatch').length, 30)
  assert.equal(ledger().filter(entry => entry.event === 'result').length, 30)
  // Other task has its own budget, but editing the launch-approved config is not approval.
  assert.equal((await call('workspace_read', { path: 'source.txt' }, 'session-two')).isError, false)
  writeFileSync(config, JSON.stringify({ version: 1, tasks: [{ ...tasks[1], allowedTools: ['workspace_write'] }] }))
  assert.equal((await call('workspace_write', { path: 'override.txt', content: 'no' }, 'session-two')).isError, true)
  assert.equal(ledger(1).filter(entry => entry.event === 'dispatch').length, 1)
})

test('A1 actual registry preserves complete file boundaries and protected evidence without free retries', async t => {
  const { call, tasks, ledger } = await fixture(t)
  const root = tasks[0].workspaceRoot, peer = tasks[1].workspaceRoot
  symlinkSync(join(peer, 'source.txt'), join(root, 'escape.txt'))
  symlinkSync(peer, join(root, 'parent'))
  symlinkSync(join(root, 'source.txt'), join(root, 'internal.txt'))
  symlinkSync(tasks[0].ledgerPath, join(root, 'audit.json'))
  writeFileSync(join(root, 'binary.txt'), Buffer.from([0, 255]))
  writeFileSync(join(root, 'oversize.txt'), Buffer.alloc(1024 * 1024 + 1, 65))
  writeFileSync(join(root, 'type.exe'), 'forbidden')
  assert.equal((await call('workspace_write', { path: 'result.txt', content: 'SAFE_ORIGINAL' })).isError, false)
  const legalRead = await call('workspace_read', { path: 'result.txt' })
  assert.equal(legalRead.isError, false)
  if (!legalRead.isError) assert.equal((legalRead.value as any).content, 'SAFE_ORIGINAL')
  const cases = [
    ['workspace_read', { path: join(peer, 'source.txt') }, 'ABSOLUTE_PATH_DENIED'],
    ['workspace_write', { path: join(peer, 'escape.txt'), content: 'bad' }, 'ABSOLUTE_PATH_DENIED'],
    ['workspace_read', { path: '../workspace-two/source.txt' }, 'PARENT_PATH_DENIED'],
    ['workspace_write', { path: '../workspace-two/escape.txt', content: 'bad' }, 'PARENT_PATH_DENIED'],
    ['workspace_read', { path: 'escape.txt' }, 'SYMLINK_ESCAPE_DENIED'],
    ['workspace_write', { path: 'escape.txt', content: 'bad' }, 'SYMLINK_WRITE_DENIED'],
    ['workspace_write', { path: 'internal.txt', content: 'bad' }, 'SYMLINK_WRITE_DENIED'],
    ['workspace_write', { path: 'parent/escape.txt', content: 'bad' }, 'SYMLINK_ESCAPE_DENIED'],
    ['workspace_list', { path: 'parent' }, 'SYMLINK_ESCAPE_DENIED'],
    ['workspace_read', { path: 'type.exe' }, 'FILE_TYPE_DENIED'],
    ['workspace_write', { path: 'new.exe', content: 'bad' }, 'FILE_TYPE_DENIED'],
    ['workspace_read', { path: 'binary.txt' }, 'BINARY_FILE_DENIED'],
    ['workspace_write', { path: 'new.txt', content: 'bad\0bytes' }, 'BINARY_CONTENT_DENIED'],
    ['workspace_read', { path: 'oversize.txt' }, 'FILE_TOO_LARGE'],
    ['workspace_write', { path: 'large.txt', content: 'x'.repeat(256 * 1024 + 1) }, 'CONTENT_TOO_LARGE'],
    ['workspace_write', { path: 'result.txt', content: 'bad' }, 'FILE_EXISTS'],
    // Unknown root/overwrite fields cannot grant overwrite; adapters never forward them.
    ['workspace_write', { path: 'result.txt', content: 'bad', overwrite: true, workspaceRoot: peer }, 'FILE_EXISTS'],
    ['workspace_read', { path: 'audit.json' }, 'SYMLINK_ESCAPE_DENIED'],
    ['workspace_write', { path: 'audit.json', content: 'bad' }, 'SYMLINK_WRITE_DENIED'],
    ['workspace_read', { path: '.' }, 'NOT_A_FILE'],
    ['workspace_read', { path: 'source.txt\0' }, 'INVALID_PATH'],
  ] as const
  for (const [name, args, code] of cases) {
    const result = await call(name, args)
    assert.equal(result.isError, true, `${name}: ${code}`)
    if (result.isError) assert.equal(result.error.info?.code, code)
  }
  const audit = ledger()
  assert.equal(audit.filter(entry => entry.event === 'dispatch').length, cases.length + 2)
  assert.equal(audit.filter(entry => entry.event === 'result').length, cases.length + 2)
  assert.equal(audit.filter(entry => entry.event === 'result' && entry.outcome === 'error').length, cases.length)
  assert.ok(audit.every(entry => entry.sessionId === tasks[0].sessionId && entry.runId === tasks[0].runId))
  assert.ok(!JSON.stringify(audit).includes('SAFE_ORIGINAL'))
  assert.equal(readFileSync(join(root, 'result.txt'), 'utf8'), 'SAFE_ORIGINAL')
  assert.equal(readFileSync(join(root, 'source.txt'), 'utf8'), 'ONLY_one')
  assert.equal(readFileSync(join(peer, 'source.txt'), 'utf8'), 'ONLY_two')
  for (const file of [join(peer, 'escape.txt'), join(root, 'new.exe'), join(root, 'new.txt'), join(root, 'large.txt')]) assert.equal(existsSync(file), false)
})
