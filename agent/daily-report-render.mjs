/** Deterministic presentation only; does not decide task success. */
export function renderDailyReport(report) {
  const check = (ok, message) => { if (!ok) throw new Error('Invalid daily report: ' + message); };
  const keys = (value, expected) => check(value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).sort().join(',') === [...expected].sort().join(','), 'unexpected fields');
  const text = value => check(typeof value === 'string' && value.length > 0 && value.length <= 6000 && !value.includes('\0'), 'text');
  const digest = value => check(typeof value === 'string' && /^[a-f0-9]{64}$/.test(value), 'source hash');
  const source = (value, suffix) => check(typeof value === 'string' && new RegExp(`^inputs/[A-Za-z0-9_-]+\\.${suffix}$`).test(value), 'source path');
  keys(report, ['date', 'notes', 'csv']);
  check(typeof report.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(report.date), 'date');
  check(Array.isArray(report.notes) && report.notes.length >= 1 && report.notes.length <= 3, 'notes');
  check(Array.isArray(report.csv) && report.csv.length >= 1 && report.csv.length <= 2, 'csv');
  const lines = [`# 日报 ${report.date}`, ''];
  for (const note of report.notes) {
    keys(note, ['path', 'sha256', 'title', 'progress', 'blockers', 'next']);
    source(note.path, 'md'); digest(note.sha256);
    for (const key of ['title', 'progress', 'blockers', 'next']) text(note[key]);
    check(!note.title.includes('\n'), 'title');
    lines.push(`## ${note.title}`, `来源: ${note.path}`, `SHA-256: ${note.sha256}`,
      '### 进展', note.progress, '### 阻塞', note.blockers, '### 下一步', note.next, '');
  }
  for (const table of report.csv) {
    keys(table, ['path', 'sha256', 'rowCount', 'columnCount', 'columns', 'numeric', 'bytes']);
    source(table.path, 'csv'); digest(table.sha256);
    for (const key of ['rowCount', 'columnCount', 'bytes']) check(Number.isSafeInteger(table[key]) && table[key] >= 0, key);
    check(Array.isArray(table.columns) && table.columns.length === table.columnCount, 'columns');
    check(table.numeric && typeof table.numeric === 'object' && !Array.isArray(table.numeric)
      && Object.keys(table.numeric).length >= 1 && Object.keys(table.numeric).length <= 4, 'numeric');
    lines.push(`## 数据 ${table.path}`, `SHA-256: ${table.sha256}`, `数据行: ${table.rowCount}`,
      '| 列 | 有效 | 缺失 | 合计 | 最小 | 最大 | 均值 |', '| --- | --- | --- | --- | --- | --- | --- |');
    for (const [column, stats] of Object.entries(table.numeric)) {
      check(table.columns.includes(column) && !/[|\r\n]/.test(column), 'column');
      keys(stats, ['count', 'missing', 'sum', 'min', 'max', 'mean']);
      for (const key of ['count', 'missing']) check(Number.isSafeInteger(stats[key]) && stats[key] >= 0, key);
      for (const key of ['sum', 'min', 'max', 'mean']) check((key !== 'sum' && stats[key] === null) || (typeof stats[key] === 'number' && Number.isFinite(stats[key])), key);
      lines.push('| ' + column + ' | ' + ['count', 'missing', 'sum', 'min', 'max', 'mean'].map(k => String(stats[k])).join(' | ') + ' |');
    }
    lines.push('');
  }
  const content = lines.join('\n');
  check(content.split('\n').length <= 200 && Buffer.byteLength(content) <= 50000, 'full-readback size');
  return content;
}
