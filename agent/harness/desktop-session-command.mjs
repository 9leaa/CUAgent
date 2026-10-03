/** Explicit lifecycle command used by the upcoming trusted Desktop adapter.
 * Does not activate profiles, deploy a VM, grant permission or run an Agent loop.
 */
import assert from 'node:assert/strict';
import { readFileSync, lstatSync, realpathSync } from 'node:fs';
import { isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createDesktopRpc, startDesktopSession, cancelDesktopSession } from './desktop-session.mjs';
import { officialSessionReader, inspectAndArchiveDesktopSession } from './desktop-session-evidence.mjs';

export async function sessionCommand(args) {
  const [mode, root, home, cookie] = args;
  assert.equal(args.length, 4);
  assert.ok(['start', 'inspect', 'cancel'].includes(mode));
  assert.ok([root, home, cookie].every(value => typeof value === 'string' && isAbsolute(value)));
  const rpc = createDesktopRpc(cookie);
  const reader = officialSessionReader(home);
  if (mode === 'start') {
    const path = join(root, 'desktop-request.json');
    assert.equal(realpathSync(path), path);
    const info = lstatSync(path);
    assert.ok(info.isFile() && info.size <= 16384 && !(info.mode & 0o077));
    return startDesktopSession(root, JSON.parse(readFileSync(path, 'utf8')), rpc);
  }
  if (mode === 'inspect') return inspectAndArchiveDesktopSession(root, rpc, reader);
  return cancelDesktopSession(root, rpc, sessionId => reader(sessionId).rows);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    console.log(JSON.stringify(await sessionCommand(process.argv.slice(2))));
  } catch {
    // The original request/response files retain private diagnostic evidence.
    console.error('DESKTOP_SESSION_COMMAND_UNCONFIRMED');
    process.exitCode = 1;
  }
}
