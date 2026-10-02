/** All A1 tool bodies require live admission, even if the root policy is unloaded. */
import type { Context } from '@deepseek-ai/cordis'
import type { ToolExecution } from '@deepseek-ai/dsh-tools'
import { registerFileTools } from './a0-file-tools.ts'
import { registerCsvTools } from './a1-csv-tools.ts'
import { registerCalculate } from './calculate.ts'
import { registerImageProbe } from './image-probe.ts'
import { registerDailyReport } from './daily-report-tools.ts'
import type {} from './a1-policy-plugin.ts'

export const name = 'cuagent-a1-tools'
export const inject = ['tools', 'attachments']

export function apply(ctx: Context, config: { readOnly?: boolean, dailyReport?: boolean } = {}): void {
  if (typeof config !== 'object' || config === null || Object.keys(config).some(key => !['readOnly', 'dailyReport'].includes(key))
    || (config.readOnly !== undefined && typeof config.readOnly !== 'boolean')
    || (config.dailyReport !== undefined && typeof config.dailyReport !== 'boolean')
    || (config.readOnly && config.dailyReport)) throw new Error('invalid reviewed A1 tools config')
  const requireAdmission = (exec: ToolExecution) => {
    const policy = ctx.get('cuagentA1Policy')
    if (!policy) throw new Error('A1 policy unavailable; no dispatch')
    return policy.requireAdmission(exec)
  }
  registerFileTools(ctx, requireAdmission, config.readOnly !== true)
  registerCsvTools(ctx, requireAdmission)
  if (config.dailyReport) { registerDailyReport(ctx, requireAdmission); return }
  registerCalculate(ctx, requireAdmission)
  if (config.readOnly !== true) registerImageProbe(ctx, requireAdmission)
}
