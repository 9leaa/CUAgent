/** Pure aggregation. Every I/O must use the caller's counted, audited invoke. */
import { WorkspacePathError } from './workspace-path.mjs';

const require = (ok, code = 'INVALID_TASK') => {
  if (!ok) throw new WorkspacePathError(code, 'report inputs rejected');
};
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
  && Object.keys(value).sort().join(',') === [...keys].sort().join(',');
const sha = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);

export async function collectReportInputs({ invoke, signal }) {
  require(typeof invoke === 'function' && typeof signal?.throwIfAborted === 'function');
  let sequence = 0;
  const call = async (name, args) => {
    signal.throwIfAborted();
    const value = await invoke(name, args, ++sequence);
    signal.throwIfAborted();
    return value;
  };
  const fullRead = async path => {
    const value = await call('workspace_read', { path });
    require(value?.path === path && value.truncated === false && typeof value.content === 'string'
      && sha(value.sha256) && Number.isSafeInteger(value.bytes) && value.bytes >= 0, 'INCOMPLETE_INPUT');
    return value;
  };
  const source = await fullRead('task.json');
  let task;
  try { task = JSON.parse(source.content); } catch { require(false); }
  require(exact(task, ['version', 'date', 'notes', 'csv', 'workflow']) && task.version === 1
    && task.workflow === 'renderer-v1' && typeof task.date === 'string'
    && /^\d{4}-\d{2}-\d{2}$/.test(task.date));
  const date = new Date(task.date + 'T00:00:00Z');
  require(Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === task.date);
  require(Array.isArray(task.notes) && task.notes.length >= 1 && task.notes.length <= 3
    && task.notes.every(p => typeof p === 'string' && /^inputs\/[A-Za-z0-9_-]+\.md$/.test(p)));
  require(Array.isArray(task.csv) && task.csv.length >= 1 && task.csv.length <= 2);
  for (const item of task.csv) {
    require(exact(item, ['path', 'numericColumns']) && typeof item.path === 'string'
      && /^inputs\/[A-Za-z0-9_-]+\.csv$/.test(item.path)
      && Array.isArray(item.numericColumns) && item.numericColumns.length >= 1 && item.numericColumns.length <= 4
      && item.numericColumns.every(c => typeof c === 'string' && c.length > 0 && !/[|\n\r\0]/.test(c))
      && new Set(item.numericColumns).size === item.numericColumns.length);
  }
  const paths = [...task.notes, ...task.csv.map(c => c.path)];
  require(new Set(paths).size === paths.length);
  const result = { task: source, notes: [], csv: [] };
  const bounded = () => require(Buffer.byteLength(JSON.stringify(result)) <= 65536, 'OUTPUT_TOO_LARGE');
  bounded();
  for (const path of task.notes) {
    const note = await fullRead(path);
    require(note.bytes <= 6000 && note.content.split(/\r\n|\n|\r/).length <= 41, 'INPUT_TOO_LARGE');
    result.notes.push(note);
    bounded();
  }
  for (const item of task.csv) {
    const value = await call('workspace_csv_stats', { path: item.path, numericColumns: item.numericColumns });
    require(exact(value, ['path', 'rowCount', 'columnCount', 'columns', 'numeric', 'bytes', 'sha256'])
      && value.path === item.path && sha(value.sha256), 'INCOMPLETE_INPUT');
    result.csv.push(value);
    bounded();
  }
  signal.throwIfAborted();
  return result;
}
