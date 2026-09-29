/** No model, credentials, Web process, or project workspace is used here. */
import assert from 'node:assert/strict'
import { mkdirSync, mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'
import { Context } from '@deepseek-ai/cordis'
import { ToolCallId } from '@deepseek-ai/dsh-llm'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import ToolRuntime from '@deepseek-ai/dsh-tools'
import type { Agent } from '@deepseek-ai/dsh-agent'
import type { SessionId } from '@deepseek-ai/dsh-session'
import { apply as applyPolicy } from './a0-policy-plugin.ts'

test('DSH rejects forbidden tools, caps dispatches at 30, and honours stop', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'cuagent-a0-dsh-'))
  t.after(() => rmSync(dir, { recursive: true, force: true }))
  const oldRun = process.env.CUAGENT_A0_RUN_ID
  const oldAudit = process.env.CUAGENT_A0_AUDIT_PATH
  const oldWorkspace = process.env.CUAGENT_A0_WORKSPACE_ROOT
  mkdirSync(join(dir, 'workspace'))
  process.env.CUAGENT_A0_RUN_ID = 'integration-run'
  process.env.CUAGENT_A0_AUDIT_PATH = join(dir, 'audit.jsonl')
  process.env.CUAGENT_A0_WORKSPACE_ROOT = join(dir, 'workspace')
  t.after(() => {
    if (oldRun === undefined) delete process.env.CUAGENT_A0_RUN_ID
    else process.env.CUAGENT_A0_RUN_ID = oldRun
    if (oldAudit === undefined) delete process.env.CUAGENT_A0_AUDIT_PATH
    else process.env.CUAGENT_A0_AUDIT_PATH = oldAudit
    if (oldWorkspace === undefined) delete process.env.CUAGENT_A0_WORKSPACE_ROOT
    else process.env.CUAGENT_A0_WORKSPACE_ROOT = oldWorkspace
  })

  const ctx = new Context()
  await ctx.plugin(SystemPrompt, {})
  await ctx.plugin(ToolRuntime)
  applyPolicy(ctx)
  let allowedBodies = 0
  let forbiddenBodies = 0
  const tool = (name: string, execute: () => Promise<string>) => ({
    name, description: name,
    parameters: { type: 'object' as const, properties: {} },
    output: { schema: { type: 'string' as const }, render: (_args: unknown, value: unknown) => [{ type: 'text' as const, text: String(value) }] },
    execute,
  })
  ctx.tools.register(tool('calculate', async () => { allowedBodies++; return 'ok' }))
  ctx.tools.register(tool('bash', async () => { forbiddenBodies++; return 'bad' }))
  const agent = { id: 'session-one' as SessionId, session: { id: 'session-one' as SessionId } } as Agent
  const call = (name: string, n: number, signal = new AbortController().signal) =>
    ctx.tools.execute({ callId: ToolCallId(`c${n}`), name, arguments: {}, agent, signal })

  assert.equal((await call('bash', 0)).isError, true)
  assert.equal(forbiddenBodies, 0)
  const stopped = new AbortController()
  stopped.abort('stop')
  assert.equal((await call('calculate', 33, stopped.signal)).isError, true)
  assert.equal(allowedBodies, 0)
  const outcomes = await Promise.all(Array.from({ length: 31 }, (_, i) => call('calculate', i + 1)))
  assert.equal(outcomes.filter(result => !result.isError).length, 30)
  assert.equal(outcomes.filter(result => result.isError).length, 1)
  assert.equal(allowedBodies, 30)
  const resumedAgent = { id: 'session-two' as SessionId, session: { id: 'session-two' as SessionId } } as Agent
  const resumed = await ctx.tools.execute({ callId: ToolCallId('continued-task'), name: 'calculate',
    arguments: {}, agent: resumedAgent, signal: new AbortController().signal })
  assert.equal(resumed.isError, true)
  assert.equal(allowedBodies, 30)
  const audit = readFileSync(process.env.CUAGENT_A0_AUDIT_PATH!, 'utf8').trim().split('\n').map(line => JSON.parse(line))
  assert.equal(audit.filter(entry => entry.event === 'dispatch').length, 30)
  assert.equal(audit.some(entry => entry.name === 'bash' && entry.event === 'dispatch'), false)
})

test('missing policy settings deny every tool instead of failing plugin activation', async t => {
  const oldRun = process.env.CUAGENT_A0_RUN_ID
  const oldAudit = process.env.CUAGENT_A0_AUDIT_PATH
  const oldWorkspace = process.env.CUAGENT_A0_WORKSPACE_ROOT
  delete process.env.CUAGENT_A0_RUN_ID
  delete process.env.CUAGENT_A0_AUDIT_PATH
  delete process.env.CUAGENT_A0_WORKSPACE_ROOT
  t.after(() => {
    if (oldRun === undefined) delete process.env.CUAGENT_A0_RUN_ID
    else process.env.CUAGENT_A0_RUN_ID = oldRun
    if (oldAudit === undefined) delete process.env.CUAGENT_A0_AUDIT_PATH
    else process.env.CUAGENT_A0_AUDIT_PATH = oldAudit
    if (oldWorkspace === undefined) delete process.env.CUAGENT_A0_WORKSPACE_ROOT
    else process.env.CUAGENT_A0_WORKSPACE_ROOT = oldWorkspace
  })
  const ctx = new Context()
  await ctx.plugin(SystemPrompt, {})
  await ctx.plugin(ToolRuntime)
  applyPolicy(ctx)
  let bodies = 0
  ctx.tools.register({
    name: 'calculate', description: 'test', parameters: { type: 'object', properties: {} },
    output: { schema: { type: 'string' }, render: (_args, value) => [{ type: 'text', text: String(value) }] },
    execute: async () => { bodies++; return 'bad' },
  })
  const agent = { id: 'failclosed' as SessionId, session: { id: 'failclosed' as SessionId } } as Agent
  const result = await ctx.tools.execute({ callId: ToolCallId('missing-config'), name: 'calculate',
    arguments: {}, agent, signal: new AbortController().signal })
  assert.equal(result.isError, true)
  assert.equal(bodies, 0)
})
