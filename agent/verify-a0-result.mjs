/** Independent, read-only check of the A0 file-tool result. */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { lstat, readFile } from 'node:fs/promises'
import { isAbsolute, join } from 'node:path'

const expected = process.argv[2]
if (expected === undefined) {
  throw new Error('usage: CUAGENT_A0_WORKSPACE_ROOT=<test-dir> node agent/verify-a0-result.mjs <expected-exact-content>')
}

const workspaceRoot = process.env.CUAGENT_A0_WORKSPACE_ROOT
if (!workspaceRoot || !isAbsolute(workspaceRoot)) {
  throw new Error('set CUAGENT_A0_WORKSPACE_ROOT to the isolated test workspace')
}
const target = join(workspaceRoot, 'result.txt')
const info = await lstat(target)
assert.ok(info.isFile() && !info.isSymbolicLink(), 'result.txt must be a regular file')
const bytes = await readFile(target)
const actual = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
assert.equal(actual, expected, 'result.txt content differs from the independent expected value')
console.log(JSON.stringify({
  verified: true,
  bytes: bytes.length,
  sha256: createHash('sha256').update(bytes).digest('hex'),
}))
