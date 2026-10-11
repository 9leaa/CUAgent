/** No App restart; trusted caller must stop it and own the shared desktop lock. */
import { prepareDesktopProfile, applyDesktopProfile, restoreDesktopProfile } from './desktop-profile.mjs';
import { join, isAbsolute } from 'node:path';
import { lstatSync, realpathSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

try {
  const [mode, root, home, buildTools] = process.argv.slice(2);
  if (process.argv.length !== 6 || !['prepare', 'prepare-handoff', 'prepare-calc', 'apply', 'restore'].includes(mode)) throw Error('arguments');
  let parseYaml;
  if (mode === 'restore') {
    const info = lstatSync(buildTools);
    if (!isAbsolute(buildTools) || realpathSync(buildTools) !== buildTools || !info.isDirectory()
        || info.uid !== process.getuid() || (info.mode & 0o022)) throw Error('trusted parser required');
    parseYaml = (await import(pathToFileURL(join(buildTools, 'node_modules/js-yaml/index.js')).href)).load;
  }
  const result = mode.startsWith('prepare') ? await prepareDesktopProfile(root, home, buildTools,
      mode === 'prepare-calc' ? 'calc-selection' : mode === 'prepare-handoff' ? 'project-handoff' : 'desktop-textedit')
    : mode === 'apply' ? applyDesktopProfile(root, home) : restoreDesktopProfile(root, home, undefined, parseYaml);
  console.log(JSON.stringify(result));
} catch {
  console.error('DESKTOP_PROFILE_UNCONFIRMED');
  process.exitCode = 1;
}
