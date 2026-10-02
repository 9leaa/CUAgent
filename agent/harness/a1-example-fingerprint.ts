/** Opt-in example only. Registration alone is not approval. Never enabled by default. */
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'
import type {} from './a1-policy-plugin.ts'
import { fingerprintWorkspaceText } from '../workspace-text-fingerprint.mjs'
import { withWorkspaceErrors } from './workspace-errors.ts'
import { HarnessError } from '@deepseek-ai/dsh-llm'
export const name = 'cuagent-a1-example-fingerprint'
export const inject = ['tools']
export function apply(ctx: Context): void {
  const definition = defineTool({
    name: 'workspace_text_fingerprint',
    description: 'Return path, exact byte length and SHA-256 of one approved UTF-8 text file. No file content, shell, network, or arbitrary host paths.',
    parameters: { path: { type: 'string', required: true, description: 'Relative .txt/.md/.csv/.json path inside this approved session.' } },
    output: { schema: { type: 'object', additionalProperties: false, properties: {
      path: { type: 'string', required: true }, bytes: { type: 'integer', required: true }, sha256: { type: 'string', required: true },
    } }, render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }] },
    async execute(args, exec) {
      exec.signal.throwIfAborted()
      if (Object.keys(args).some(key => key !== 'path')) throw new HarnessError('unexpected fingerprint parameter', 'INVALID_ARGS')
      const policy = ctx.get('cuagentA1Policy')
      if (!policy) throw new Error('A1 policy unavailable; no fingerprint execution')
      const workspaceRoot = policy.requireAdmission(exec)
      const value = await withWorkspaceErrors(() => fingerprintWorkspaceText({ workspaceRoot, path: args.path }))
      exec.signal.throwIfAborted()
      return value
    },
  })
  // Official author shorthand has an open root; publish and enforce this closed contract.
  ctx.tools.register({ ...definition, parameters: { ...definition.parameters, additionalProperties: false } })
}
