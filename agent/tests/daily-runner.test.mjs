import test from 'node:test';
import assert from 'node:assert/strict';
import { observedSession } from '../harness/daily-report-runner.mjs';

test('recovery observation matches exact official prompt identity without echoing content', () => {
  const rows = [{ type: 'turn/start', data: {} },
    { type: 'user/message', data: { source: { kind: 'user', rpcId: 'original' }, content: 'private' } },
    { type: 'tool/call', data: {} }, { type: 'turn/end', data: { reason: 'completed' } }];
  const observed = observedSession('session', false, rows, 'original');
  assert.equal(observed.promptObserved, true);
  assert.equal(observed.terminal, true);
  assert.equal(observed.calls, 1);
  assert.equal(JSON.stringify(observed).includes('private'), false);
  assert.equal(observedSession('session', false, rows, 'different').promptObserved, false);
  assert.equal(observedSession('session', true, rows, 'original').terminal, false);
});

test('old turn completion never certifies a later unfinished turn', () => {
  const rows = [{ type: 'turn/start', data: {} }, { type: 'turn/end', data: { reason: 'completed' } },
    { type: 'turn/start', data: {} }];
  assert.equal(observedSession('session', false, rows).terminal, false);
  assert.equal(observedSession('session', false, []).terminal, false);
  assert.equal(observedSession('session', false, []).promptObserved, false);
});
