import assert from 'node:assert/strict'
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test, type TestContext } from 'node:test'
import { A0Policy, type A0Call } from './a0-policy.ts'

function fixture(t: TestContext) {
  const dir = mkdtempSync(join(tmpdir(), 'cuagent-a0-policy-'))
  t.after(() => rmSync(dir, { recursive: true, force: true }))
  return join(dir, 'audit.jsonl')
}

const call = (number: number, overrides: Partial<A0Call> = {}): A0Call => ({
  sessionId: 'task-one', callId: `call-${number}`, name: 'workspace_read', aborted: false, ...overrides,
})

test('limits admitted calls to 30 and retains the count after restart', t => {
  const path = fixture(t)
  const policy = new A0Policy(path, 'run-one', ['workspace_read'])
  for (let i = 1; i <= 30; i++) {
    assert.equal(policy.guard(call(i)), undefined)
    assert.equal(policy.dispatch(call(i)), undefined)
  }
  assert.match(policy.guard(call(31)) ?? '', /budget exhausted/)
  assert.equal(policy.count(), 30)
  const resumed = new A0Policy(path, 'run-one', ['workspace_read'])
  assert.equal(resumed.count(), 30)
  assert.match(resumed.guard(call(32)) ?? '', /budget exhausted/)
  assert.match(resumed.guard(call(33, { sessionId: 'task-two' })) ?? '', /budget exhausted/)
  const newRun = new A0Policy(path, 'run-two', ['workspace_read'])
  assert.equal(newRun.dispatch(call(34, { sessionId: 'task-two' })), undefined)
  assert.equal(newRun.count(), 1)
})

test('forbidden and stopped calls never reserve a slot', t => {
  const path = fixture(t)
  const policy = new A0Policy(path, 'run-one', ['workspace_read'])
  assert.match(policy.guard(call(1, { name: 'bash' })) ?? '', /not allowed/)
  assert.match(policy.guard(call(2, { aborted: true })) ?? '', /stopped/)
  assert.match(policy.guard(call(3, { sessionId: undefined })) ?? '', /session is required/)
  assert.equal(policy.count(), 0)
  assert.equal(policy.guard(call(4)), undefined)
  assert.match(policy.dispatch(call(4, { aborted: true })) ?? '', /stopped/)
  assert.equal(policy.count(), 0)
  assert.equal(policy.dispatch(call(4)), undefined)
  assert.equal(policy.count(), 1)
  policy.result(call(4), 'TOOL_FAILED')
  const entries = readFileSync(path, 'utf8').trim().split('\n').map(line => JSON.parse(line))
  assert.deepEqual(entries.map(entry => entry.event), ['denied', 'denied', 'denied', 'denied', 'dispatch', 'result'])
  assert.equal(entries.at(-1).errorCode, 'TOOL_FAILED')
  assert.equal(entries.some(entry => 'arguments' in entry), false)
})

test('corrupt ledger fails closed instead of resetting the budget', t => {
  const path = fixture(t)
  writeFileSync(path, '{broken\n')
  assert.throws(() => new A0Policy(path, 'run-one', ['workspace_read']))
})

test('failed calls and retries consume budget, while audit write failure blocks dispatch', t => {
  const path = fixture(t)
  const policy = new A0Policy(path, 'run-one', ['workspace_read'])
  assert.equal(policy.dispatch(call(1)), undefined)
  policy.result(call(1), 'READ_FAILED')
  assert.equal(policy.dispatch(call(2)), undefined)
  assert.equal(policy.count(), 2)
  rmSync(path)
  mkdirSync(path)
  assert.match(policy.dispatch(call(3)) ?? '', /audit unavailable/)
  assert.equal(policy.count(), 2)
})
