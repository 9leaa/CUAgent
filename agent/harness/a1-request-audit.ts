/** Request-side allowlist complements final execution admission. No prompts logged. */
import type { Context } from '@deepseek-ai/cordis'
import type {} from './a1-policy-plugin.ts'
export const name = 'cuagent-a1-request-audit'
export const inject = ['llm']
export function apply(ctx: Context): void {
  ctx.on('llm/stream', async function* (options, next) {
    const policy = ctx.get('cuagentA1Policy')
    if (!policy) throw new Error('A1 policy unavailable; refusing model request')
    policy.request(options)
    yield* next()
  })
}
