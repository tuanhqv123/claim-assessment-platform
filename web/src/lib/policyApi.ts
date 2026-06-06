// Policy & member administration (Challenge 15 + RAG corpus).
// Insurers upload the signed policy document; its text becomes the RAG corpus
// the assessment agent retrieves clauses from.

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface BenefitSummary {
  type: string | null;
  annual_limit: number | null;
}

export interface PolicySummary {
  id: string;
  tenant_id: string;
  policy_number: string | null;
  policyholder_name: string | null;
  policyholder_type: string | null;
  status: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  benefits: BenefitSummary[];
  member_count: number;
  member_ids: string[];
  has_document: boolean;
}

export interface PolicyExclusion {
  clause?: string;
  description?: string;
  keywords?: string[];
}

export interface PolicyDetail extends PolicySummary {
  data: Record<string, unknown>;
  member_ids: string[];
  exclusions: PolicyExclusion[];
  document_text: string;
  document_uploaded: boolean;
  document_url: string | null;
  clause_count: number;
}

export interface PolicyDocumentResult {
  document_url: string | null;
  document_chars: number;
  clause_count: number;
  has_document: boolean;
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.errors && Array.isArray(body.errors)) detail = body.errors.join("; ");
      else if (body?.error) detail = String(body.error);
      else if (body?.detail) {
        detail =
          typeof body.detail === "string"
            ? body.detail
            : body.detail.error || body.detail.message || JSON.stringify(body.detail);
      }
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function listPolicies(tenantId: string): Promise<PolicySummary[]> {
  return unwrap(
    await fetch(`${API_BASE}/api/tenants/${tenantId}/policies`, { cache: "no-store" }),
  );
}

export async function getPolicy(policyId: string): Promise<PolicyDetail> {
  return unwrap(await fetch(`${API_BASE}/api/policies/${policyId}`, { cache: "no-store" }));
}

export async function createPolicy(
  tenantId: string,
  policyNumber: string,
  data: Record<string, unknown>,
): Promise<PolicySummary> {
  return unwrap(
    await fetch(`${API_BASE}/api/tenants/${tenantId}/policies`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy_number: policyNumber, data }),
    }),
  );
}

export async function updatePolicy(
  policyId: string,
  data: Record<string, unknown>,
): Promise<PolicySummary> {
  return unwrap(
    await fetch(`${API_BASE}/api/policies/${policyId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data }),
    }),
  );
}

export async function deletePolicy(policyId: string): Promise<void> {
  await unwrap(
    await fetch(`${API_BASE}/api/policies/${policyId}`, { method: "DELETE" }),
  );
}

export async function uploadPolicyDocument(
  policyId: string,
  file: File,
): Promise<PolicyDocumentResult> {
  const form = new FormData();
  form.append("file", file);
  return unwrap(
    await fetch(`${API_BASE}/api/policies/${policyId}/document`, {
      method: "POST",
      body: form,
    }),
  );
}

export async function addMember(policyId: string, memberId: string): Promise<string[]> {
  const res = await unwrap<{ member_ids: string[] }>(
    await fetch(`${API_BASE}/api/policies/${policyId}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ member_id: memberId }),
    }),
  );
  return res.member_ids;
}

export async function removeMember(policyId: string, memberId: string): Promise<string[]> {
  const res = await unwrap<{ member_ids: string[] }>(
    await fetch(
      `${API_BASE}/api/policies/${policyId}/members/${encodeURIComponent(memberId)}`,
      { method: "DELETE" },
    ),
  );
  return res.member_ids;
}
