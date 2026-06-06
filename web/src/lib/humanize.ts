/**
 * Human-readable rendering of arbitrary (often nested) JSON values coming from
 * OCR extraction. Turns objects/arrays into "Label: value" text with humanized
 * keys (snake_case / camelCase -> spaced words), numbers with thousand
 * separators, comma-separated pairs inside an object, and pipe-separated items
 * across an array of objects.
 */

/** "unit_price" / "unitPrice" -> "Unit price". */
export function humanizeKey(key: string): string {
  return key
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2") // camelCase boundary
    .replace(/[_-]+/g, " ") // snake / kebab
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase()
    .replace(/^./, (c) => c.toUpperCase());
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

const EMPTY = (v: unknown) => v === null || v === undefined || v === "";

/**
 * Render a value as readable text.
 * - primitives: string as-is; numbers with thousand separators; booleans Yes/No
 * - object: `Key: val, Key: val` (humanized keys)
 * - array of primitives: `a, b, c`
 * - array of objects: each item on its OWN LINE (newline-separated):
 *     `Key: val, Key: val\nKey: val, Key: val`
 *   Render these in a container with `white-space: pre-line` to show the breaks.
 */
export function humanizeValue(value: unknown): string {
  if (EMPTY(value)) return "—";
  if (typeof value === "number") {
    return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string") {
    // Humanize pure snake_case identifiers (discharge_summary -> "Discharge
    // summary") but leave free text and codes (POL-003, 02/11/2023, "Bangkok
    // Hospital", K35.80) untouched.
    if (/^[a-z0-9]+(_[a-z0-9]+)+$/.test(value)) return humanizeKey(value);
    return value;
  }

  if (Array.isArray(value)) {
    const parts = value.filter((v) => !EMPTY(v)).map((v) => humanizeValue(v));
    const hasObjects = value.some((v) => isPlainObject(v) || Array.isArray(v));
    // Multiple objects -> one per line; primitives -> comma-separated.
    return parts.join(hasObjects ? "\n" : ", ");
  }

  if (isPlainObject(value)) {
    return Object.entries(value)
      .filter(([, v]) => !EMPTY(v))
      .map(([k, v]) => `${humanizeKey(k)}: ${humanizeValue(v)}`)
      .join(", ");
  }

  return String(value);
}
