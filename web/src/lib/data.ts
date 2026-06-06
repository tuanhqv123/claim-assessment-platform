import type { ClaimInput } from "@/types/claim";
import type { AssessmentResult } from "@/types/assessment";

interface CaseMapping {
  id: string;
  claimFile: string;
  resultFile: string;
}

const CASES: CaseMapping[] = [
  { id: "1", claimFile: "/data/claim_1.json", resultFile: "/data/case_1_approve.json" },
  { id: "2", claimFile: "/data/claim_2.json", resultFile: "/data/case_2_reject.json" },
  { id: "3", claimFile: "/data/claim_3.json", resultFile: "/data/case_3_request_info.json" },
];

export function getCaseIds(): string[] {
  return CASES.map((c) => c.id);
}

function getCaseById(id: string): CaseMapping | undefined {
  return CASES.find((c) => c.id === id);
}

export async function loadClaim(id: string): Promise<ClaimInput | null> {
  const c = getCaseById(id);
  if (!c) return null;
  const res = await fetch(c.claimFile);
  if (!res.ok) return null;
  return res.json();
}

export async function loadResult(id: string): Promise<AssessmentResult | null> {
  const c = getCaseById(id);
  if (!c) return null;
  const res = await fetch(c.resultFile);
  if (!res.ok) return null;
  return res.json();
}
