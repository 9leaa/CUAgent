/** Limit inherited application tools to the reviewed A0 capabilities. */
import type { Context } from '@deepseek-ai/cordis'
export const name = 'cuagent-desktop-tool-scope'
export const inject = ['tools']
export function apply(ctx: Context): void {
  ctx.on('agent/created', ({ agent }) => {
    agent.ctx.tools.restrict({ deny: ['load_workspace_dependencies'] })
  }, { global: true })
}
