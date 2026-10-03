/** Root-mounted A1 policy service. Approval is private task config, not prompt text. */
import { createHash, randomUUID } from 'node:crypto'
import { lstatSync, readFileSync } from 'node:fs'
import { Service, type Context } from '@deepseek-ai/cordis'
import type { ToolExecution, ToolExecutionResult } from '@deepseek-ai/dsh-tools'
import { A1Policy } from '../a1-policy.mjs'
import { loadA1TaskConfig } from '../a1-task-config.mjs'
import { readWorkspaceFile } from '../workspace-read.mjs'
import { calculateWorkspaceCsvStats } from '../workspace-csv-stats.mjs'
import { collectReportInputs } from '../report-inputs.mjs'

export const name = 'cuagent-a1-policy'
export const inject = ['tools']
export const callOf = (exec: Readonly<ToolExecution>) => ({ sessionId: exec.agent?.session.id,
  callId: String(exec.callId), name: exec.name, aborted: exec.signal.aborted, arguments: exec.arguments })
const digest = (text: string) => createHash('sha256').update(text).digest('hex')

declare module '@deepseek-ai/cordis' { interface Context { cuagentA1Policy: A1PolicyService } }

export class A1PolicyService extends Service {
  readonly instanceId = randomUUID()
  private policies = new Map<string, A1Policy>()
  private configPath?: string
  private configDigest?: string
  constructor(ctx: Context) {
    super(ctx, 'cuagentA1Policy')
    try {
      const approved = loadA1TaskConfig(process.env.CUAGENT_A1_TASKS_PATH)
      this.policies = approved.policies
      this.configPath = approved.path; this.configDigest = approved.digest
    } catch {
      this.policies.clear()
      ctx.logger.error('CUAgent A1 task policy unavailable; all calls denied')
    }
  }
  private policyFor(sessionId: string | undefined): A1Policy | undefined {
    try {
      if (!this.configPath || (lstatSync(this.configPath).mode & 0o077) !== 0 || digest(readFileSync(this.configPath, 'utf8')) !== this.configDigest) return undefined
      return this.policies.get(sessionId ?? '')
    } catch { return undefined }
  }
  private policy(exec: Readonly<ToolExecution>): A1Policy | undefined { return this.policyFor(exec.agent?.session.id) }
  request(options: { sessionId?: string, tools?: { name: string }[], provider?: string, model?: string, messages: { content: unknown }[] }): void {
    const policy = this.policyFor(options.sessionId)
    if (!policy) throw new Error('A1 model request has no approved task')
    const imageBlocks = options.messages.reduce((count, message) => count + (Array.isArray(message.content)
      ? message.content.filter(block => block.type === 'image').length : 0), 0)
    policy.request({ toolNames: (options.tools ?? []).map(tool => tool.name), provider: options.provider, model: options.model, imageBlocks })
  }
  guard(exec: Readonly<ToolExecution>): string | undefined {
    const policy = this.policy(exec)
    if (!policy) return 'A1: policy or task unavailable'
    const reason = policy.guard(callOf(exec))
    // Log known-task denials without reserving a budget slot.
    return reason ? policy.dispatch(callOf(exec)) : undefined
  }
  dispatch(exec: Readonly<ToolExecution>): string | undefined {
    const policy = this.policy(exec)
    return policy ? policy.dispatch(callOf(exec)) : 'A1: policy or task unavailable'
  }
  requireAdmission(exec: ToolExecution): string {
    const policy = this.policy(exec)
    if (!policy) throw new Error('A1 policy or task unavailable')
    policy.assertAdmitted(callOf(exec))
    return policy.workspaceFor(exec.agent?.session.id)
  }
  async dailyReportSource(exec: ToolExecution): Promise<string> {
    // One separately counted, fixed-path internal read. Outer admission covers
    // the eventual write, including failure; this cannot be used as free I/O.
    if (exec.name !== 'workspace_daily_report') throw new Error('wrong internal read owner')
    const root = this.requireAdmission(exec)
    const policy = this.policy(exec)!
    const call = { ...callOf(exec), callId: String(exec.callId) + ':daily-source',
      name: 'workspace_read', arguments: { path: 'report.json' } }
    const refusal = policy.dispatch(call)
    if (refusal) throw new Error(refusal)
    let value
    try {
      exec.signal.throwIfAborted()
      value = await readWorkspaceFile({ workspaceRoot: root, path: 'report.json' })
      exec.signal.throwIfAborted()
      if (value.truncated) throw new Error('report source must be fully read')
    } catch (error) {
      policy.result(call, { errorCode: 'DAILY_SOURCE_FAILED' })
      throw error
    }
    policy.result(call, { artifact: value })
    return value.content
  }
  async reportInputs(exec: ToolExecution): Promise<unknown> {
    if (exec.name !== 'workspace_report_inputs') throw new Error('wrong aggregate owner')
    return collectReportInputs({ signal: exec.signal, invoke: async (name: string, args: any, sequence: number) => {
      if (this.ctx.get('cuagentA1Policy')?.instanceId !== this.instanceId) throw new Error('A1 policy unavailable')
      const root = this.requireAdmission(exec)
      const policy = this.policy(exec)!
      const call = { ...callOf(exec), callId: String(exec.callId) + ':input-' + sequence,
        name, arguments: args }
      const refusal = policy.dispatch(call)
      if (refusal) throw new Error(refusal)
      let value
      try {
        exec.signal.throwIfAborted()
        value = name === 'workspace_read'
          ? await readWorkspaceFile({ workspaceRoot: root, ...args })
          : await calculateWorkspaceCsvStats({ workspaceRoot: root, ...args })
        exec.signal.throwIfAborted()
        this.requireAdmission(exec)
      } catch (error) {
        policy.result(call, { errorCode: 'REPORT_INPUT_FAILED' })
        throw error
      }
      policy.result(call, { artifact: value })
      return value
    } })
  }
  result(exec: Readonly<ToolExecution>, result: ToolExecutionResult): void {
    // Only called for dispatches admitted by this wrapper; denials are not results.
    const policy = this.policies.get(exec.agent?.session.id ?? '')
    if (!policy) throw new Error('A1 result task unavailable')
    let artifact: unknown = result.isError ? undefined : result.value
    if (artifact && typeof artifact === 'object' && 'result' in artifact && typeof artifact.result === 'string') {
      try { artifact = JSON.parse(artifact.result) } catch { artifact = undefined }
    }
    policy.result(callOf(exec), { errorCode: result.isError ? result.error.info?.code ?? 'TOOL_ERROR' : undefined, artifact })
  }
}

function denied(reason: string): ToolExecutionResult {
  return { isError: true, content: [{ type: 'text', text: reason }],
    error: { message: reason, info: { name: 'A1PolicyError', code: 'A1_POLICY_DENIED' } } }
}

export function apply(ctx: Context): void {
  new A1PolicyService(ctx)
  ctx.tools.guard(exec => {
    const active = ctx.get('cuagentA1Policy')
    return active ? active.guard(exec) : 'A1: policy unavailable'
  })
  ctx.on('tools/execute', async (exec, next) => {
    const service = ctx.get('cuagentA1Policy')
    const reason = service ? service.dispatch(exec) : 'A1: policy unavailable'
    if (reason) return denied(reason)
    const result = await next()
    service!.result(exec, result)
    return result
  })
}
