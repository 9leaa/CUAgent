/** A1 task admission and audit. No model loop, mutable budget, or implicit approval. */
import { createHash } from 'node:crypto';
import { closeSync, existsSync, fsyncSync, lstatSync, openSync, readFileSync, realpathSync, unlinkSync, writeSync } from 'node:fs';
import { basename, dirname, isAbsolute, join, relative, sep } from 'node:path';

export const A1_REVIEWED_TOOLS = Object.freeze(['calculate', 'workspace_image_probe', 'workspace_list', 'workspace_read', 'workspace_write', 'workspace_csv_stats']);
// Reviewed example candidates, never implicitly enabled by a preset or default task.
export const A1_REVIEWED_EXTENSION_TOOLS = Object.freeze(['workspace_text_fingerprint', 'workspace_daily_report']);
const sha = value => createHash('sha256').update(value).digest('hex');
const inside = (root, target) => { const path = relative(root, target); return path === '' || (!isAbsolute(path) && path !== '..' && !path.startsWith(`..${sep}`)); };
const safeCode = code => typeof code === 'string' && /^[A-Z0-9_]{1,80}$/.test(code) ? code : 'TOOL_ERROR';

export class A1Policy {
	#used = 0; #pending = new Map(); #seen = new Set(); #failed = false;
	#ledger; #run; #session; #root; #rootIdentity; #allowed; #identity;
	#snapshot;
	#controlPath; #controlEpoch;
	constructor({ ledgerPath, runId, sessionId, workspaceRoot, allowedTools, controlPath, controlEpoch }) {
		if (!/^[A-Za-z0-9_-]{1,80}$/.test(runId ?? '') || typeof sessionId !== 'string' || !sessionId || sessionId.length > 160) throw new Error('invalid A1 task identity');
		if (!isAbsolute(ledgerPath ?? '') || !isAbsolute(workspaceRoot ?? '')) throw new Error('A1 paths must be absolute');
		const root = realpathSync(workspaceRoot);
		const rootStat = lstatSync(root);
		if (!rootStat.isDirectory()) throw new Error('A1 root must be a directory');
		// Require a pre-created, private developer-side audit directory.
		const auditParent = realpathSync(dirname(ledgerPath));
		const auditStat = lstatSync(auditParent);
		if (!auditStat.isDirectory() || (auditStat.mode & 0o077) !== 0 || inside(root, auditParent)) throw new Error('A1 audit directory must be private and outside the workspace');
		if (existsSync(ledgerPath) && (!lstatSync(ledgerPath).isFile() || lstatSync(ledgerPath).isSymbolicLink() || (lstatSync(ledgerPath).mode & 0o077) !== 0)) throw new Error('invalid A1 audit file');
		if (!Array.isArray(allowedTools) || !allowedTools.length || new Set(allowedTools).size !== allowedTools.length || allowedTools.some(name => ![...A1_REVIEWED_TOOLS, ...A1_REVIEWED_EXTENSION_TOOLS].includes(name))) throw new Error('unreviewed A1 capability');
		this.#ledger = join(auditParent, basename(ledgerPath)); this.#run = runId; this.#session = sessionId; this.#root = root;
		this.#rootIdentity = `${rootStat.dev}:${rootStat.ino}`;
		this.#allowed = new Set(allowedTools);
		if (controlPath !== undefined || controlEpoch !== undefined) {
			if (!isAbsolute(controlPath ?? '') || !Number.isSafeInteger(controlEpoch) || controlEpoch < 1) throw new Error('invalid backend control binding');
			const parent = realpathSync(dirname(controlPath));
			const canonicalControl = join(parent, basename(controlPath));
			if (inside(root, canonicalControl) || (lstatSync(parent).mode & 0o077) !== 0) throw new Error('invalid backend control binding');
			this.#controlPath = canonicalControl; this.#controlEpoch = controlEpoch;
		}
		this.#identity = sha(JSON.stringify({ runId, sessionId, root, rootIdentity: this.#rootIdentity, allowedTools: [...allowedTools].sort(), limit: 30,
			...(this.#controlPath ? { controlPath: this.#controlPath } : {}) }));
		const initial = existsSync(this.#ledger) ? readFileSync(this.#ledger, 'utf8') : '';
		this.#snapshot = sha(initial);
		for (const line of initial.split('\n')) {
			if (!line) continue;
			const entry = JSON.parse(line);
			if (entry.identity !== this.#identity || entry.runId !== runId || entry.sessionId !== sessionId || !['dispatch', 'result', 'denied', 'request'].includes(entry.event)) throw new Error('A1 ledger identity or event mismatch');
			if (entry.event === 'dispatch') {
				if (entry.used !== this.#used + 1 || this.#used >= 30 || this.#seen.has(entry.callId) || !this.#allowed.has(entry.name)) throw new Error('invalid A1 dispatch sequence');
				this.#used++; this.#seen.add(entry.callId); this.#pending.set(entry.callId, { name: entry.name });
			} else if (entry.event === 'result') {
				if (this.#pending.get(entry.callId)?.name !== entry.name) throw new Error('unmatched A1 result');
				this.#pending.delete(entry.callId);
			}
		}
		// An old in-flight dispatch is UNKNOWN, never silently replayed.
		if (this.#pending.size) this.#failed = true;
	}
	count() { return this.#used; }
	request({ toolNames, provider, model, imageBlocks = 0 }) {
		if (this.#failed || !this.#rootUnchanged() || !this.#controlActive()) throw new Error('A1 request policy unavailable');
		if (!Array.isArray(toolNames) || toolNames.some(name => !this.#allowed.has(name))) throw new Error('A1 request contains an unapproved tool');
		try { this.#append({ event: 'request', toolNames: [...toolNames].sort(),
			providerSha256: sha(String(provider ?? '')), modelSha256: sha(String(model ?? '')),
			imageBlocks: Number.isSafeInteger(imageBlocks) && imageBlocks >= 0 ? imageBlocks : 0 }); }
		catch (error) { this.#failed = true; throw error; }
	}
	assertAdmitted(call) {
		const pending = this.#pending.get(call.callId);
		if (this.#failed || call.aborted || call.sessionId !== this.#session || pending?.name !== call.name || pending.started === undefined || !this.#rootUnchanged() || !this.#controlActive()) throw new Error('A1 execution lacks active admission');
	}
	workspaceFor(sessionId) {
		if (sessionId !== this.#session || !this.#rootUnchanged()) throw new Error('A1 task root or session mismatch');
		return this.#root;
	}
	#rootUnchanged() {
		try { const stat = lstatSync(this.#root); return stat.isDirectory() && `${stat.dev}:${stat.ino}` === this.#rootIdentity && realpathSync(this.#root) === this.#root; } catch { return false; }
	}
	#controlActive() {
		if (!this.#controlPath) return true;
		try {
			const stat = lstatSync(this.#controlPath);
			if (!stat.isFile() || stat.isSymbolicLink() || (stat.mode & 0o077) !== 0 || stat.size > 4096 || realpathSync(this.#controlPath) !== this.#controlPath) return false;
			const value = JSON.parse(readFileSync(this.#controlPath, 'utf8'));
			return value.version === 1 && value.runId === this.#run && value.epoch === this.#controlEpoch
				&& value.stopped === false && Number.isSafeInteger(value.expiresAt)
				&& value.expiresAt > Date.now() && value.expiresAt <= Date.now() + 60000;
		} catch { return false; }
	}
	guard(call) {
		return this.#failed ? 'A1: audit unavailable or unresolved dispatch'
			: call.sessionId !== this.#session ? 'A1: session not approved'
			: !this.#rootUnchanged() ? 'A1: approved root changed'
			: !this.#controlActive() ? 'A1: backend execution lease stopped, stale or unavailable'
			: call.aborted ? 'A1: turn stopped'
			: typeof call.callId !== 'string' || !call.callId || call.callId.length > 160 ? 'A1: invalid call identity'
			: this.#seen.has(call.callId) ? 'A1: call identity already used'
			: !this.#allowed.has(call.name) ? 'A1: tool not approved'
			: this.#used >= 30 ? 'A1: 30-call budget exhausted' : undefined;
	}
	dispatch(call) {
		const reason = this.guard(call);
		if (reason) {
			if (!this.#failed) {
				try { this.#append({ event: 'denied', reason,
					attemptedSessionSha256: sha(String(call.sessionId ?? '')),
					callIdSha256: sha(String(call.callId ?? '')),
					toolSha256: sha(String(call.name ?? '')) }); }
				catch { this.#failed = true; return 'A1: audit unavailable'; }
			}
			return reason;
		}
		try {
			const args = JSON.stringify(call.arguments ?? {});
			this.#append({ event: 'dispatch', callId: call.callId, name: call.name, used: this.#used + 1,
				arguments: { bytes: Buffer.byteLength(args), sha256: sha(args) } });
			this.#used++; this.#seen.add(call.callId);
			this.#pending.set(call.callId, { name: call.name, started: performance.now() });
			return undefined;
		} catch { this.#failed = true; return 'A1: audit unavailable'; }
	}
	result(call, { errorCode, artifact } = {}) {
		const pending = this.#pending.get(call.callId);
		if (call.sessionId !== this.#session || !pending || pending.name !== call.name || pending.started === undefined) { this.#failed = true; throw new Error('unmatched A1 result'); }
		try {
			const reference = artifact && Number.isSafeInteger(artifact.bytes) && artifact.bytes >= 0 && /^[a-f0-9]{64}$/.test(artifact.sha256 ?? '')
				? { bytes: artifact.bytes, sha256: artifact.sha256 } : undefined;
			this.#append({ event: 'result', callId: call.callId, name: call.name,
				durationMs: Math.max(0, performance.now() - pending.started),
				outcome: errorCode === undefined ? 'returned' : 'error',
				...(errorCode === undefined ? {} : { errorCode: safeCode(errorCode) }),
				...(reference ? { artifact: reference } : {}) });
			this.#pending.delete(call.callId);
		} catch (error) { this.#failed = true; throw error; }
	}
	#append(entry) {
		// Exclusive write lock also denies a competing instance with this ledger.
		const lockPath = `${this.#ledger}.lock`;
		const parent = dirname(this.#ledger);
		if (realpathSync(parent) !== parent || (lstatSync(parent).mode & 0o077) !== 0 || inside(this.#root, parent)) throw new Error('audit directory changed');
		const lock = openSync(lockPath, 'wx', 0o600);
		try {
			// Detect out-of-process appends rather than trusting a stale budget.
			if (existsSync(this.#ledger) && (!lstatSync(this.#ledger).isFile() || lstatSync(this.#ledger).isSymbolicLink() || (lstatSync(this.#ledger).mode & 0o077) !== 0)) throw new Error('audit file changed');
			const current = existsSync(this.#ledger) ? readFileSync(this.#ledger, 'utf8') : '';
			if (sha(current) !== this.#snapshot) throw new Error('A1 ledger changed concurrently');
			const diskCount = current.split('\n').filter(Boolean).map(JSON.parse).filter(item => item.event === 'dispatch').length;
			if (diskCount !== this.#used) throw new Error('A1 ledger changed concurrently');
			const fd = openSync(this.#ledger, 'a', 0o600);
			try {
				const data = Buffer.from(JSON.stringify({ at: new Date().toISOString(), identity: this.#identity, runId: this.#run, sessionId: this.#session, ...entry }) + '\n');
				let offset = 0;
				while (offset < data.length) { const written = writeSync(fd, data, offset, data.length - offset); if (written < 1) throw new Error('audit write made no progress'); offset += written; }
				fsyncSync(fd);
				this.#snapshot = sha(Buffer.concat([Buffer.from(current), data]));
			} finally { closeSync(fd); }
		} finally { closeSync(lock); unlinkSync(lockPath); }
	}
}
