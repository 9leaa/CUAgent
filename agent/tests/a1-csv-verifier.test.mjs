import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { A1_SALES_EXPECTED, A1_SALES_SOURCE, expectedSalesMarkdown, verifyA1SalesArtifacts } from '../a1-csv-verifier.mjs';

function fixture() {
	const json = JSON.stringify(A1_SALES_EXPECTED, null, 2) + '\n';
	const markdown = expectedSalesMarkdown();
	return {
		source: A1_SALES_SOURCE, json, markdown,
		readbacks: [['csv-stats.json', json], ['csv-report.md', markdown]].map(([path, content]) => ({
			path, content, startLine: 1, truncated: false, bytes: Buffer.byteLength(content),
			sha256: createHash('sha256').update(content).digest('hex'),
		})),
	};
}

test('CSV independent oracle verifies every field, provenance and both artifact readbacks', () => {
	const verified = verifyA1SalesArtifacts(fixture());
	assert.equal(verified.contentVerified, true);
	assert.equal(verified.requiresExecutionEvidence, true);
	assert.equal(verified.artifacts.length, 2);
	assert.equal(verified.status, undefined);
});

test('CSV verifier rejects incorrect, missing and extra statistics including every numeric field', () => {
	const paths = [['rowCount'], ['columnCount'], ['bytes'], ['sha256'], ['path'], ['columns'],
		...['units', 'revenue'].flatMap(column => ['count', 'missing', 'sum', 'min', 'max', 'mean'].map(key => ['numeric', column, key]))];
	for (const path of paths) {
		const input = fixture();
		const value = JSON.parse(input.json);
		const parent = path.slice(0, -1).reduce((object, key) => object[key], value);
		parent[path.at(-1)] = 'wrong';
		input.json = JSON.stringify(value);
		assert.throws(() => verifyA1SalesArtifacts(input), /complete statistics differ/);
	}
	for (const mutate of [value => { delete value.numeric.revenue; }, value => { value.unexpected = 1; }]) {
		const input = fixture(); const value = JSON.parse(input.json); mutate(value); input.json = JSON.stringify(value);
		assert.throws(() => verifyA1SalesArtifacts(input), /complete statistics differ/);
	}
});

test('CSV verifier rejects a plausible Markdown report containing correct numbers but false cells', () => {
	const input = fixture();
	input.markdown = input.markdown.replace('| revenue | 4 | 1 |', '| revenue | 1 | 4 |');
	assert.throws(() => verifyA1SalesArtifacts(input), /Markdown fields/);
});

test('CSV verifier rejects changed source, stale hash and incomplete or missing readback evidence', () => {
	for (const mutate of [
		input => { input.source += '\n'; },
		input => { input.readbacks[0].sha256 = '0'.repeat(64); },
		input => { input.readbacks[0].bytes += 1; },
		input => { input.readbacks[0].content = 'partial'; },
		input => { input.readbacks[0].startLine = 2; },
		input => { input.readbacks[0].truncated = true; },
		input => { input.readbacks.pop(); },
		input => { input.readbacks[1] = input.readbacks[0]; },
	]) {
		const input = fixture(); mutate(input);
		assert.throws(() => verifyA1SalesArtifacts(input));
	}
});
