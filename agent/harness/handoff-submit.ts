/** One original VM submission. No retries or model loop; official terminal result only. */
import type { Context } from '@deepseek-ai/cordis'
import type { ToolExecution, ToolRunContext } from '@deepseek-ai/dsh-tools'
import reportSchema from './handoff-result.schema.json' with { type: 'json' }

export function registerHandoffSubmit(ctx: Context, binding: {
  runId: string; sessionId: string; inputSha256: string
}, request: (args: unknown, signal: AbortSignal) => Promise<any>, stop: () => Promise<void>) {
  let state: 'open' | 'pending' | 'committed' | 'failed' = 'open'
  const staged = new WeakMap<ToolExecution, string>()
  const fail = () => {
    state = 'failed'
    void stop().catch(() => ctx.logger.error('P7 submission unconfirmed; local dispatch remains denied'))
  }
  const { $defs, ...report } = reportSchema
  ctx.tools.guard(() => state === 'open' ? undefined : 'P7 submission terminal or pending')
  ctx.tools.register({
    name: 'vm_submit_handoff',
    description: 'Submit your complete unchanged validated report after GUI save, reopen, result write and readback. Pass the full report object, not a draft reference or prose. One original raw call. Success ends this turn; failure or unknown delivery cannot be retried. This does not certify semantic or GUI acceptance.',
    parameters: { type: 'object', properties: { report }, required: ['report'], additionalProperties: false, $defs },
    output: { schema: { type: 'object', properties: { result: { type: 'string' } },
      required: ['result'], additionalProperties: false },
      render: (_args: unknown, value: { result: string }) => [{ type: 'text' as const, text: value.result }] },
    isConcurrencySafe: () => false,
    async execute(args: unknown, exec: ToolRunContext) {
      if (state !== 'open' || exec.signal.aborted || exec.parent !== undefined
          || exec.agent?.session.id !== binding.sessionId) throw new Error('P7 submission not authorized')
      state = 'pending' // Before HTTP await: even a second concurrent execution cannot dispatch.
      try {
        const value = await request(args, exec.signal)
        const keys = ['status', 'protocol', 'runId', 'sessionId', 'inputSha256', 'reportSha256',
          'documentSha256', 'used', 'semanticVerified', 'guiVerified'].sort()
        if (exec.signal.aborted || value === null || typeof value !== 'object'
            || JSON.stringify(Object.keys(value).sort()) !== JSON.stringify(keys)
            || value.status !== 'HANDOFF_SUBMITTED' || value.protocol !== 'p7-tool-submit-v1'
            || value.runId !== binding.runId || value.sessionId !== binding.sessionId
            || value.inputSha256 !== binding.inputSha256 || value.semanticVerified !== false || value.guiVerified !== false
            || !Number.isInteger(value.used) || value.used < 1 || value.used > 30
            || !['reportSha256', 'documentSha256'].every(k => typeof value[k] === 'string' && /^[0-9a-f]{64}$/.test(value[k]))) {
          throw new Error('P7 submission response unconfirmed')
        }
        const result = JSON.stringify(value)
        staged.set(exec, result)
        exec.concludeTurn() // Official registry applies this only to its final successful result.
        return { result }
      } catch (error) { fail(); throw error }
    },
  })
  ctx.on('tools/result', (exec, result) => {
    const original = staged.get(exec)
    if (original === undefined) return
    staged.delete(exec)
    if (state !== 'pending' || result.isError || exec.signal.aborted
        || JSON.stringify(result.content) !== JSON.stringify([{ type: 'text', text: original }])
        || JSON.stringify(result.value) !== JSON.stringify({ result: original })) { fail(); return }
    state = 'committed'
  })
  return { blocked: () => state !== 'open', state: () => state }
}
