/**
 * Maps an OCR extraction result to a partial prefill for the member claim form.
 *
 * Only fields that can be confidently derived from the document are returned;
 * the member still fills policy/member/claim_type/sub_benefit/etc. by hand.
 * Every accessor is defensive — OCR output may be missing or oddly shaped.
 */

import type { OcrExtractResult } from "@/lib/memberApi";

export interface ClaimPrefill {
  provider?: string;
  amount?: number;
  claim_date?: string;
  diagnosis_description?: string;
  diagnosis_code?: string;
  procedure_codes?: string; // comma-joined, matches the form field
}

/** ICD-10 looking code, e.g. "J06" or "S52.5". */
const ICD10_RE = /[A-Z]\d{2}(?:\.\d+)?/;
/** CPT looking code: a standalone 5-digit number. */
const CPT_RE = /\b\d{5}\b/g;

const MONTHS: Record<string, number> = {
  jan: 1, january: 1,
  feb: 2, february: 2,
  mar: 3, march: 3,
  apr: 4, april: 4,
  may: 5,
  jun: 6, june: 6,
  jul: 7, july: 7,
  aug: 8, august: 8,
  sep: 9, sept: 9, september: 9,
  oct: 10, october: 10,
  nov: 11, november: 11,
  dec: 12, december: 12,
};

/** Read a top-level OCR field's `.value`, or undefined if absent/null. */
function fieldValue(result: OcrExtractResult, key: string): unknown {
  const field = result?.fields?.[key];
  if (!field) return undefined;
  const v = field.value;
  return v === null || v === undefined ? undefined : v;
}

function asString(v: unknown): string | undefined {
  if (typeof v === "string") {
    const t = v.trim();
    return t ? t : undefined;
  }
  if (typeof v === "number" && Number.isFinite(v)) return String(v);
  return undefined;
}

function asNumber(v: unknown): number | undefined {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string") {
    // Strip currency symbols / thousands separators, keep digits + dot/minus.
    const cleaned = v.replace(/[^0-9.\-]/g, "");
    if (!cleaned) return undefined;
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : undefined;
  }
  return undefined;
}

const pad = (n: number) => String(n).padStart(2, "0");

/**
 * Normalize a date string to YYYY-MM-DD when recognizable; otherwise return the
 * raw (trimmed) string so the member can fix it rather than lose the value.
 * Accepts: YYYY-MM-DD, DD/MM/YYYY (or DD-MM-YYYY), "15 March 2024",
 * "March 15, 2024".
 */
function normalizeDate(raw: unknown): string | undefined {
  const s = asString(raw);
  if (!s) return undefined;

  // Already YYYY-MM-DD (allow any separator), keep as-is normalized.
  let m = s.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/);
  if (m) {
    return `${m[1]}-${pad(Number(m[2]))}-${pad(Number(m[3]))}`;
  }

  // DD/MM/YYYY or DD-MM-YYYY (assume day-first, matching the brief).
  m = s.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$/);
  if (m) {
    return `${m[3]}-${pad(Number(m[2]))}-${pad(Number(m[1]))}`;
  }

  // "15 March 2024" / "15 Mar 2024".
  m = s.match(/^(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})$/);
  if (m) {
    const mon = MONTHS[m[2].toLowerCase()];
    if (mon) return `${m[3]}-${pad(mon)}-${pad(Number(m[1]))}`;
  }

  // "March 15, 2024" / "Mar 15 2024".
  m = s.match(/^([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})$/);
  if (m) {
    const mon = MONTHS[m[1].toLowerCase()];
    if (mon) return `${m[3]}-${pad(mon)}-${pad(Number(m[2]))}`;
  }

  // Unparseable: pass the raw value through.
  return s;
}

/** Pull a human-readable string out of a diagnosis field that may be an object. */
function diagnosisPrimaryText(result: OcrExtractResult): string | undefined {
  const v = fieldValue(result, "diagnosis");
  if (typeof v === "object" && v !== null) {
    const primary = (v as Record<string, unknown>).primary;
    return asString(primary);
  }
  return asString(v);
}

/** Pull procedures text whether stored as a string or an array of values. */
function proceduresText(result: OcrExtractResult): string | undefined {
  const v = fieldValue(result, "procedures_performed");
  if (Array.isArray(v)) {
    const joined = v
      .map((item) => {
        if (typeof item === "object" && item !== null) {
          const rec = item as Record<string, unknown>;
          return asString(rec.code ?? rec.name ?? rec.description) ?? "";
        }
        return asString(item) ?? "";
      })
      .filter(Boolean)
      .join(" ");
    return joined || undefined;
  }
  return asString(v);
}

export function deriveClaimPrefill(result: OcrExtractResult): ClaimPrefill {
  const prefill: ClaimPrefill = {};
  if (!result || typeof result !== "object") return prefill;

  const docType = result.document_type;

  switch (docType) {
    case "receipt": {
      const provider = asString(fieldValue(result, "hospital_name"));
      if (provider) prefill.provider = provider;

      // Insurance focus: prefer the insurer-paid amount, then the total cost.
      const amount =
        asNumber(fieldValue(result, "insurance_paid")) ??
        asNumber(fieldValue(result, "total_cost")) ??
        asNumber(fieldValue(result, "grand_total"));
      if (amount !== undefined) prefill.amount = amount;

      const date = normalizeDate(fieldValue(result, "date"));
      if (date) prefill.claim_date = date;
      break;
    }

    case "discharge_summary": {
      const provider = asString(fieldValue(result, "hospital_name"));
      if (provider) prefill.provider = provider;

      const date =
        normalizeDate(fieldValue(result, "discharge_date")) ??
        normalizeDate(fieldValue(result, "admission_date"));
      if (date) prefill.claim_date = date;

      const diagText = diagnosisPrimaryText(result);
      if (diagText) {
        prefill.diagnosis_description = diagText;
        const icd = diagText.match(ICD10_RE);
        if (icd) prefill.diagnosis_code = icd[0];
      }

      const procText = proceduresText(result);
      if (procText) {
        const cpts = procText.match(CPT_RE);
        if (cpts && cpts.length > 0) {
          prefill.procedure_codes = cpts.join(", ");
        }
      }
      break;
    }

    case "lab_report": {
      const provider = asString(fieldValue(result, "lab_name"));
      if (provider) prefill.provider = provider;

      const date = normalizeDate(fieldValue(result, "date"));
      if (date) prefill.claim_date = date;
      break;
    }

    case "prescription": {
      const provider = asString(fieldValue(result, "doctor_name"));
      if (provider) prefill.provider = provider;

      const date = normalizeDate(fieldValue(result, "date"));
      if (date) prefill.claim_date = date;
      break;
    }

    default:
      break;
  }

  return prefill;
}
