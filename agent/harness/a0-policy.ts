/** A0's process-local admission policy. The append-only ledger survives a restart. */
import { closeSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync, writeSync } from 'node:fs'
import { dirname } from 'node:path'

export interface A0Call {
  sessionId: string | undefined
  callId: string
  name: string
  aborted: boolean
}

type AuditEvent = {
  at: string
  event: 'denied' | 'dispatch' | 'result'
  runId: string
  sessionId: string
  callId: string
  name: string
  used?: number
  reason?: string
  errorCode?: string
}

/** One explicit run id owns the budget, even if the task changes sessions. */
export class A0Policy {
  private used = 0
  private auditFailed = false
  private readonly allowed: ReadonlySet<string>

  constructor(
    private readonly ledgerPath: string,
    private readonly runId: string,
    allowedTools: readonly string[],
    private readonly limit = 30,
  ) {
    if (!Number.isSafeInteger(limit) || limit < 1) throw new Error('invalid A0 tool-call limit')
    if (!runId || !/^[A-Za-z0-9_-]{1,80}$/.test(runId)) throw new Error('invalid A0 run id')
    this.allowed = new Set(allowedTools)
    mkdirSync(dirname(ledgerPath), { recursive: true, mode: 0o700 })
    if (!existsSync(ledgerPath)) return
    const ledger = readFileSync(ledgerPath, 'utf8')
    for (const line of ledger.split('\n')) {
      if (line === '') continue
      const entry: unknown = JSON.parse(line)
      if (typeof entry !== 'object' || entry === null || !('event' in entry)
        || !('runId' in entry) || typeof entry.runId !== 'string'
        || !('sessionId' in entry) || typeof entry.sessionId !== 'string'
        || !('callId' in entry) || typeof entry.callId !== 'string'
        || !('name' in entry) || typeof entry.name !== 'string'
        || !['denied', 'dispatch', 'result'].includes(String(entry.event))) {
        throw new Error('invalid A0 audit ledger')
      }
      if (entry.runId === this.runId && entry.event === 'dispatch') {
        if (!('used' in entry) || entry.used !== this.used + 1) {
          throw new Error('invalid A0 audit count sequence')
        }
        this.used++
      }
    }
  }

  count(): number { return this.used }

  /** Guard checks identity and current state; actual dispatch consumes budget. */
  guard(call: A0Call): string | undefined {
    const sessionId = call.sessionId ?? ''
    const base = { sessionId, callId: call.callId, name: call.name }
    const reason = this.auditFailed ? 'A0: audit unavailable'
      : !sessionId ? 'A0: agent session is required'
      : call.aborted ? 'A0: turn is stopped'
      : !this.allowed.has(call.name) ? 'A0: tool is not allowed'
      : this.used >= this.limit ? 'A0: 30-call budget exhausted'
      : undefined
    if (reason !== undefined) {
      try { this.append({ ...base, event: 'denied', reason }) }
      catch { this.auditFailed = true; return 'A0: audit unavailable' }
      return reason
    }
    return undefined
  }

  /** Synchronous write-ahead count: parallel calls cannot both take the last slot. */
  dispatch(call: A0Call): string | undefined {
    const reason = this.guard(call)
    if (reason !== undefined) return reason
    try {
      this.append({ sessionId: call.sessionId!, callId: call.callId, name: call.name, event: 'dispatch', used: this.used + 1 })
    } catch {
      this.auditFailed = true
      return 'A0: audit unavailable'
    }
    this.used++
    return undefined
  }

  result(call: A0Call, errorCode?: string): void {
    try {
      this.append({ sessionId: call.sessionId ?? '', callId: call.callId, name: call.name, event: 'result',
        ...errorCode === undefined ? {} : { errorCode } })
    } catch (error) {
      this.auditFailed = true
      throw error
    }
  }

  private append(entry: Omit<AuditEvent, 'at' | 'runId'>): void {
    const line = Buffer.from(JSON.stringify({ at: new Date().toISOString(), runId: this.runId, ...entry }) + '\n')
    const fd = openSync(this.ledgerPath, 'a', 0o600)
    try {
      let offset = 0
      while (offset < line.length) {
        const written = writeSync(fd, line, offset, line.length - offset)
        if (written < 1) throw new Error('A0 audit write made no progress')
        offset += written
      }
      fsyncSync(fd)
    } finally {
      closeSync(fd)
    }
  }
}
