/** Minimal A0 file tools; the model cannot choose the workspace root. */
import { realpathSync, statSync } from 'node:fs'
import { isAbsolute } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'
import { listWorkspaceDirectory } from '../workspace-list.mjs'
import { readWorkspaceFile } from '../workspace-read.mjs'
import { writeWorkspaceFile } from '../workspace-write.mjs'

export const name = 'cuagent-a0-file-tools'
export const inject = ['tools']

export function apply(ctx: Context): void {
  const configuredRoot = process.env.CUAGENT_A0_WORKSPACE_ROOT
  if (!configuredRoot || !isAbsolute(configuredRoot)) {
    throw new Error('A0 file tools require an absolute CUAGENT_A0_WORKSPACE_ROOT')
  }
  const workspaceRoot = realpathSync(configuredRoot)
  if (!statSync(workspaceRoot).isDirectory()) throw new Error('A0 workspace root is not a directory')

  ctx.tools.register(defineTool({
    name: 'workspace_list',
    description: 'List at most 200 entries inside the dedicated A0 test workspace. No host paths.',
    parameters: { path: { type: 'string', description: 'Relative directory; omit for workspace root.' } },
    output: {
      schema: {
        type: 'object', additionalProperties: false,
        properties: {
          path: { type: 'string', required: true },
          entries: { type: 'array', required: true, items: {
            type: 'object', additionalProperties: false,
            properties: { name: { type: 'string', required: true }, type: { type: 'string', required: true } },
          } },
          totalEntries: { type: 'integer', required: true },
          truncated: { type: 'boolean', required: true },
        },
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(args, exec) {
      exec.signal.throwIfAborted()
      const value = await listWorkspaceDirectory({ workspaceRoot, path: args.path ?? '.' })
      exec.signal.throwIfAborted()
      return value
    },
  }))

  ctx.tools.register(defineTool({
    name: 'workspace_read',
    description: 'Read a UTF-8 text file inside the dedicated A0 test workspace.',
    parameters: { path: { type: 'string', required: true, description: 'Relative .txt/.md/.json/.csv path.' } },
    output: {
      schema: {
        type: 'object', additionalProperties: false,
        properties: {
          path: { type: 'string', required: true },
          content: { type: 'string', required: true },
          startLine: { type: 'integer', required: true },
          endLine: { type: 'integer', required: true },
          totalLines: { type: 'integer', required: true },
          truncated: { type: 'boolean', required: true },
          bytes: { type: 'integer', required: true },
          sha256: { type: 'string', required: true },
        },
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(args, exec) {
      exec.signal.throwIfAborted()
      const value = await readWorkspaceFile({ workspaceRoot, path: args.path })
      exec.signal.throwIfAborted()
      return value
    },
  }))

  ctx.tools.register(defineTool({
    name: 'workspace_write',
    description: 'Create a new UTF-8 text file inside the dedicated A0 test workspace; never overwrite.',
    parameters: {
      path: { type: 'string', required: true, description: 'Relative .txt/.md/.json path.' },
      content: { type: 'string', required: true, description: 'UTF-8 text, at most 256 KiB.' },
    },
    output: {
      schema: {
        type: 'object', additionalProperties: false,
        properties: {
          path: { type: 'string', required: true },
          status: { type: 'string', required: true },
          bytes: { type: 'integer', required: true },
          sha256: { type: 'string', required: true },
        },
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(args, exec) {
      exec.signal.throwIfAborted()
      const value = await writeWorkspaceFile({ workspaceRoot, path: args.path, content: args.content })
      exec.signal.throwIfAborted()
      return value
    },
  }))
}
