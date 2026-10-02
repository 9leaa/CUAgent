/** Fixed new synthetic inputs and independent developer-side field/source oracle. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
const sha = value => createHash('sha256').update(value).digest('hex');
export const A1_TEXT_INPUTS = Object.freeze({
	'project.txt': '项目编号：PRJ-614\n负责人：林舟\n优先级：高\n截止日期：2026-10-18\n状态：计划中\n',
	'meeting.md': '# 评审会议\n会议编号：MTG-207\n日期：2026-10-02\n决定：仅使用专用测试目录\n行动项：新增CSV验收\n负责人：陈禾\n',
	'ticket.txt': '工单编号：TKT-903\n报告人：吴青\n严重程度：中\n问题：重复会话串目录\n预期：越界拒绝并留审计\n',
});
export function expectedTextRecords() {
	// Manually specified oracle, never derived with the extraction implementation.
	return [
		{ type: 'project', id: 'PRJ-614', fields: { owner: '林舟', priority: '高', deadline: '2026-10-18', status: '计划中' }, source: { path: 'project.txt', sha256: sha(A1_TEXT_INPUTS['project.txt']) } },
		{ type: 'meeting', id: 'MTG-207', fields: { date: '2026-10-02', decision: '仅使用专用测试目录', action: '新增CSV验收', owner: '陈禾' }, source: { path: 'meeting.md', sha256: sha(A1_TEXT_INPUTS['meeting.md']) } },
		{ type: 'ticket', id: 'TKT-903', fields: { reporter: '吴青', severity: '中', issue: '重复会话串目录', expected: '越界拒绝并留审计' }, source: { path: 'ticket.txt', sha256: sha(A1_TEXT_INPUTS['ticket.txt']) } },
	];
}
export function expectedTextMarkdown() {
	return ['# Extracted records', '', ...expectedTextRecords().flatMap(record => [
		`## ${record.type}`, `ID: ${record.id}`,
		...Object.entries(record.fields).map(([key, value]) => `${key}: ${value}`),
		`Source: ${record.source.path}`, `Source SHA-256: ${record.source.sha256}`, '',
	])].join('\n') + '\n';
}
export function verifyA1TextArtifacts({ sources, json, markdown, readbacks }) {
	assert.deepEqual(sources, A1_TEXT_INPUTS, 'source text bytes changed');
	assert.deepEqual(JSON.parse(json), { records: expectedTextRecords() }, 'fields or source provenance differ');
	assert.equal(markdown, expectedTextMarkdown(), 'complete Markdown differs');
	assert.ok(Array.isArray(readbacks) && readbacks.length === 2, 'both complete readbacks are required');
	const artifacts = [['text-records.json', json], ['text-report.md', markdown]];
	for (const [path, content] of artifacts) {
		const matches = readbacks.filter(item => item?.path === path);
		assert.equal(matches.length, 1, 'unique readback required');
		const actual = matches[0];
		assert.equal(actual.startLine, 1); assert.equal(actual.truncated, false);
		assert.equal(actual.content, content); assert.equal(actual.bytes, Buffer.byteLength(content));
		assert.equal(actual.sha256, sha(content));
	}
	return { contentVerified: true, requiresExecutionEvidence: true,
		sources: Object.entries(sources).map(([path, content]) => ({ path, sha256: sha(content), bytes: Buffer.byteLength(content) })),
		artifacts: artifacts.map(([path, content]) => ({ path, sha256: sha(content), bytes: Buffer.byteLength(content) })) };
}
