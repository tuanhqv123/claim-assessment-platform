/**
 * Typed fetch helpers for the Member Claim Submission + Document Upload flow
 * (Challenge 08 intake). All shapes follow ../docs/API_CONTRACT.md.
 *
 * This module is self-contained (does not touch the shared web/src/lib/api.ts).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Tenant + config shapes (mirror src/tenant/config_schema.py)
// ---------------------------------------------------------------------------

export interface CustomFieldSpec {
  key: string;
  label: string;
  type: string; // "text" | "number" | "date" | ... (free-form on the backend)
  required: boolean;
}

export interface DocumentRequirements {
  required: string[];
  optional: string[];
}

export interface ApprovalTier {
  min: number;
  max: number | null;
  role: string;
}

export interface NotificationRule {
  channels: string[];
}

export interface TenantConfig {
  branding: {
    company_name: string;
    logo_url?: string | null;
    primary_color?: string | null;
    secondary_color?: string | null;
  };
  claim_types: string[];
  documents: Record<string, DocumentRequirements>;
  auto_approval_threshold: number;
  approval_tiers: ApprovalTier[];
  notifications: Record<string, NotificationRule>;
  sla: Record<string, number>;
  custom_fields: CustomFieldSpec[];
}

export interface TenantSummary {
  id: string;
  slug: string;
  name: string;
  config_summary: {
    claim_types: string[];
    auto_approval_threshold: number;
  };
}

export interface ActiveConfigResponse {
  tenant_id: string;
  version: number;
  config: TenantConfig;
}

// ---------------------------------------------------------------------------
// Claim shapes
// ---------------------------------------------------------------------------

export interface CreateClaimInput {
  tenant_id: string;
  claim_number?: string;
  policy_number: string;
  member_id: string;
  claim_type: string;
  sub_benefit: string;
  diagnosis_code: string;
  diagnosis_description: string;
  procedure_codes: string[];
  amount: number;
  claim_date: string;
  provider: string;
  custom_fields: Record<string, unknown>;
  submitted_document_ids?: string[];
}

/** The created claim row (subset we rely on; backend may return more). */
export interface ClaimRow {
  id: string;
  tenant_id: string;
  claim_number: string;
  claim_type: string;
  amount: number;
  state: string;
  member_id: string | null;
  policy_id: string | null;
  sub_benefit: string | null;
  diagnosis_code: string | null;
  diagnosis_description: string | null;
  procedure_codes: string[];
  provider: string | null;
  claim_date: string | null;
  custom_fields: Record<string, unknown>;
  sla_deadline: string | null;
  created_at: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// OCR + document shapes (mirror src/ocr/pipeline.extract_document)
// ---------------------------------------------------------------------------

export type OcrDocumentType =
  | "receipt"
  | "discharge_summary"
  | "lab_report"
  | "prescription"
  | string;

export interface OcrField {
  value: unknown;
  confidence: number;
}

/**
 * A single OCR-detected region. `bbox` is `[x1, y1, x2, y2]` in the source
 * image's PIXEL coordinates (top-left origin).
 */
export interface OcrLayoutElement {
  bbox: [number, number, number, number];
  category: string;
  text?: string;
}

export interface OcrExtractResult {
  document_type: OcrDocumentType;
  confidence: number;
  fields: Record<string, OcrField>;
  validation_errors: string[];
  /** OCR-detected regions to overlay on the document preview. */
  layout?: OcrLayoutElement[];
  /** Natural pixel size of the source image: `[width, height]`. */
  image_size?: [number, number];
}

/** The persisted document row returned by POST /api/claims/{id}/documents. */
export interface DocumentRow {
  id: string;
  claim_id: string | null;
  tenant_id: string;
  document_type: string | null;
  file_name: string | null;
  storage_path: string | null;
  status: string;
  confidence: number | null;
  ocr_result: OcrExtractResult | null;
  issues: string[];
  created_at: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Runtime preview (required docs / approval routing / sla / notifications)
// ---------------------------------------------------------------------------

export interface ApprovalRouting {
  tier_role: string;
  auto_approved: boolean;
}

export interface CustomFieldValidation {
  required: string[];
  provided: Record<string, unknown>;
  valid: boolean;
  errors: string[];
}

export interface RuntimePreview {
  required_documents: string[];
  approval_routing: ApprovalRouting;
  notifications: Record<string, string[]>;
  sla_deadline: string;
  custom_fields: CustomFieldValidation;
}

// ---------------------------------------------------------------------------
// Document-completeness check (required-docs checklist)
// ---------------------------------------------------------------------------

export interface CheckDocumentsInput {
  tenant_id: string;
  claim_type: string;
  /** OCR-classified document_type of each uploaded doc, e.g. ["receipt"]. */
  uploaded_types: string[];
}

export interface CheckDocumentsResult {
  claim_type: string;
  required: string[];
  optional: string[];
  satisfied: string[];
  missing: string[];
  /** Uploaded types that don't map to any doc required/optional for this claim type. */
  mismatches: string[];
  complete: boolean;
}

// ---------------------------------------------------------------------------
// Error helper
// ---------------------------------------------------------------------------

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.errors && Array.isArray(body.errors)) {
        detail = body.errors.join("; ");
      } else if (body?.error) {
        detail = String(body.error);
      } else if (body?.detail) {
        // FastAPI may wrap our payload: {"detail": {"error": "..."}}.
        detail =
          typeof body.detail === "string"
            ? body.detail
            : body.detail.error || body.detail.message || JSON.stringify(body.detail);
      }
    } catch {
      // body was not JSON; keep status text
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export async function listTenants(): Promise<TenantSummary[]> {
  const res = await fetch(`${API_BASE}/api/tenants`, { cache: "no-store" });
  return unwrap<TenantSummary[]>(res);
}

export async function getActiveConfig(
  tenantId: string,
): Promise<ActiveConfigResponse> {
  const res = await fetch(`${API_BASE}/api/tenants/${tenantId}/config`, {
    cache: "no-store",
  });
  return unwrap<ActiveConfigResponse>(res);
}

export async function createClaim(input: CreateClaimInput): Promise<ClaimRow> {
  const res = await fetch(`${API_BASE}/api/claims`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return unwrap<ClaimRow>(res);
}

/** Stateless OCR preview of a single uploaded file (multipart `file`). */
export async function ocrExtract(file: File): Promise<OcrExtractResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/ocr/extract`, {
    method: "POST",
    body: form,
  });
  return unwrap<OcrExtractResult>(res);
}

export interface OcrStepEvent {
  event: "step";
  step: string;
  label?: string;
  status: "running" | "done";
  data?: Record<string, unknown>;
}

/**
 * Streaming OCR: calls `onStep` for each pipeline stage event
 * (ocr -> structure -> validate) as it happens, resolves with the final result.
 * Lets the UI show what the OCR model / LLM is doing live.
 */
export async function ocrExtractStream(
  file: File,
  onStep: (ev: OcrStepEvent) => void,
): Promise<OcrExtractResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/ocr/extract/stream`, {
    method: "POST",
    body: form,
  });
  if (!res.ok || !res.body) throw new Error(`OCR failed (${res.status})`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: OcrExtractResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      let obj: Record<string, unknown>;
      try {
        obj = JSON.parse(line.slice(5).trim());
      } catch {
        continue;
      }
      if (obj.event === "done") {
        result = obj.result as OcrExtractResult;
      } else if (obj.event === "error") {
        throw new Error(String(obj.message ?? "OCR error"));
      } else if (obj.event === "step") {
        onStep(obj as unknown as OcrStepEvent);
      }
    }
  }
  if (!result) throw new Error("OCR stream ended without a result");
  return result;
}

/** Attach (and OCR-persist) a document to an existing claim. */
export async function attachDocument(
  claimId: string,
  file: File,
): Promise<DocumentRow> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/claims/${claimId}/documents`, {
    method: "POST",
    body: form,
  });
  return unwrap<DocumentRow>(res);
}

/**
 * Run the tenant runtime over a draft claim to preview required documents,
 * approval routing, SLA deadline and notifications without persisting.
 * Used to render the post-submit confirmation payoff.
 */
export async function previewClaim(
  tenantId: string,
  claim: Record<string, unknown>,
): Promise<RuntimePreview> {
  const res = await fetch(`${API_BASE}/api/tenants/${tenantId}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ claim }),
  });
  return unwrap<RuntimePreview>(res);
}

/**
 * Check, for a given claim type, which required documents the member's uploaded
 * (OCR-classified) document types satisfy and which are still missing. Used to
 * render the live required-documents checklist + post-submit completeness view.
 */
export async function checkDocuments(
  body: CheckDocumentsInput,
): Promise<CheckDocumentsResult> {
  const res = await fetch(`${API_BASE}/api/documents/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return unwrap<CheckDocumentsResult>(res);
}

export { API_BASE };
