/** Opt-in P4 tool. Registration alone never supplies approval. */
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'
import { withWorkspaceErrors } from './workspace-errors.ts'
import type {} from './a1-policy-plugin.ts'

export const name = 'cuagent-report-inputs'
export const inject = ['tools']

export function apply(ctx: Context): void {
  ctx.tools.register(defineTool({
    name: 'workspace_report_inputs',
    description: 'Read fixed task.json and its complete notes and CSV statistics. No report generation. Each internal read/stat costs a separate request, plus one for this call. No arbitrary paths or truncation.',
    parameters: {},
    output: { schema: { type: 'object', additionalProperties: false,
      properties: { result: { type: 'string', required: true } } },
      render: (_args, value) => [{ type: 'text', text: value.result }] },
    async execute(_args, exec) {
      exec.signal.throwIfAborted()
      const service = ctx.get('cuagentA1Policy')
      if (!service) throw new Error('A1 policy unavailable')
      const result = await withWorkspaceErrors(() => service.reportInputs(exec))
      exec.signal.throwIfAborted()
      return { result: JSON.stringify(result) }
    },
  }))
}
