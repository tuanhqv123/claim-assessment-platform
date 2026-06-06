// Typed fetch helpers for the Admin Tenant Configuration UI (Challenge 15).
// Base URL from NEXT_PUBLIC_API_URL (default http://localhost:8000).
// Shapes mirror docs/API_CONTRACT.md and src/tenant/* exactly.

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Config types (mirror src/tenant/config_schema.py TenantConfig)
// ---------------------------------------------------------------------------

export interface Branding {
  company_name: string;
  logo_url?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
}

export interface DocumentRequirements {
  required: string[];
  optional: string[];
}

export interface ApprovalTier {
  min: number;
  max: number | null; // null => unbounded top tier
  role: string;
}

export interface NotificationRule {
  channels: string[];
}

export interface Notifications {
  claim_submitted: NotificationRule;
  approved: NotificationRule;
  rejected: NotificationRule;
  payment_sent: NotificationRule;
}

export interface CustomField {
  key: string;
  label: string;
  type: string; // default "text"
  required: boolean;
}

export interface TenantConfig {
  branding: Branding;
  claim_types: string[];
  documents: Record<string, DocumentRequirements>;
  auto_approval_threshold: number;
  approval_tiers: ApprovalTier[];
  notifications: Notifications;
  sla: Record<string, number>;
  custom_fields: CustomField[];
}

// ---------------------------------------------------------------------------
// Endpoint response shapes
// ---------------------------------------------------------------------------

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

export interface ConfigVersionMeta {
  version: number;
  is_active: boolean;
  created_at: string;
  // The contract specifies only metadata, but if the backend also returns the
  // full config body per version we use it to render a historical version.
  config?: TenantConfig;
}

// process_claim result (src/tenant/runtime.process_claim)
export interface PreviewResult {
  required_documents: string[];
  approval_routing: {
    tier_role: string;
    auto_approved: boolean;
  };
  notifications: Record<string, string[]>;
  sla_deadline: string;
  custom_fields: {
    required: string[];
    provided: Record<string, unknown>;
    valid: boolean;
    errors: string[];
  };
}

// Claim shape accepted by the preview endpoint.
export interface PreviewClaim {
  claim_type: string;
  amount: number;
  custom_fields?: Record<string, unknown>;
  [key: string]: unknown;
}

// One entry from src/tenant/diff.diff_configs. a_value / b_value may be the
// ABSENT sentinel string "<absent>" when a key exists on only one side.
export interface DiffEntry {
  path: string;
  a_value: unknown;
  b_value: unknown;
}

export const DIFF_ABSENT = "<absent>";

export interface CreateTenantPayload {
  slug: string;
  name: string;
  config: TenantConfig;
}

// ---------------------------------------------------------------------------
// Error handling — surfaces backend 422 { errors: [...] }
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  status: number;
  /** Backend-supplied validation messages (from a 422 { errors: [...] }). */
  errors: string[];

  constructor(status: number, message: string, errors: string[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // non-JSON body
  }
  if (body && typeof body === "object") {
    const obj = body as Record<string, unknown>;
    // 422 validation: { errors: [...] }
    if (Array.isArray(obj.errors)) {
      const errs = (obj.errors as unknown[]).map((e) => String(e));
      return new ApiError(res.status, errs.join("; ") || res.statusText, errs);
    }
    // FastAPI default: { detail: ... }
    if (typeof obj.detail === "string") {
      return new ApiError(res.status, obj.detail, [obj.detail]);
    }
    if (Array.isArray(obj.detail)) {
      const errs = (obj.detail as unknown[]).map((d) => {
        if (d && typeof d === "object") {
          const dd = d as Record<string, unknown>;
          const loc = Array.isArray(dd.loc) ? dd.loc.join(".") : "";
          return loc ? `${loc}: ${dd.msg}` : String(dd.msg ?? JSON.stringify(d));
        }
        return String(d);
      });
      return new ApiError(res.status, errs.join("; "), errs);
    }
    // { error: "..." } single-message style (workflow endpoints)
    if (typeof obj.error === "string") {
      return new ApiError(res.status, obj.error, [obj.error]);
    }
  }
  return new ApiError(res.status, res.statusText || `Request failed (${res.status})`);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Role": "admin",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw await parseError(res);
  }
  // Some endpoints may return empty body.
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export function listTenants(): Promise<TenantSummary[]> {
  return request<TenantSummary[]>("/api/tenants");
}

export function createTenant(payload: CreateTenantPayload): Promise<unknown> {
  return request<unknown>("/api/tenants", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getActiveConfig(tenantId: string): Promise<ActiveConfigResponse> {
  return request<ActiveConfigResponse>(`/api/tenants/${tenantId}/config`);
}

export function listConfigVersions(tenantId: string): Promise<ConfigVersionMeta[]> {
  return request<ConfigVersionMeta[]>(`/api/tenants/${tenantId}/config/versions`);
}

export function saveConfig(
  tenantId: string,
  config: TenantConfig,
): Promise<ActiveConfigResponse> {
  return request<ActiveConfigResponse>(`/api/tenants/${tenantId}/config`, {
    method: "POST",
    body: JSON.stringify({ config }),
  });
}

export function rollbackConfig(
  tenantId: string,
  version: number,
): Promise<ActiveConfigResponse> {
  return request<ActiveConfigResponse>(`/api/tenants/${tenantId}/config/rollback`, {
    method: "POST",
    body: JSON.stringify({ version }),
  });
}

export function previewClaim(
  tenantId: string,
  claim: PreviewClaim,
): Promise<PreviewResult> {
  return request<PreviewResult>(`/api/tenants/${tenantId}/preview`, {
    method: "POST",
    body: JSON.stringify({ claim }),
  });
}

export function diffConfigs(
  tenantA: string,
  tenantB: string,
): Promise<DiffEntry[]> {
  const params = new URLSearchParams({ a: tenantA, b: tenantB });
  return request<DiffEntry[]>(`/api/config/diff?${params.toString()}`);
}

// ---------------------------------------------------------------------------
// Helpers / shared constants
// ---------------------------------------------------------------------------

export const ALL_CLAIM_TYPES = [
  "OUTPATIENT",
  "INPATIENT",
  "DENTAL",
  "MATERNITY",
  "OPTICAL",
] as const;

export const NOTIFICATION_EVENTS = [
  "claim_submitted",
  "approved",
  "rejected",
  "payment_sent",
] as const;

export const NOTIFICATION_CHANNELS = ["email", "sms", "webhook", "push"] as const;

export const APPROVAL_ROLES = [
  "auto",
  "assessor",
  "team_lead",
  "manager",
  "director",
  "committee",
] as const;

export const CUSTOM_FIELD_TYPES = ["text", "number", "date", "boolean"] as const;

/** A blank, schema-valid starting config for onboarding a new tenant. */
export function blankConfig(): TenantConfig {
  return {
    branding: {
      company_name: "",
      logo_url: null,
      primary_color: "#1677ff",
      secondary_color: "#10243E",
    },
    claim_types: ["OUTPATIENT"],
    documents: {
      OUTPATIENT: { required: ["medical_receipt"], optional: [] },
    },
    auto_approval_threshold: 5000,
    approval_tiers: [
      { min: 0, max: 5000, role: "auto" },
      { min: 5000, max: null, role: "assessor" },
    ],
    notifications: {
      claim_submitted: { channels: ["email"] },
      approved: { channels: ["email"] },
      rejected: { channels: ["email"] },
      payment_sent: { channels: ["email"] },
    },
    sla: { default: 7 },
    custom_fields: [],
  };
}
