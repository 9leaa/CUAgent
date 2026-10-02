import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { A1_TEXT_INPUTS, expectedTextRecords, expectedTextMarkdown, verifyA1TextArtifacts } from '../a1-text-verifier.mjs';
function fixture() {
	const json = JSON.stringify({ records: expectedTextRecords() }, null, 2) + '\n', markdown = expectedTextMarkdown();
	return { sources: { ...A1_TEXT_INPUTS }, json, markdown,
		readbacks: [['text-records.json', json], ['text-report.md', markdown]].map(([path, content]) => ({ path, content, startLine: 1, truncated: false, bytes: Buffer.byteLength(content), sha256: createHash('sha256').update(content).digest('hex') })) };
}
test('new three-text oracle checks every extracted field, exact source and full artifact readbacks', () => {
	// Task format specifies a blank line after every record, including the last.
	assert.ok(expectedTextMarkdown().endsWith('\n\n'));
	assert.equal(verifyA1TextArtifacts(fixture()).contentVerified, true);
});
test('text oracle rejects every wrong field, provenance, omitted record and extra data', () => {
	for (let index = 0; index < 3; index++) {
		for (const key of Object.keys(expectedTextRecords()[index].fields)) {
			const input = fixture(), result = JSON.parse(input.json); result.records[index].fields[key] = 'wrong'; input.json = JSON.stringify(result);
			assert.throws(() => verifyA1TextArtifacts(input), /fields or source/);
		}
	}
	for (const mutate of [result => { result.records.pop(); }, result => { result.extra = true; }, result => { result.records[0].source.path = 'ticket.txt'; }, result => { result.records[0].source.sha256 = '0'.repeat(64); }]) {
		const input = fixture(), result = JSON.parse(input.json); mutate(result); input.json = JSON.stringify(result); assert.throws(() => verifyA1TextArtifacts(input));
	}
});
test('text oracle rejects altered source, plausible wrong report and missing/partial/stale readbacks', () => {
	for (const mutate of [input => { input.sources['project.txt'] += 'changed'; }, input => { input.markdown = input.markdown.replace('林舟', '陈禾'); }, input => { input.readbacks.pop(); }, input => { input.readbacks[0].truncated = true; }, input => { input.readbacks[0].sha256 = '0'.repeat(64); }]) {
		const input = fixture(); mutate(input); assert.throws(() => verifyA1TextArtifacts(input));
	}
});
