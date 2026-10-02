// Developer-side content verifier. Never register this as an Agent tool.
// No import of the implementation under test; the public fixture oracle is fixed.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

export const A1_SALES_SOURCE = 'region,units,revenue\nNorth,2,100\nSouth,3,150\nEast,1,70\nWest,5,110\nNorth,3,\n';
export const A1_SALES_EXPECTED = Object.freeze({
	path: 'sales.csv', rowCount: 5, columnCount: 3,
	columns: ['region', 'units', 'revenue'],
	numeric: {
		units: { count: 5, missing: 0, sum: 14, min: 1, max: 5, mean: 2.8 },
		revenue: { count: 4, missing: 1, sum: 430, min: 70, max: 150, mean: 107.5 },
	},
	bytes: Buffer.byteLength(A1_SALES_SOURCE),
	sha256: hash(A1_SALES_SOURCE),
});

function hash(value) { return createHash('sha256').update(value).digest('hex'); }

// The controlled task supplies this report format, but not expected numbers.
// Exact comparison prevents correct-looking prose hiding incorrect table cells.
export function expectedSalesMarkdown() {
	const expected = A1_SALES_EXPECTED;
	return [
		'# Sales statistics', '',
		`Source: ${expected.path}`, `Source SHA-256: ${expected.sha256}`,
		`Source bytes: ${expected.bytes}`, `Data rows: ${expected.rowCount}`,
		`Columns: ${expected.columnCount}`, `Headers: ${expected.columns.join(', ')}`, '',
		'| Column | Count | Missing | Sum | Min | Max | Mean |',
		'| --- | --- | --- | --- | --- | --- | --- |',
		...Object.entries(expected.numeric).map(([name, stat]) =>
			`| ${name} | ${stat.count} | ${stat.missing} | ${stat.sum} | ${stat.min} | ${stat.max} | ${stat.mean} |`), '',
	].join('\n');
}

/**
 * Verify artifact bytes and complete readbacks against a protected oracle.
 * This proves content only. The caller must separately verify actual official
 * session/call IDs, stats/read/write trajectory, budget and policy admission.
 */
export function verifyA1SalesArtifacts({ source, json, markdown, readbacks }) {
	assert.equal(source, A1_SALES_SOURCE, 'source fixture changed');
	assert.equal(typeof json, 'string', 'JSON artifact must be UTF-8 text');
	assert.deepEqual(JSON.parse(json), A1_SALES_EXPECTED, 'complete statistics differ');
	assert.equal(markdown, expectedSalesMarkdown(), 'Markdown fields or source provenance differ');
	assert.ok(Array.isArray(readbacks), 'readback evidence is required');
	assert.equal(readbacks.length, 2, 'both artifacts need one complete readback');
	const artifacts = [['csv-stats.json', json], ['csv-report.md', markdown]];
	for (const [path, content] of artifacts) {
		const matches = readbacks.filter(item => item?.path === path);
		assert.equal(matches.length, 1, `missing or duplicate readback: ${path}`);
		const actual = matches[0];
		assert.equal(actual.truncated, false, `truncated readback: ${path}`);
		assert.equal(actual.startLine, 1, `partial readback: ${path}`);
		assert.equal(actual.content, content, `readback content mismatch: ${path}`);
		assert.equal(actual.bytes, Buffer.byteLength(content), `readback bytes mismatch: ${path}`);
		assert.equal(actual.sha256, hash(content), `readback hash mismatch: ${path}`);
	}
	return {
		contentVerified: true,
		// Deliberately not SUCCEEDED: artifact presence is not tool execution proof.
		requiresExecutionEvidence: true,
		source: { path: 'sales.csv', bytes: Buffer.byteLength(source), sha256: hash(source) },
		artifacts: artifacts.map(([path, content]) => ({ path, bytes: Buffer.byteLength(content), sha256: hash(content) })),
	};
}
