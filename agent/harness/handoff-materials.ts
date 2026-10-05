/** Verify the exact frozen material JSON; this is not semantic acceptance. */
import { createHash } from 'node:crypto'

function canonical(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']'
  if (value !== null && typeof value === 'object') return '{' + Object.keys(value).sort()
    .map(key => JSON.stringify(key) + ':' + canonical((value as Record<string, unknown>)[key])).join(',') + '}'
  if (typeof value !== 'string' && typeof value !== 'boolean' && value !== null
      && !(typeof value === 'number' && Number.isFinite(value))) throw new Error('Invalid material JSON')
  return JSON.stringify(value)
}

export function verifyHandoffMaterials(value: any, expected: string): string {
  if (!value || Array.isArray(value) || typeof value !== 'object'
      || Object.keys(value).sort().join(',') !== 'inputSha256,materials,used'
      || !/^[0-9a-f]{64}$/.test(expected) || value.inputSha256 !== expected
      || !Number.isInteger(value.used) || value.used < 1 || value.used > 30
      || !value.materials || Array.isArray(value.materials) || typeof value.materials !== 'object'
      || value.materials.kind !== 'project-handoff'
      || Object.keys(value.materials).sort().join(',') !== 'asOf,kind,notes,previousReport,project,tasksCsv') {
    throw new Error('Handoff material binding invalid')
  }
  const encoded = canonical(value.materials)
  if (Buffer.byteLength(encoded, 'utf8') > 256 * 1024
      || createHash('sha256').update(encoded, 'utf8').digest('hex') !== expected) {
    throw new Error('Handoff material bytes differ from frozen input')
  }
  return JSON.stringify({ materials: value.materials, inputSha256: expected, used: value.used })
}
