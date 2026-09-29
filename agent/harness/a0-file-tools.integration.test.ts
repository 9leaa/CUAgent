/** Exercises the actual DSH tool registry without an LLM or a Web process. */
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { basename, join } from 'node:path'
import { test } from 'node:test'
import { Context } from '@deepseek-ai/cordis'
import { ToolCallId } from '@deepseek-ai/dsh-llm'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import ToolRuntime from '@deepseek-ai/dsh-tools'
import type { Agent } from '@deepseek-ai/dsh-agent'
import type { SessionId } from '@deepseek-ai/dsh-session'
import { apply as applyFiles } from './a0-file-tools.ts'
import { apply as applyPolicy } from './a0-policy-plugin.ts'

test('DSH writes, reads, and independently checks result.txt in a temporary test directory', async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'cuagent-a0-workspace-'))
  const testDir = mkdtempSync(join(workspace, 'a0-file-test-'))
  const auditDir = mkdtempSync(join(tmpdir(), 'cuagent-a0-file-audit-'))
  t.after(() => {
    rmSync(testDir, { recursive: true, force: true })
    rmSync(workspace, { recursive: true, force: true })
    rmSync(auditDir, { recursive: true, force: true })
  })
  const oldRun = process.env.CUAGENT_A0_RUN_ID
  const oldAudit = process.env.CUAGENT_A0_AUDIT_PATH
  const oldWorkspace = process.env.CUAGENT_A0_WORKSPACE_ROOT
  process.env.CUAGENT_A0_RUN_ID = `file-test-${randomUUID()}`
  process.env.CUAGENT_A0_AUDIT_PATH = join(auditDir, 'audit.jsonl')
  process.env.CUAGENT_A0_WORKSPACE_ROOT = workspace
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
  applyFiles(ctx)
  const agent = { id: 'file-test' as SessionId, session: { id: 'file-test' as SessionId } } as Agent
  const path = `${basename(testDir)}/result.txt`
  const expected = `a0-file-test-${randomUUID()}`
  const signal = new AbortController().signal
  const write = await ctx.tools.execute({ callId: ToolCallId('write-1'), name: 'workspace_write',
    arguments: { path, content: expected }, agent, signal })
  assert.equal(write.isError, false, JSON.stringify(write.content))
  const read = await ctx.tools.execute({ callId: ToolCallId('read-1'), name: 'workspace_read',
    arguments: { path }, agent, signal })
  assert.equal(read.isError, false, JSON.stringify(read.content))
  if (read.isError) throw new Error('unreachable: read failed')
  assert.equal((read.value as { content: string }).content, expected)
  assert.equal(readFileSync(join(testDir, 'result.txt'), 'utf8'), expected)
  const absoluteRead = await ctx.tools.execute({ callId: ToolCallId('absolute-read'), name: 'workspace_read',
    arguments: { path: join(testDir, 'result.txt') }, agent, signal })
  assert.equal(absoluteRead.isError, true)
  const parentWrite = await ctx.tools.execute({ callId: ToolCallId('parent-write'), name: 'workspace_write',
    arguments: { path: '../escape.txt', content: 'bad' }, agent, signal })
  assert.equal(parentWrite.isError, true)
  const overwrite = await ctx.tools.execute({ callId: ToolCallId('overwrite'), name: 'workspace_write',
    arguments: { path, content: 'bad' }, agent, signal })
  assert.equal(overwrite.isError, true)
  assert.equal(readFileSync(join(testDir, 'result.txt'), 'utf8'), expected)
  const outside = join(auditDir, 'outside.txt')
  writeFileSync(outside, 'outside')
  symlinkSync(outside, join(testDir, 'escape.txt'))
  const symlinkRead = await ctx.tools.execute({ callId: ToolCallId('symlink-read'), name: 'workspace_read',
    arguments: { path: `${basename(testDir)}/escape.txt` }, agent, signal })
  assert.equal(symlinkRead.isError, true)
  assert.equal(readFileSync(outside, 'utf8'), 'outside')
  const audit = readFileSync(process.env.CUAGENT_A0_AUDIT_PATH!, 'utf8').trim().split('\n').map(line => JSON.parse(line))
  assert.deepEqual(audit.filter(entry => entry.event === 'dispatch').map(entry => entry.name),
    ['workspace_write', 'workspace_read', 'workspace_read', 'workspace_write', 'workspace_write', 'workspace_read'])
  assert.equal(audit.filter(entry => entry.event === 'result').length, 6)
})
