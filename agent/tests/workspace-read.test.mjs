import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
	readWorkspaceFile,
	WORKSPACE_READ_MAX_FILE_BYTES,
	WORKSPACE_READ_MAX_OUTPUT_BYTES,
	WorkspaceReadError,
} from "../workspace-read.mjs";

async function withWorkspace(run) {
	const testRoot = await mkdtemp(join(tmpdir(), "osagent-workspace-read-"));
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
		assert.ok(error instanceof WorkspaceReadError);
		assert.equal(error.code, code);
		return true;
	});
}

test("reads an allowed UTF-8 text file with verification metadata", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "notes.txt"), "alpha\nbeta\ngamma", "utf8");

		const result = await readWorkspaceFile({ workspaceRoot, path: "notes.txt" });

		assert.equal(result.content, "alpha\nbeta\ngamma");
		assert.equal(result.totalLines, 3);
		assert.equal(result.truncated, false);
		assert.equal(result.bytes, 16);
		assert.match(result.sha256, /^[a-f0-9]{64}$/);
	});
});

test("returns a bounded line range", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "notes.md"), "one\ntwo\nthree\nfour", "utf8");

		const result = await readWorkspaceFile({
			workspaceRoot,
			path: "notes.md",
			startLine: 2,
			maxLines: 2,
		});

		assert.equal(result.content, "two\nthree");
		assert.equal(result.startLine, 2);
		assert.equal(result.endLine, 3);
		assert.equal(result.totalLines, 4);
		assert.equal(result.truncated, true);
	});
});

test("reduces the returned line range to the output byte limit", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		const line = "x".repeat(30 * 1024);
		await writeFile(join(workspaceRoot, "long.txt"), `${line}\n${line}\n${line}`, "utf8");

		const result = await readWorkspaceFile({ workspaceRoot, path: "long.txt" });

		assert.equal(result.endLine, 2);
		assert.equal(result.truncated, true);
		assert.ok(Buffer.byteLength(result.content, "utf8") <= WORKSPACE_READ_MAX_OUTPUT_BYTES);
	});
});

test("rejects absolute and parent paths", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await expectCode(readWorkspaceFile({ workspaceRoot, path: "/tmp/a.txt" }), "ABSOLUTE_PATH_DENIED");
		await expectCode(readWorkspaceFile({ workspaceRoot, path: "../a.txt" }), "PARENT_PATH_DENIED");
	});
});

test("rejects disallowed extensions and binary content", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "script.sh"), "echo unsafe", "utf8");
		await writeFile(join(workspaceRoot, "binary.txt"), Buffer.from([0xff, 0xfe, 0x00]));

		await expectCode(readWorkspaceFile({ workspaceRoot, path: "script.sh" }), "FILE_TYPE_DENIED");
		await expectCode(readWorkspaceFile({ workspaceRoot, path: "binary.txt" }), "BINARY_FILE_DENIED");
	});
});

test("rejects oversized files", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await writeFile(join(workspaceRoot, "large.txt"), Buffer.alloc(WORKSPACE_READ_MAX_FILE_BYTES + 1, 97));

		await expectCode(readWorkspaceFile({ workspaceRoot, path: "large.txt" }), "FILE_TOO_LARGE");
	});
});

test("rejects symlink escapes but allows internal symlinks", async () => {
	await withWorkspace(async ({ testRoot, workspaceRoot }) => {
		const outside = join(testRoot, "outside.txt");
		await writeFile(outside, "outside", "utf8");
		await writeFile(join(workspaceRoot, "inside.txt"), "inside", "utf8");
		await symlink(outside, join(workspaceRoot, "escape.txt"));
		await symlink(join(workspaceRoot, "inside.txt"), join(workspaceRoot, "alias.txt"));

		await expectCode(readWorkspaceFile({ workspaceRoot, path: "escape.txt" }), "SYMLINK_ESCAPE_DENIED");
		const result = await readWorkspaceFile({ workspaceRoot, path: "alias.txt" });
		assert.equal(result.content, "inside");
	});
});

test("rejects directories and invalid line ranges", async () => {
	await withWorkspace(async ({ workspaceRoot }) => {
		await mkdir(join(workspaceRoot, "folder"));
		await writeFile(join(workspaceRoot, "short.json"), "{}", "utf8");

		await expectCode(readWorkspaceFile({ workspaceRoot, path: "folder" }), "NOT_A_FILE");
		await expectCode(
			readWorkspaceFile({ workspaceRoot, path: "short.json", startLine: 3 }),
			"INVALID_RANGE",
		);
	});
});
