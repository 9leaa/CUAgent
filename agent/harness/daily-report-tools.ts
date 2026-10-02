import type { Context } from '@deepseek-ai/cordis'
import { defineTool, type ToolExecution } from '@deepseek-ai/dsh-tools'
import { renderDailyReport } from '../daily-report-render.mjs'
import { writeWorkspaceFile } from '../workspace-write.mjs'
import { withWorkspaceErrors } from './workspace-errors.ts'
import type {} from './a1-policy-plugin.ts'

export function registerDailyReport(ctx: Context, rootFor: (exec: ToolExecution) => string): void {
  ctx.tools.register(defineTool({
    name: 'workspace_daily_report',
    description: 'Read existing report.json and create report.md with deterministic formatting. Costs two actual requests (read + write). Never overwrites. Read both artifacts back afterwards.',
    parameters: {},
    output: {
      schema: { type: 'object', additionalProperties: false, properties: {
        path: { type: 'string', required: true }, status: { type: 'string', required: true },
        bytes: { type: 'integer', required: true }, sha256: { type: 'string', required: true },
      } },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(_args, exec) {
      const workspaceRoot = rootFor(exec)
      const service = ctx.get('cuagentA1Policy')
      if (!service) throw new Error('A1 policy unavailable')
      const source = await service.dailyReportSource(exec)
      exec.signal.throwIfAborted()
      const content = renderDailyReport(JSON.parse(source))
      rootFor(exec)
      const value = await withWorkspaceErrors(() => writeWorkspaceFile({ workspaceRoot, path: 'report.md', content }))
      exec.signal.throwIfAborted()
      return value
    },
  }))
}
