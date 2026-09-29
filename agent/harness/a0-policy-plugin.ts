/** Mount at the dedicated A0 instance root, not inside one selectable preset. */
import { isAbsolute, relative, sep } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import type { ToolExecution, ToolExecutionResult } from '@deepseek-ai/dsh-tools'
import { A0Policy, type A0Call } from './a0-policy.ts'

export const name = 'cuagent-a0-policy'
export const inject = ['tools']

const ALLOWED = ['calculate', 'workspace_image_probe', 'workspace_list', 'workspace_read', 'workspace_write'] as const

function callOf(exec: Readonly<ToolExecution>): A0Call {
  return {
    sessionId: exec.agent?.session.id,
    callId: String(exec.callId),
    name: exec.name,
    aborted: exec.signal.aborted,
  }
}

function denied(reason: string): ToolExecutionResult {
  return {
    content: [{ type: 'text', text: `Error: ${reason}` }],
    isError: true,
    error: { message: reason, info: { name: 'A0PolicyError', code: 'A0_POLICY_DENIED' } },
  }
}

export function apply(ctx: Context): void {
  let policy: A0Policy | undefined
  try {
    const runId = process.env.CUAGENT_A0_RUN_ID
    const auditPath = process.env.CUAGENT_A0_AUDIT_PATH
    const workspaceRoot = process.env.CUAGENT_A0_WORKSPACE_ROOT
    if (!runId || !auditPath || !isAbsolute(auditPath) || !workspaceRoot || !isAbsolute(workspaceRoot)) {
      throw new Error('run id, absolute audit path, and absolute workspace root are required')
    }
    const auditRelativeToWorkspace = relative(workspaceRoot, auditPath)
    if (auditRelativeToWorkspace === '' || (!auditRelativeToWorkspace.startsWith(`..${sep}`)
      && auditRelativeToWorkspace !== '..' && !isAbsolute(auditRelativeToWorkspace))) {
      throw new Error('audit must be outside the model workspace')
    }
    policy = new A0Policy(auditPath, runId, ALLOWED)
  } catch (error) {
    ctx.logger.error(`CUAgent A0 policy unavailable; all tool calls denied: ${error instanceof Error ? error.message : String(error)}`)
  }
  const active = policy
  ctx.tools.guard(exec => active === undefined ? 'A0: policy unavailable' : active.guard(callOf(exec)))
  ctx.on('tools/execute', async (exec, next): Promise<ToolExecutionResult> => {
    const reason = active === undefined ? 'A0: policy unavailable' : active.dispatch(callOf(exec))
    return reason === undefined ? next() : denied(reason)
  })
  ctx.on('tools/result', (exec, result): undefined => {
    active?.result(callOf(exec), result.isError ? result.error.info?.code ?? 'TOOL_ERROR' : undefined)
    return undefined
  })
}
