/** Record request metadata only; prompts and credentials never enter this log. */
import { appendFileSync } from 'node:fs'
import { join } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'

export const name = 'cuagent-desktop-request-audit'
export const inject = ['llm']

export function apply(ctx: Context): void {
  const ledger = process.env.CUAGENT_A0_AUDIT_PATH
  if (!ledger) throw new Error('request audit requires CUAGENT_A0_AUDIT_PATH')
  const path = join(ledger, '..', 'request-audit.jsonl')
  ctx.on('llm/stream', async function* (options, next) {
    const toolNames = (options.tools ?? []).map(tool => tool.name).sort()
    const allowed = new Set(['calculate', 'workspace_image_probe', 'workspace_list', 'workspace_read', 'workspace_write'])
    if (toolNames.some(name => !allowed.has(name))) {
      appendFileSync(path, JSON.stringify({ at: new Date().toISOString(),
        runId: process.env.CUAGENT_A0_RUN_ID, toolNames, rejected: true }) + '\n', { mode: 0o600 })
      throw new Error('Desktop A0 request contains an unreviewed tool; refusing model dispatch')
    }
    const imageBlocks = options.messages.reduce((count, message) => count
      + (Array.isArray(message.content) ? message.content.filter(block => block.type === 'image').length : 0), 0)
    appendFileSync(path, JSON.stringify({ at: new Date().toISOString(),
      runId: process.env.CUAGENT_A0_RUN_ID, provider: options.provider,
      model: options.model, toolNames, imageBlocks }) + '\n', { mode: 0o600 })
    yield* next()
  })
}
