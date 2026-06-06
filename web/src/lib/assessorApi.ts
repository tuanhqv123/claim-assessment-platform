import type { AssessmentReport, ToolCallEntry } from "@/types";
import type { Recommendation } from "@/constants";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---- Roles & states (mirror backend enums / API_CONTRACT.md) ----
export const ROLES = [
  "document_clerk",
  "assessor",
  "team_lead",
  "manager",
  "director",
  "committee",
  "finance",
  "admin",
] as const;
export type Role = (typeof ROLES)[number];

export const CLAIM_STATES = [
  "SUBMITTED",
  "DOCUMENTS_VERIFIED",
  "UNDER_ASSESSMENT",
  "PENDING_INFO",
  "APPROVED",
  "REJECTED",
  "PAYMENT_INITIATED",
  "CLOSED",
] as const;
export type ClaimState = (typeof CLAIM_STATES)[number];

// ---- Wire types ----
export interface ClaimListItem {
  id: string;
  claim_number: string;
  tenant_id: string;
  claim_type: string;
  amount: number;
  state: ClaimState;
  member_id: string | null;
  created_at: string;
}

export interface ClaimRow {
  id: string;
  claim_number: string;
  tenant_id: string;
  policy_id: string | null;
  member_id: string | null;
  claim_type: string;
  sub_benefit: string | null;
  diagnosis_code: string | null;
  diagnosis_description: string | null;
  procedure_codes: string[];
  amount: number;
  claim_date: string | null;
  provider: string | null;
  state: ClaimState;
  sla_deadline: string | null;
  custom_fields: Record<string, unknown>;
  info_request_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentRow {
  id: string;
  claim_id: string | null;
  tenant_id: string;
  file_name: string | null;
  document_type: string | null;
  status: string;
  confidence: number | null;
  issues: string[];
  ocr_result: Record<string, unknown> | null;
  storage_path: string | null;
  /** Public URL of the stored file (Supabase Storage), when available. */
  file_url?: string | null;
  created_at: string;
}

export interface TransitionAuditEntry {
  id: number | string;
  claim_id: string;
  from_state: ClaimState | null;
  to_state: ClaimState;
  triggered_by: string | null;
  triggered_by_role: Role | null;
  reason: string | null;
  notes: string | null;
  side_effects: Record<string, unknown> | unknown[] | null;
  created_at: string;
}

export interface AvailableTransition {
  to: ClaimState;
  role: Role | string;
  preconditions?: string[];
}

export interface AssessmentRecord {
  id?: string;
  recommendation: Recommendation | null;
  recommendation_reason: string | null;
  report: AssessmentReport | null;
  tool_call_log: ToolCallEntry[] | null;
  guard_flags: GuardFlags | null;
  created_at?: string;
}

export type GuardFlags =
  | Record<string, unknown>
  | unknown[]
  | null;

export interface ClaimDetail {
  claim: ClaimRow;
  documents: DocumentRow[];
  assessment: AssessmentRecord | null;
  transitions: TransitionAuditEntry[];
  available_transitions: AvailableTransition[];
}

export interface AssessResponse {
  recommendation: Recommendation;
  recommendation_reason: string;
  report: AssessmentReport;
  tool_call_log: ToolCallEntry[];
  guard_flags: GuardFlags;
}

export interface TransitionsResponse {
  current_state: ClaimState;
  audit: TransitionAuditEntry[];
  available: AvailableTransition[];
}

export interface TransitionRequest {
  to_state: ClaimState;
  reason?: string;
  notes?: string;
  context?: Record<string, unknown>;
}

export interface TransitionResponse {
  state: ClaimState;
  audit_entry: TransitionAuditEntry;
}

/** Error carrying the backend's specific message (e.g. unauthorized role). */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(res: Response): Promise<never> {
  let message = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    // Possible shapes:
    //   {"error": "..."}                     (this contract)
    //   {"detail": {"error": "..."}}         (FastAPI wraps our HTTPException detail)
    //   {"detail": "..."}                    (plain FastAPI)
    //   {"message": "..."}
    const detail = body?.detail;
    const fromDetail =
      detail && typeof detail === "object"
        ? detail.error || detail.message
        : detail;
    message = body?.error || fromDetail || body?.message || message;
    if (typeof message !== "string") message = JSON.stringify(message);
  } catch {
    // non-JSON body — keep default
  }
  throw new ApiError(message, res.status);
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) return parseError(res);
  return res.json() as Promise<T>;
}

// ---- Endpoints ----

export async function listClaims(params: {
  tenantId?: string;
  state?: ClaimState | "";
} = {}): Promise<ClaimListItem[]> {
  const qs = new URLSearchParams();
  if (params.tenantId) qs.set("tenant_id", params.tenantId);
  if (params.state) qs.set("state", params.state);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return getJson<ClaimListItem[]>(`/api/claims${suffix}`);
}

export async function getClaim(id: string): Promise<ClaimDetail> {
  return getJson<ClaimDetail>(`/api/claims/${id}`);
}

export async function runAssessment(id: string): Promise<AssessResponse> {
  const res = await fetch(`${API_BASE}/api/claims/${id}/assess`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
  });
  if (!res.ok) return parseError(res);
  return res.json() as Promise<AssessResponse>;
}

/** One tool-call step emitted by the streaming assessor. */
export interface AssessStepEvent {
  tool: string;
  data?: Record<string, unknown>;
}

interface AssessSseEvent {
  event: "step" | "done" | "error";
  tool?: string;
  data?: Record<string, unknown>;
  result?: AssessResponse;
  message?: string;
}

/**
 * Run the agent assessment, streaming each tool call live via SSE.
 * `onStep` fires once per tool as the agent runs; the promise resolves with the
 * final guarded result on `done`, or rejects on `error`.
 */
export async function runAssessmentStream(
  claimId: string,
  onStep: (ev: AssessStepEvent) => void,
): Promise<AssessResponse> {
  const res = await fetch(`${API_BASE}/api/claims/${claimId}/assess/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
  });
  if (!res.ok) return parseError(res);
  if (!res.body) throw new ApiError("No response body", res.status);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: AssessResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      let ev: AssessSseEvent;
      try {
        ev = JSON.parse(trimmed.slice(trimmed.indexOf(":") + 1).trim());
      } catch {
        continue; // skip malformed
      }
      if (ev.event === "step" && ev.tool) {
        onStep({ tool: ev.tool, data: ev.data });
      } else if (ev.event === "done" && ev.result) {
        result = ev.result;
      } else if (ev.event === "error") {
        throw new ApiError(ev.message || "Assessment failed", res.status);
      }
    }
  }

  if (!result) throw new ApiError("Assessment stream ended without a result", res.status);
  return result;
}

export async function getTransitions(
  id: string,
): Promise<TransitionsResponse> {
  return getJson<TransitionsResponse>(`/api/claims/${id}/transitions`);
}

export async function postTransition(
  id: string,
  body: TransitionRequest,
  role: Role,
  userId?: string,
): Promise<TransitionResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-Role": role,
  };
  if (userId) headers["X-User-Id"] = userId;

  const res = await fetch(`${API_BASE}/api/claims/${id}/transition`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) return parseError(res);
  return res.json() as Promise<TransitionResponse>;
}
