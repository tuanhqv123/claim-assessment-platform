// Members directory (insured persons) administration, per tenant.
// A lightweight people-directory — distinct from the policy member-id roster
// (policyApi.addMember/removeMember) and from staff accounts (profiles).

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Member {
  id: string;
  tenant_id: string;
  member_code: string | null;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  status: string | null;
  note: string | null;
}

export interface MemberInput {
  member_code: string;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  status?: string;
  note?: string | null;
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

export async function listMembers(tenantId: string): Promise<Member[]> {
  return unwrap(
    await fetch(`${API_BASE}/api/tenants/${tenantId}/members`, { cache: "no-store" }),
  );
}

export async function createMember(tenantId: string, input: MemberInput): Promise<Member> {
  return unwrap(
    await fetch(`${API_BASE}/api/tenants/${tenantId}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

export async function updateMember(
  memberId: string,
  input: Partial<MemberInput>,
): Promise<Member> {
  return unwrap(
    await fetch(`${API_BASE}/api/members/${memberId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

export async function deleteMember(memberId: string): Promise<void> {
  await unwrap(await fetch(`${API_BASE}/api/members/${memberId}`, { method: "DELETE" }));
}
