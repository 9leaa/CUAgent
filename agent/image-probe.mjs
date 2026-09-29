import { createHash } from "node:crypto";
import { deflateSync, inflateSync } from "node:zlib";

export const IMAGE_PROBE_WIDTH = 96;
export const IMAGE_PROBE_HEIGHT = 64;

const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

function crc32(buffer) {
	let crc = 0xffffffff;
	for (const byte of buffer) {
		crc ^= byte;
		for (let bit = 0; bit < 8; bit += 1) {
			crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
		}
	}
	return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
	const typeBuffer = Buffer.from(type, "ascii");
	const length = Buffer.alloc(4);
	length.writeUInt32BE(data.length);
	const checksum = Buffer.alloc(4);
	checksum.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])));
	return Buffer.concat([length, typeBuffer, data, checksum]);
}

export function createImageProbePng() {
	const stride = IMAGE_PROBE_WIDTH * 4 + 1;
	const pixels = Buffer.alloc(stride * IMAGE_PROBE_HEIGHT);
	for (let y = 0; y < IMAGE_PROBE_HEIGHT; y += 1) {
		const rowOffset = y * stride;
		pixels[rowOffset] = 0;
		for (let x = 0; x < IMAGE_PROBE_WIDTH; x += 1) {
			const pixelOffset = rowOffset + 1 + x * 4;
			const left = x < IMAGE_PROBE_WIDTH / 2;
			const top = y < IMAGE_PROBE_HEIGHT / 2;
			const color = top ? (left ? [255, 0, 0] : [0, 0, 255]) : left ? [0, 255, 0] : [255, 255, 0];
			pixels[pixelOffset] = color[0];
			pixels[pixelOffset + 1] = color[1];
			pixels[pixelOffset + 2] = color[2];
			pixels[pixelOffset + 3] = 255;
		}
	}

	const header = Buffer.alloc(13);
	header.writeUInt32BE(IMAGE_PROBE_WIDTH, 0);
	header.writeUInt32BE(IMAGE_PROBE_HEIGHT, 4);
	header[8] = 8;
	header[9] = 6;
	return Buffer.concat([
		PNG_SIGNATURE,
		pngChunk("IHDR", header),
		pngChunk("IDAT", deflateSync(pixels)),
		pngChunk("IEND", Buffer.alloc(0)),
	]);
}

/**
 * The four quadrant colours, keyed by position. Colour names are the labels a
 * verifier compares against; RGB values are what the encoder writes.
 */
export const IMAGE_PROBE_COLORS = Object.freeze({
	red: Object.freeze([255, 0, 0]),
	blue: Object.freeze([0, 0, 255]),
	green: Object.freeze([0, 255, 0]),
	yellow: Object.freeze([255, 255, 0]),
});

/** Quadrant order as reported by a caller: top-left, top-right, bottom-left, bottom-right. */
export const IMAGE_PROBE_POSITIONS = Object.freeze(["top-left", "top-right", "bottom-left", "bottom-right"]);

const COLOR_NAMES = Object.freeze(Object.keys(IMAGE_PROBE_COLORS));

/**
 * Encode a probe PNG from an explicit position→colour-name assignment.
 *
 * The assignment is a parameter rather than internal randomness so the encoder
 * stays deterministic and testable, and so the caller that holds the answer can
 * keep it away from the model.
 * @param {Record<string, string>} assignment - position name to colour name.
 * @returns {Buffer} the PNG bytes.
 */
export function createImageProbePngFor(assignment) {
	const stride = IMAGE_PROBE_WIDTH * 4 + 1;
	const pixels = Buffer.alloc(stride * IMAGE_PROBE_HEIGHT);
	for (const position of IMAGE_PROBE_POSITIONS) {
		const colorName = assignment[position];
		if (!Object.hasOwn(IMAGE_PROBE_COLORS, colorName ?? "")) {
			throw new Error(`unsupported colour for ${position}: ${String(colorName)}`);
		}
	}
	for (let y = 0; y < IMAGE_PROBE_HEIGHT; y += 1) {
		const rowOffset = y * stride;
		pixels[rowOffset] = 0;
		for (let x = 0; x < IMAGE_PROBE_WIDTH; x += 1) {
			const pixelOffset = rowOffset + 1 + x * 4;
			const left = x < IMAGE_PROBE_WIDTH / 2;
			const top = y < IMAGE_PROBE_HEIGHT / 2;
			const position = top ? (left ? "top-left" : "top-right") : left ? "bottom-left" : "bottom-right";
			const color = IMAGE_PROBE_COLORS[assignment[position]];
			pixels[pixelOffset] = color[0];
			pixels[pixelOffset + 1] = color[1];
			pixels[pixelOffset + 2] = color[2];
			pixels[pixelOffset + 3] = 255;
		}
	}

	const header = Buffer.alloc(13);
	header.writeUInt32BE(IMAGE_PROBE_WIDTH, 0);
	header.writeUInt32BE(IMAGE_PROBE_HEIGHT, 4);
	header[8] = 8;
	header[9] = 6;
	return Buffer.concat([
		PNG_SIGNATURE,
		pngChunk("IHDR", header),
		pngChunk("IDAT", deflateSync(pixels)),
		pngChunk("IEND", Buffer.alloc(0)),
	]);
}

/**
 * Draw a fresh random assignment: the four colours are placed in the four
 * quadrants in a uniformly random order, so no fixed position→colour mapping
 * can be guessed or memorised.
 * @param {() => number} [random] - injectable RNG returning [0, 1); defaults to Math.random.
 * @returns {Record<string, string>} position name to colour name.
 */
export function createRandomImageProbeAssignment(random = Math.random) {
	const pool = [...COLOR_NAMES];
	for (let index = pool.length - 1; index > 0; index -= 1) {
		const swap = Math.floor(random() * (index + 1));
		[pool[index], pool[swap]] = [pool[swap], pool[index]];
	}
	return Object.fromEntries(IMAGE_PROBE_POSITIONS.map((position, index) => [position, pool[index]]));
}

/**
 * Read back the quadrant colour names actually encoded in a probe PNG, by
 * decoding and sampling one interior pixel per quadrant.
 *
 * This is the independent check: it reads the produced bytes, not the
 * assignment that was intended.
 * @param {Buffer} png - the PNG bytes to inspect.
 * @returns {Record<string, string>} position name to colour name.
 */
export function readImageProbeAssignment(png) {
	const chunks = [];
	let offset = 8;
	while (offset < png.length) {
		const length = png.readUInt32BE(offset);
		const type = png.subarray(offset + 4, offset + 8).toString("ascii");
		if (type === "IDAT") chunks.push(png.subarray(offset + 8, offset + 8 + length));
		offset += 12 + length;
	}
	const raw = inflateSync(Buffer.concat(chunks));
	const stride = IMAGE_PROBE_WIDTH * 4 + 1;
	const sample = (x, y) => [raw[y * stride + 1 + x * 4], raw[y * stride + 1 + x * 4 + 1], raw[y * stride + 1 + x * 4 + 2]];
	const points = [["top-left", 10, 10], ["top-right", 80, 10], ["bottom-left", 10, 50], ["bottom-right", 80, 50]];
	const result = {};
	for (const [position, x, y] of points) {
		const rgb = sample(x, y);
		const match = COLOR_NAMES.find((name) => IMAGE_PROBE_COLORS[name].every((channel, index) => channel === rgb[index]));
		if (match === undefined) throw new Error(`unrecognised colour at ${position}: ${rgb.join(",")}`);
		result[position] = match;
	}
	return result;
}

export function createImageProbeResult() {
	const png = createImageProbePng();
	return {
		png,
		data: png.toString("base64"),
		mimeType: "image/png",
		width: IMAGE_PROBE_WIDTH,
		height: IMAGE_PROBE_HEIGHT,
		sha256: createHash("sha256").update(png).digest("hex"),
	};
}
