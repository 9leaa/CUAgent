import assert from 'node:assert/strict';
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { A1Policy } from '../a1-policy.mjs';

function fixture(t) {
	const root = mkdtempSync(join(tmpdir(), 'cuagent-a1-policy-'));
	t.after(() => rmSync(root, { recursive: true, force: true }));
	const workspaceRoot = join(root, 'workspace'); const audit = join(root, 'audit');
	mkdirSync(workspaceRoot); mkdirSync(audit, { mode: 0o700 });
	const options = { workspaceRoot, ledgerPath: join(audit, 'calls.jsonl'), runId: 'a1-test', sessionId: 'session-one', allowedTools: ['workspace_read', 'workspace_write'] };
	const call = id => ({ sessionId: options.sessionId, callId: `call-${id}`, name: 'workspace_read', aborted: false, arguments: { path: 'test.txt' } });
	return { options, call, policy: new A1Policy(options) };
}

test('scheduled report binds its deadline, rejects early renderer and direct Markdown writes', t => {
	const { options, call } = fixture(t);
	let now = Date.now();
	t.mock.method(Date, 'now', () => now);
	const bound = { ...options, allowedTools: [...options.allowedTools, 'workspace_daily_report'], publishNotBefore: now + 60000 };
	const policy = new A1Policy(bound);
	for (const path of ['report.md', '@report.md', './report.md', 'other.md']) {
		assert.match(policy.dispatch({ ...call(path), name: 'workspace_write', arguments: { path } }), /publication/);
	}
	assert.match(policy.dispatch({ ...call('render'), name: 'workspace_daily_report', arguments: {} }), /publication/);
	const draft = { ...call('draft'), name: 'workspace_write', arguments: { path: 'report.json' } };
	assert.equal(policy.dispatch(draft), undefined); policy.assertAdmitted(draft); policy.result(draft);
	assert.equal(policy.count(), 1);
	assert.throws(() => new A1Policy({ ...bound, publishNotBefore: now }), /identity/);
	now += 60000;
	const render = { ...call('render-on-time'), name: 'workspace_daily_report', arguments: {} };
	assert.equal(policy.dispatch(render), undefined);
	now -= 1;
	assert.throws(() => policy.assertAdmitted(render), /admission/);
});

test('A1 fixed 30-call budget persists across completed calls and restart', t => {
	const { options, call, policy } = fixture(t);
	for (let i = 0; i < 29; i++) { assert.equal(policy.dispatch(call(i)), undefined); policy.result(call(i), i % 2 ? { errorCode: 'UNAVAILABLE' } : {}); }
	const resumed = new A1Policy(options);
	assert.equal(resumed.count(), 29);
	assert.equal(resumed.dispatch(call(29)), undefined); resumed.result(call(29));
	assert.match(resumed.dispatch(call(30)), /budget exhausted/);
	assert.equal(new A1Policy(options).count(), 30);
});

test('A1 rejects foreign session, stopped turn, unknown tool and repeated call IDs', t => {
	const { call, policy } = fixture(t);
	for (const change of [{ sessionId: 'other' }, { aborted: true }, { name: 'shell' }, { callId: '' }]) assert.ok(policy.dispatch({ ...call(0), ...change }));
	assert.equal(policy.count(), 0);
	assert.equal(policy.dispatch(call(0)), undefined); policy.result(call(0));
	assert.match(policy.dispatch(call(0)), /already used/);
	assert.equal(policy.count(), 1);
	assert.throws(() => policy.workspaceFor('other'), /session mismatch/);
});

test('A1 denied attempts are audited without dispatching or storing attacker text', t => {
	const { options, call, policy } = fixture(t);
	assert.ok(policy.dispatch({ ...call(0), sessionId: 'SECRET_SESSION', name: 'SECRET_TOOL' }));
	const raw = readFileSync(options.ledgerPath, 'utf8');
	assert.ok(!raw.includes('SECRET_SESSION') && !raw.includes('SECRET_TOOL'));
	assert.equal(JSON.parse(raw).event, 'denied');
	assert.equal(new A1Policy(options).count(), 0);
});

test('A1 restart refuses an unresolved side effect without replay or reset', t => {
	const { options, call, policy } = fixture(t);
	assert.equal(policy.dispatch(call(0)), undefined);
	const restarted = new A1Policy(options);
	assert.equal(restarted.count(), 1);
	assert.match(restarted.dispatch(call(1)), /unresolved dispatch/);
	assert.throws(() => restarted.result(call(0)), /unmatched/);
});

test('A1 ledger cannot be reused with changed session, root or capabilities', t => {
	const { options, call, policy } = fixture(t);
	policy.dispatch(call(0)); policy.result(call(0));
	for (const override of [{ sessionId: 'other' }, { runId: 'other' }, { allowedTools: ['workspace_read'] }]) assert.throws(() => new A1Policy({ ...options, ...override }), /identity/);
	assert.throws(() => new A1Policy({ ...options, allowedTools: ['shell'] }), /unreviewed/);
	assert.throws(() => new A1Policy({ ...options, ledgerPath: join(options.workspaceRoot, 'audit.jsonl') }), /outside/);
});

test('A1 competing instances and post-activation ledger tampering fail closed', t => {
	const { options, call, policy } = fixture(t);
	const competing = new A1Policy(options);
	policy.dispatch(call(0)); policy.result(call(0));
	assert.match(competing.dispatch(call(1)), /audit unavailable/);
	const resumed = new A1Policy(options);
	writeFileSync(options.ledgerPath, '', { mode: 0o600 });
	assert.match(resumed.dispatch(call(1)), /audit unavailable/);
	assert.equal(resumed.count(), 1);
});

test('A1 audit correlates calls, sanitizes content and stores timing/artifact hashes', t => {
	const { options, call, policy } = fixture(t);
	const execution = { ...call(0), arguments: { content: 'SECRET_SENTINEL' } };
	policy.dispatch(execution);
	policy.result(execution, { artifact: { bytes: 3, sha256: 'a'.repeat(64), content: 'SECRET_SENTINEL' } });
	const raw = readFileSync(options.ledgerPath, 'utf8');
	assert.ok(!raw.includes('SECRET_SENTINEL'));
	const entries = raw.trim().split('\n').map(JSON.parse);
	assert.equal(entries.length, 2);
	assert.equal(entries[0].callId, entries[1].callId);
	assert.equal(entries[1].sessionId, options.sessionId);
	assert.ok(entries[1].durationMs >= 0);
	assert.deepEqual(entries[1].artifact, { bytes: 3, sha256: 'a'.repeat(64) });
});

test('A1 removed root, mismatched result and unsafe audit permissions block further calls', t => {
	const { options, call, policy } = fixture(t);
	assert.equal(policy.dispatch(call(0)), undefined);
	assert.throws(() => policy.result({ ...call(0), name: 'workspace_write' }), /unmatched/);
	assert.match(policy.dispatch(call(1)), /audit unavailable/);
	const { options: separate, call: otherCall, policy: other } = fixture(t);
	chmodSync(join(separate.ledgerPath, '..'), 0o755);
	assert.throws(() => new A1Policy(separate), /private/);
	assert.match(other.dispatch(otherCall(0)), /audit unavailable/);
	const { options: third, call: thirdCall, policy: thirdPolicy } = fixture(t);
	rmSync(third.workspaceRoot, { recursive: true });
	assert.match(thirdPolicy.dispatch(thirdCall(0)), /root changed/);
});
