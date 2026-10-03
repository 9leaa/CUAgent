/** No App restart; trusted caller must stop it and own the shared desktop lock. */
import { prepareDesktopProfile, applyDesktopProfile, restoreDesktopProfile } from './desktop-profile.mjs';

try {
  const [mode, root, home, buildTools] = process.argv.slice(2);
  if (process.argv.length !== 6 || !['prepare', 'apply', 'restore'].includes(mode)) throw Error('arguments');
  const result = mode === 'prepare' ? await prepareDesktopProfile(root, home, buildTools)
    : mode === 'apply' ? applyDesktopProfile(root, home) : restoreDesktopProfile(root, home);
  console.log(JSON.stringify(result));
} catch {
  console.error('DESKTOP_PROFILE_UNCONFIRMED');
  process.exitCode = 1;
}
