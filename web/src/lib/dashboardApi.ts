/**
 * Typed fetch helper for the platform Dashboard.
 *
 * Backed by GET /api/stats. Self-contained (does not touch the shared
 * web/src/lib/api.ts).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface TenantStat {
  tenant_id: string;
  name: string;
  count: number;
}

export interface RecentClaim {
  id: string;
  claim_number: string;
  tenant_id: string;
  claim_type: string;
  amount: number;
  state: string;
  member_id: string | null;
  created_at: string;
}

export interface PlatformStats {
  total_claims: number;
  total_documents: number;
  total_tenants: number;
  total_amount: number;
  by_state: Record<string, number>;
  by_tenant: TenantStat[];
  recent: RecentClaim[];
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.error) detail = String(body.error);
      else if (body?.detail)
        detail =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
    } catch {
      // body was not JSON; keep status text
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function getStats(): Promise<PlatformStats> {
  const res = await fetch(`${API_BASE}/api/stats`, { cache: "no-store" });
  return unwrap<PlatformStats>(res);
}

export { API_BASE };
