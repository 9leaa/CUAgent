/** Explicit trusted lifecycle entrypoint; never starts an Agent prompt. */
import { isAbsolute } from 'node:path';
import { stopIdleDesktop, startDesktop } from './desktop-app.mjs';

try {
  const [mode, root, home, cookie, launchFile] = process.argv.slice(2);
  if (process.argv.length !== 7 || !['stop-activate', 'stop-restore', 'start-p6', 'start-p7', 'start-calc', 'start-restore'].includes(mode)
      || ![root, home, cookie, launchFile].every(value => typeof value === 'string' && isAbsolute(value))) throw Error('arguments');
  const result = mode.startsWith('stop-') ? await stopIdleDesktop(root, cookie, mode.slice(5))
    : await startDesktop(root, home, cookie, mode.slice(6), launchFile);
  console.log(JSON.stringify(result));
} catch {
  console.error('DESKTOP_APP_LIFECYCLE_UNCONFIRMED');
  process.exitCode = 1;
}
