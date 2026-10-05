/** Trusted conversion provenance; not independent visual/semantic acceptance. */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { closeSync, constants, fstatSync, fsyncSync, lstatSync, openSync, realpathSync, writeFileSync } from 'node:fs'
import { isAbsolute, join } from 'node:path'

export function recordHandoffImage(root: string, binding: { runId: string; sessionId: string; inputSha256: string },
  state: { snapshot_id: string }, used: number, png: Buffer,
  image: { attachmentId: string; mediaType: string; bytes: number; width: number; height: number }): void {
  assert.ok(isAbsolute(root) && realpathSync(root) === root)
  const info = lstatSync(root)
  assert.ok(info.isDirectory() && info.uid === process.getuid() && !(info.mode & 0o077))
  assert.match(binding.runId, /^p2-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/u)
  assert.match(binding.sessionId, /^session-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/u)
  assert.match(binding.inputSha256, /^[0-9a-f]{64}$/u)
  assert.ok(typeof state.snapshot_id === 'string' && state.snapshot_id.length > 0 && state.snapshot_id.length <= 256)
  assert.ok(Number.isInteger(used) && used >= 1 && used <= 30)
  assert.ok(Buffer.isBuffer(png) && png.length >= 8 && png.length <= 8 * 1024 * 1024
    && png.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])))
  assert.match(image.attachmentId, /^sha256:[0-9a-f]{64}$/u)
  assert.ok(['image/png', 'image/webp'].includes(image.mediaType))
  assert.ok([image.bytes, image.width, image.height].every(v => Number.isInteger(v) && v > 0))
  assert.ok(image.bytes <= 8 * 1024 * 1024)
  const attachment = { attachmentId: image.attachmentId, mediaType: image.mediaType,
    bytes: image.bytes, width: image.width, height: image.height }
  const record = { version: 1, ...binding, snapshotId: state.snapshot_id, used,
    source: { sha256: createHash('sha256').update(png).digest('hex'), bytes: png.length }, attachment }
  const parent = openSync(root, constants.O_RDONLY | constants.O_DIRECTORY | constants.O_NOFOLLOW)
  try {
    const current = fstatSync(parent)
    assert.equal(current.ino, info.ino); assert.equal(current.dev, info.dev)
    const fd = openSync(join(root, `handoff-image-${String(used).padStart(2, '0')}.json`),
      constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600)
    try { writeFileSync(fd, JSON.stringify(record) + '\n'); fsyncSync(fd) } finally { closeSync(fd) }
    fsyncSync(parent)
    const after = lstatSync(root)
    assert.equal(realpathSync(root), root)
    assert.equal(after.ino, info.ino); assert.equal(after.dev, info.dev)
    assert.equal(after.uid, process.getuid()); assert.equal(after.mode & 0o077, 0)
  } finally { closeSync(parent) }
}
