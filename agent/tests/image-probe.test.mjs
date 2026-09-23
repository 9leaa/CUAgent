import assert from "node:assert/strict";
import { inflateSync } from "node:zlib";
import test from "node:test";

import {
	createImageProbeResult,
	IMAGE_PROBE_HEIGHT,
	IMAGE_PROBE_WIDTH,
} from "../image-probe.mjs";

function pngChunks(buffer) {
	const chunks = [];
	let offset = 8;
	while (offset < buffer.length) {
		const length = buffer.readUInt32BE(offset);
		const type = buffer.subarray(offset + 4, offset + 8).toString("ascii");
		chunks.push({ type, data: buffer.subarray(offset + 8, offset + 8 + length) });
		offset += 12 + length;
	}
	return chunks;
}

test("creates a deterministic valid PNG tool payload", () => {
	const first = createImageProbeResult();
	const second = createImageProbeResult();

	assert.equal(first.mimeType, "image/png");
	assert.equal(first.data, second.data);
	assert.equal(first.sha256, second.sha256);
	assert.match(first.sha256, /^[a-f0-9]{64}$/);
	assert.deepEqual(first.png.subarray(0, 8), Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));

	const chunks = pngChunks(first.png);
	const header = chunks.find((chunk) => chunk.type === "IHDR").data;
	assert.equal(header.readUInt32BE(0), IMAGE_PROBE_WIDTH);
	assert.equal(header.readUInt32BE(4), IMAGE_PROBE_HEIGHT);
	assert.deepEqual(chunks.map((chunk) => chunk.type), ["IHDR", "IDAT", "IEND"]);
});

test("encodes four independently checked quadrant colors", () => {
	const result = createImageProbeResult();
	const chunks = pngChunks(result.png);
	const raw = inflateSync(Buffer.concat(chunks.filter((chunk) => chunk.type === "IDAT").map((chunk) => chunk.data)));
	const stride = IMAGE_PROBE_WIDTH * 4 + 1;
	const pixel = (x, y) => [...raw.subarray(y * stride + 1 + x * 4, y * stride + 1 + x * 4 + 4)];

	assert.deepEqual(pixel(10, 10), [255, 0, 0, 255]);
	assert.deepEqual(pixel(80, 10), [0, 0, 255, 255]);
	assert.deepEqual(pixel(10, 50), [0, 255, 0, 255]);
	assert.deepEqual(pixel(80, 50), [255, 255, 0, 255]);
});
