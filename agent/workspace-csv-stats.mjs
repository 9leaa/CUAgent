import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

import {
	resolveExistingWorkspacePath,
	WorkspacePathError,
	workspaceDisplayPath,
} from "./workspace-path.mjs";

export const WORKSPACE_CSV_MAX_FILE_BYTES = 1024 * 1024;
export const WORKSPACE_CSV_MAX_ROWS = 10000;
export const WORKSPACE_CSV_MAX_COLUMNS = 100;
export const WORKSPACE_CSV_MAX_NUMERIC_COLUMNS = 20;

export { WorkspacePathError as WorkspaceCsvStatsError };

export function parseCsv(text) {
	if (typeof text !== "string" || text.length === 0) {
		throw new WorkspacePathError("EMPTY_CSV", "CSV file is empty");
	}

	const rows = [];
	let row = [];
	let field = "";
	let inQuotes = false;
	let quotedFieldClosed = false;

	for (let index = 0; index < text.length; index += 1) {
		const character = text[index];
		if (inQuotes) {
			if (character === '"') {
				if (text[index + 1] === '"') {
					field += '"';
					index += 1;
				} else {
					inQuotes = false;
					quotedFieldClosed = true;
				}
			} else {
				field += character;
			}
			continue;
		}

		if (quotedFieldClosed && character !== "," && character !== "\n" && character !== "\r") {
			throw new WorkspacePathError("INVALID_CSV", "unexpected content after a quoted field");
		}
		if (character === '"') {
			if (field.length !== 0) {
				throw new WorkspacePathError("INVALID_CSV", "quote must start at the beginning of a field");
			}
			inQuotes = true;
		} else if (character === ",") {
			row.push(field);
			field = "";
			quotedFieldClosed = false;
		} else if (character === "\n" || character === "\r") {
			row.push(field);
			rows.push(row);
			row = [];
			field = "";
			quotedFieldClosed = false;
			if (character === "\r" && text[index + 1] === "\n") index += 1;
		} else {
			field += character;
		}
	}

	if (inQuotes) throw new WorkspacePathError("INVALID_CSV", "CSV contains an unterminated quoted field");
	if (field.length > 0 || row.length > 0 || quotedFieldClosed) {
		row.push(field);
		rows.push(row);
	}
	if (rows.length === 0) throw new WorkspacePathError("EMPTY_CSV", "CSV file is empty");
	return rows;
}

function validateTable(rows) {
	const headers = rows[0];
	if (headers.length === 0 || headers.length > WORKSPACE_CSV_MAX_COLUMNS) {
		throw new WorkspacePathError("INVALID_CSV", `CSV must contain 1 to ${WORKSPACE_CSV_MAX_COLUMNS} columns`);
	}
	if (headers.some((header) => header.length === 0)) {
		throw new WorkspacePathError("INVALID_CSV", "CSV headers must not be empty");
	}
	if (new Set(headers).size !== headers.length) {
		throw new WorkspacePathError("INVALID_CSV", "CSV headers must be unique");
	}

	const dataRows = rows.slice(1);
	if (dataRows.length > WORKSPACE_CSV_MAX_ROWS) {
		throw new WorkspacePathError("CSV_TOO_MANY_ROWS", `CSV exceeds ${WORKSPACE_CSV_MAX_ROWS} data rows`);
	}
	for (let index = 0; index < dataRows.length; index += 1) {
		if (dataRows[index].length !== headers.length) {
			throw new WorkspacePathError(
				"INVALID_CSV",
				`row ${index + 2} has ${dataRows[index].length} fields; expected ${headers.length}`,
			);
		}
	}
	return { headers, dataRows };
}

function validateNumericColumns(value, headers) {
	if (!Array.isArray(value) || value.length < 1 || value.length > WORKSPACE_CSV_MAX_NUMERIC_COLUMNS) {
		throw new WorkspacePathError(
			"INVALID_COLUMNS",
			`numericColumns must contain 1 to ${WORKSPACE_CSV_MAX_NUMERIC_COLUMNS} column names`,
		);
	}
	if (value.some((column) => typeof column !== "string" || column.length === 0)) {
		throw new WorkspacePathError("INVALID_COLUMNS", "numeric column names must be non-empty strings");
	}
	if (new Set(value).size !== value.length) {
		throw new WorkspacePathError("INVALID_COLUMNS", "numeric column names must be unique");
	}
	for (const column of value) {
		if (!headers.includes(column)) {
			throw new WorkspacePathError("COLUMN_NOT_FOUND", `numeric column not found: ${column}`);
		}
	}
	return value;
}

function parseNumericCell(value, column, rowNumber) {
	const trimmed = value.trim();
	if (trimmed === "") return null;
	if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) {
		throw new WorkspacePathError("NON_NUMERIC_VALUE", `column ${column} contains a non-numeric value at row ${rowNumber}`);
	}
	const numeric = Number(trimmed);
	if (!Number.isFinite(numeric)) {
		throw new WorkspacePathError("NON_NUMERIC_VALUE", `column ${column} contains a non-finite value at row ${rowNumber}`);
	}
	return numeric;
}

export async function calculateWorkspaceCsvStats({ workspaceRoot, path, numericColumns }) {
	const { canonicalTarget, requestedPath, targetStat } = await resolveExistingWorkspacePath({
		workspaceRoot,
		path,
		kind: "file",
	});
	if (!canonicalTarget.toLowerCase().endsWith(".csv")) {
		throw new WorkspacePathError("FILE_TYPE_DENIED", "only .csv files are allowed");
	}
	if (targetStat.size > WORKSPACE_CSV_MAX_FILE_BYTES) {
		throw new WorkspacePathError("FILE_TOO_LARGE", `CSV exceeds ${WORKSPACE_CSV_MAX_FILE_BYTES} bytes`);
	}

	let buffer;
	try {
		buffer = await readFile(canonicalTarget);
	} catch {
		throw new WorkspacePathError("UNAVAILABLE", `file is unavailable: ${workspaceDisplayPath(requestedPath)}`);
	}
	if (buffer.length > WORKSPACE_CSV_MAX_FILE_BYTES) {
		throw new WorkspacePathError("FILE_TOO_LARGE", `CSV exceeds ${WORKSPACE_CSV_MAX_FILE_BYTES} bytes`);
	}

	let text;
	try {
		text = new TextDecoder("utf-8", { fatal: true }).decode(buffer);
	} catch {
		throw new WorkspacePathError("BINARY_FILE_DENIED", "CSV is not valid UTF-8 text");
	}
	if (text.includes("\0")) throw new WorkspacePathError("BINARY_FILE_DENIED", "CSV contains null bytes");

	const { headers, dataRows } = validateTable(parseCsv(text));
	const selectedColumns = validateNumericColumns(numericColumns, headers);
	const numeric = {};
	for (const column of selectedColumns) {
		const columnIndex = headers.indexOf(column);
		const values = [];
		for (let rowIndex = 0; rowIndex < dataRows.length; rowIndex += 1) {
			const value = parseNumericCell(dataRows[rowIndex][columnIndex], column, rowIndex + 2);
			if (value !== null) values.push(value);
		}
		const sum = values.reduce((total, value) => total + value, 0);
		if (!Number.isFinite(sum)) {
			throw new WorkspacePathError("NUMERIC_OVERFLOW", `column ${column} aggregate exceeds finite numeric range`);
		}
		// CSV headers are data, including special JavaScript property names.
		Object.defineProperty(numeric, column, { enumerable: true, configurable: true, writable: true, value: {
			count: values.length,
			missing: dataRows.length - values.length,
			sum,
			min: values.length === 0 ? null : Math.min(...values),
			max: values.length === 0 ? null : Math.max(...values),
			mean: values.length === 0 ? null : sum / values.length,
		} });
	}

	return {
		path: workspaceDisplayPath(requestedPath),
		rowCount: dataRows.length,
		columnCount: headers.length,
		columns: headers,
		numeric,
		bytes: buffer.length,
		sha256: createHash("sha256").update(buffer).digest("hex"),
	};
}
