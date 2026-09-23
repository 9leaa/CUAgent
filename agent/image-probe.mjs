import { createHash } from "node:crypto";
import { deflateSync } from "node:zlib";

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
