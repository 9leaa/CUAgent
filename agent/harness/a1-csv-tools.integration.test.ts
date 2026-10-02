/** Same-version official tool registry. No model, credentials or desktop actions. */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'
import { Context } from '@deepseek-ai/cordis'
import { ToolCallId } from '@deepseek-ai/dsh-llm'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import ToolRuntime from '@deepseek-ai/dsh-tools'
import type { Agent } from '@deepseek-ai/dsh-agent'
import { apply as csvTools } from './a1-csv-tools.ts'
import { apply as a0Policy } from './a0-policy-plugin.ts'

const source = 'region,units,revenue\nNorth,2,100\nSouth,3,150\nEast,1,70\nWest,5,110\nNorth,3,\n'

async function fixture(t: any) {
  const dir = mkdtempSync(join(tmpdir(), 'cuagent-a1-csv-'))
  const workspace = join(dir, 'workspace')
  mkdirSync(workspace)
  const keys = ['CUAGENT_A1_WORKSPACE_ROOT', 'CUAGENT_A0_WORKSPACE_ROOT',
    'CUAGENT_A0_RUN_ID', 'CUAGENT_A0_AUDIT_PATH']
  const before = Object.fromEntries(keys.map(key => [key, process.env[key]]))
  process.env.CUAGENT_A1_WORKSPACE_ROOT = workspace
  t.after(() => {
    for (const key of keys) {
      if (before[key] === undefined) delete process.env[key]
      else process.env[key] = before[key]
    }
    rmSync(dir, { recursive: true, force: true })
  })
  const ctx = new Context()
  await ctx.plugin(SystemPrompt, {})
  await ctx.plugin(ToolRuntime)
  t.after(() => ctx.fiber.dispose())
  writeFileSync(join(workspace, 'sales.csv'), source)
  const agent = { id: 'a1-csv-session', session: { id: 'a1-csv-session' } } as unknown as Agent
  let serial = 0
  const call = (args: unknown, signal = new AbortController().signal) => ctx.tools.execute({
    callId: ToolCallId(`csv-${++serial}`), name: 'workspace_csv_stats',
    arguments: args, agent, signal,
  })
  return { ctx, dir, workspace, call }
}

test('A1 CSV actual registry exposes complete statistics and input hash', async t => {
  const { ctx, workspace, call } = await fixture(t)
  csvTools(ctx)
  const result = await call({ path: 'sales.csv', numericColumns: ['units', 'revenue'] })
  assert.equal(result.isError, false, JSON.stringify(result.content))
  if (result.isError) throw new Error('CSV failed')
  const actual = JSON.parse((result.value as { result: string }).result)
  assert.equal(actual.rowCount, 5)
  assert.equal(actual.columnCount, 3)
  assert.deepEqual(actual.columns, ['region', 'units', 'revenue'])
  assert.deepEqual(actual.numeric.units, { count: 5, missing: 0, sum: 14, min: 1, max: 5, mean: 2.8 })
  assert.deepEqual(actual.numeric.revenue, { count: 4, missing: 1, sum: 430, min: 70, max: 150, mean: 107.5 })
  assert.equal(actual.sha256, createHash('sha256').update(readFileSync(join(workspace, 'sales.csv'))).digest('hex'))
  assert.equal(readFileSync(join(workspace, 'sales.csv'), 'utf8'), source)
})

test('A1 CSV registry rejects path, type, binary, size and malformed/statistical inputs', async t => {
  const { ctx, dir, workspace, call } = await fixture(t)
  csvTools(ctx)
  const outside = join(dir, 'outside.csv')
  writeFileSync(outside, 'units\n99\n')
  symlinkSync(outside, join(workspace, 'escape.csv'))
  writeFileSync(join(workspace, 'wrong.txt'), source)
  writeFileSync(join(workspace, 'binary.csv'), Buffer.from([0xff, 0, 0xfe]))
  writeFileSync(join(workspace, 'large.csv'), Buffer.alloc(1024 * 1024 + 1, 97))
  writeFileSync(join(workspace, 'invalid.csv'), 'units\nnot-number\n')
  writeFileSync(join(workspace, 'uneven.csv'), 'units,revenue\n1\n')
  writeFileSync(join(workspace, 'overflow.csv'), 'units\n1e308\n1e308\n')
  const bad = [
    { path: outside, numericColumns: ['units'] },
    { path: '../outside.csv', numericColumns: ['units'] },
    { path: 'escape.csv', numericColumns: ['units'] },
    ...['wrong.txt', 'binary.csv', 'large.csv', 'invalid.csv', 'uneven.csv', 'overflow.csv'].map(path => ({ path, numericColumns: ['units'] })),
    { path: 'sales.csv', numericColumns: [] },
    { path: 'sales.csv', numericColumns: ['missing'] },
    { path: 'sales.csv', numericColumns: ['units', 'units'] },
    { path: 'sales.csv', numericColumns: [1] },
  ]
  for (const args of bad) assert.equal((await call(args)).isError, true, JSON.stringify(args))
  const overflow = await call({ path: 'overflow.csv', numericColumns: ['units'] })
  assert.equal(overflow.isError, true)
  if (overflow.isError) assert.equal(overflow.error.info?.code, 'NUMERIC_OVERFLOW')
  assert.equal(readFileSync(outside, 'utf8'), 'units\n99\n')
})

test('A1 CSV cancels before execution and rejects unconfigured roots', async t => {
  const { ctx, call } = await fixture(t)
  csvTools(ctx)
  const cancelled = new AbortController()
  cancelled.abort('explicit stop')
  assert.equal((await call({ path: 'sales.csv', numericColumns: ['units'] }, cancelled.signal)).isError, true)
  delete process.env.CUAGENT_A1_WORKSPACE_ROOT
  assert.throws(() => csvTools(ctx), /absolute CUAGENT_A1_WORKSPACE_ROOT/)
})

test('adding the A1 CSV registration cannot bypass the unchanged A0 whitelist', async t => {
  const { ctx, dir, workspace, call } = await fixture(t)
  process.env.CUAGENT_A0_WORKSPACE_ROOT = workspace
  process.env.CUAGENT_A0_RUN_ID = 'a1-csv-under-a0'
  process.env.CUAGENT_A0_AUDIT_PATH = join(dir, 'audit.jsonl')
  a0Policy(ctx)
  csvTools(ctx)
  assert.equal((await call({ path: 'sales.csv', numericColumns: ['units'] })).isError, true)
  const entries = readFileSync(join(dir, 'audit.jsonl'), 'utf8').trim().split('\n').map(JSON.parse)
  assert.equal(entries.filter(entry => entry.event === 'dispatch').length, 0)
  assert.ok(entries.some(entry => entry.event === 'denied' && entry.name === 'workspace_csv_stats'))
})
