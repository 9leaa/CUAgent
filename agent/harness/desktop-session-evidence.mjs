/** Read-only official persistence adapter. Never modifies Harness session files. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { constants, existsSync, lstatSync, openSync, closeSync, fstatSync,
  readFileSync, readSync, readdirSync, realpathSync, writeFileSync } from 'node:fs';
import { isAbsolute, join, resolve } from 'node:path';
import { inspectDesktopSession } from './desktop-session.mjs';

const LIMIT = 64 * 1024 * 1024;

export function officialSessionReader(home) {
  assert.ok(isAbsolute(home) && realpathSync(home) === resolve(home));
  const info = lstatSync(home);
  assert.ok(info.isDirectory() && info.uid === process.getuid() && !(info.mode & 0o077));
  const sessions = join(home, 'sessions');
  assert.equal(realpathSync(sessions), sessions);
  assert.ok(lstatSync(sessions).isDirectory());
  return sessionId => {
    assert.match(sessionId, /^session-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u);
    const candidates = [];
    for (const group of readdirSync(sessions)) {
      const directory = join(sessions, group);
      if (!lstatSync(directory).isDirectory() || realpathSync(directory) !== directory) continue;
      const target = join(directory, sessionId, 'session.v4.jsonl.zstd');
      if (!existsSync(target)) continue;
      assert.equal(realpathSync(target), target, 'session path may not contain links');
      candidates.push(target);
    }
    assert.equal(candidates.length, 1, 'unique official session required');
    const fd = openSync(candidates[0], constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    let compressed;
    try {
      const current = fstatSync(fd);
      assert.ok(current.isFile() && current.uid === process.getuid() && current.size > 0 && current.size <= LIMIT);
      const bounded = Buffer.alloc(current.size + 1);
      let size = 0, count;
      while (size < bounded.length && (count = readSync(fd, bounded, size, bounded.length - size, null))) size += count;
      assert.equal(size, current.size, 'source changed while collecting');
      compressed = bounded.subarray(0, size);
    } finally { closeSync(fd); }
    const bytes = execFileSync('/opt/homebrew/bin/zstd', ['-dc'], {
      input: compressed, maxBuffer: LIMIT, timeout: 10000, stdio: ['pipe', 'pipe', 'ignore'],
    });
    const raw = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    const rows = raw.trimEnd().split('\n').map(line => JSON.parse(line));
    assert.ok(rows.length > 0 && rows.every(row => row && typeof row.type === 'string'));
    return { raw, rows };
  };
}

export async function inspectAndArchiveDesktopSession(root, rpc, readSession) {
  let snapshot;
  const observed = await inspectDesktopSession(root, rpc, sessionId => {
    snapshot = readSession(sessionId);
    return snapshot.rows;
  });
  if (observed.terminal) {
    assert.ok(observed.promptObserved && observed.userMessages === 1,
      'terminal evidence must belong to the one original prompt');
    const output = join(root, 'session.jsonl');
    if (existsSync(output)) {
      assert.ok(!lstatSync(output).isSymbolicLink());
      assert.equal(readFileSync(output, 'utf8'), snapshot.raw, 'terminal session evidence changed');
    } else {
      writeFileSync(output, snapshot.raw, { flag: 'wx', mode: 0o600 });
    }
  }
  return observed;
}
