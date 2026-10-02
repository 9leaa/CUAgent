/** A1 CSV adapter. No shell, arbitrary roots, model loop or verifier capability. */
import { realpathSync, statSync } from 'node:fs'
import { isAbsolute } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import { defineTool, type ToolExecution } from '@deepseek-ai/dsh-tools'
import { calculateWorkspaceCsvStats } from '../workspace-csv-stats.mjs'
import { withWorkspaceErrors } from './workspace-errors.ts'

export const name = 'cuagent-a1-csv-tools'
export const inject = ['tools']

export function apply(ctx: Context): void {
  const configuredRoot = process.env.CUAGENT_A1_WORKSPACE_ROOT
  if (!configuredRoot || !isAbsolute(configuredRoot)) {
    throw new Error('A1 CSV requires an absolute CUAGENT_A1_WORKSPACE_ROOT')
  }
  const workspaceRoot = realpathSync(configuredRoot)
  if (!statSync(workspaceRoot).isDirectory()) throw new Error('A1 CSV workspace is not a directory')
  registerCsvTools(ctx, () => workspaceRoot)
}

export function registerCsvTools(ctx: Context, rootFor: (exec: ToolExecution) => string): void {
  ctx.tools.register(defineTool({
    name: 'workspace_csv_stats',
    description: 'Read one CSV inside the explicitly approved A1 test workspace and calculate row/column counts and selected numeric statistics. No shell or arbitrary paths. Missing cells are excluded from numeric count/mean and recorded separately.',
    parameters: {
      path: { type: 'string', required: true, description: 'Relative .csv path inside this task.' },
      numericColumns: { type: 'array', required: true, items: { type: 'string' },
        description: 'One to twenty distinct numeric column names in the CSV header.' },
    },
    output: {
      schema: { type: 'object', additionalProperties: false,
        properties: { result: { type: 'string', required: true } } },
      render: (_args, value) => [{ type: 'text', text: value.result }],
    },
    async execute(args, exec) {
      exec.signal.throwIfAborted()
      const value = await withWorkspaceErrors(() => calculateWorkspaceCsvStats({ workspaceRoot: rootFor(exec),
        path: args.path, numericColumns: args.numericColumns }))
      exec.signal.throwIfAborted()
      return { result: JSON.stringify(value) }
    },
  }))
}
