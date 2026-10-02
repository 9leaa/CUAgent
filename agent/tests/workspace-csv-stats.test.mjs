import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
	calculateWorkspaceCsvStats,
	parseCsv,
	WORKSPACE_CSV_MAX_FILE_BYTES,
	WorkspaceCsvStatsError,
} from "../workspace-csv-stats.mjs";

async function withWorkspace(run) {
	const testRoot = await mkdtemp(join(tmpdir(), "osagent-workspace-csv-"));
	const workspaceRoot = join(testRoot, "workspace");
	await mkdir(workspaceRoot);
	try {
		await run({ testRoot, workspaceRoot });
	} finally {
		await rm(testRoot, { recursive: true, force: true });
	}
}

async function expectCode(promise, code) {
	await assert.rejects(promise, (error) => {
		assert.ok(error instanceof WorkspaceCsvStatsError);
		assert.equal(error.code, code);
		return true;
	});
}

test("calculates deterministic statistics and missing counts", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(
			join(workspaceRoot, "sales.csv"),
			"region,units,revenue\nNorth,2,100\nSouth,3,150\nEast,1,70\nWest,5,110\nNorth,3,\n",
			"utf8",
		);

		const result = await calculateWorkspaceCsvStats({
			workspaceRoot,
			path: "sales.csv",
			numericColumns: ["units", "revenue"],
		});

		assert.equal(result.rowCount, 5);
		assert.deepEqual(result.columns, ["region", "units", "revenue"]);
		assert.deepEqual(result.numeric.units, { count: 5, missing: 0, sum: 14, min: 1, max: 5, mean: 2.8 });
		assert.deepEqual(result.numeric.revenue, { count: 4, missing: 1, sum: 430, min: 70, max: 150, mean: 107.5 });
		assert.match(result.sha256, /^[a-f0-9]{64}$/);
	});
});

test("parses quoted commas, escaped quotes, and line breaks", () => {
	assert.deepEqual(parseCsv('name,note\r\n"North, A","said ""yes"""\r\n'), [
		["name", "note"],
		["North, A", 'said "yes"'],
	]);
});

test("preserves a final quoted empty field without a newline", () => {
	assert.deepEqual(parseCsv('value\n""'), [["value"], [""]]);
});

test("rejects finite cells whose sum overflows instead of emitting JSON null", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "overflow.csv"), "value\n1e308\n1e308\n");
		await expectCode(calculateWorkspaceCsvStats({ workspaceRoot, path: "overflow.csv", numericColumns: ["value"] }), "NUMERIC_OVERFLOW");
	});
});

test("special object property names remain ordinary numeric column data", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "special.csv"), "__proto__,constructor\n2,3\n4,5\n");
		const result = await calculateWorkspaceCsvStats({ workspaceRoot, path: "special.csv", numericColumns: ["__proto__", "constructor"] });
		const decoded = JSON.parse(JSON.stringify(result));
		assert.deepEqual(decoded.numeric.__proto__, { count: 2, missing: 0, sum: 6, min: 2, max: 4, mean: 3 });
		assert.deepEqual(decoded.numeric.constructor, { count: 2, missing: 0, sum: 8, min: 3, max: 5, mean: 4 });
		assert.equal(Object.getPrototypeOf(result.numeric), Object.prototype);
	});
});

test("rejects unexpected content after a quoted field", () => {
	assert.throws(
		() => parseCsv('name,value\n"alpha"extra,1\n'),
		(error) => error instanceof WorkspaceCsvStatsError && error.code === "INVALID_CSV",
	);
});

test("rejects absolute, parent, and escaping symlink paths", async () => {
	await withWorkspace(async ({ testRoot, workspaceRoot }) => {
		const outside = join(testRoot, "outside.csv");
		await writeFile(outside, "value\n1\n", "utf8");
		await symlink(outside, join(workspaceRoot, "escape.csv"));

		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "/tmp/a.csv", numericColumns: ["value"] }),
			"ABSOLUTE_PATH_DENIED",
		);
		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "../a.csv", numericColumns: ["value"] }),
			"PARENT_PATH_DENIED",
		);
		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "escape.csv", numericColumns: ["value"] }),
			"SYMLINK_ESCAPE_DENIED",
		);
	});
});

test("rejects malformed tables and duplicate headers", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "uneven.csv"), "a,b\n1\n", "utf8");
		await writeFile(join(workspaceRoot, "duplicate.csv"), "a,a\n1,2\n", "utf8");

		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "uneven.csv", numericColumns: ["a"] }),
			"INVALID_CSV",
		);
		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "duplicate.csv", numericColumns: ["a"] }),
			"INVALID_CSV",
		);
	});
});

test("rejects missing numeric columns and non-numeric cells", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "values.csv"), "label,value\na,not-a-number\n", "utf8");

		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "values.csv", numericColumns: ["missing"] }),
			"COLUMN_NOT_FOUND",
		);
		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "values.csv", numericColumns: ["value"] }),
			"NON_NUMERIC_VALUE",
		);
	});
});

test("rejects non-CSV, binary, and oversized files", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "values.txt"), "value\n1\n", "utf8");
		await writeFile(join(workspaceRoot, "binary.csv"), Buffer.from([0xff, 0xfe, 0x00]));
		await writeFile(join(workspaceRoot, "large.csv"), Buffer.alloc(WORKSPACE_CSV_MAX_FILE_BYTES + 1, 97));

		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "values.txt", numericColumns: ["value"] }),
			"FILE_TYPE_DENIED",
		);
		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "binary.csv", numericColumns: ["value"] }),
			"BINARY_FILE_DENIED",
		);
		await expectCode(
			calculateWorkspaceCsvStats({ workspaceRoot, path: "large.csv", numericColumns: ["value"] }),
			"FILE_TOO_LARGE",
		);
	});
});
