import type { ClaimState } from "@/lib/assessorApi";

// Seeded tenants (API_CONTRACT.md). Used for the queue filter labels.
export const TENANTS: { id: string; name: string }[] = [
  { id: "a0000000-0000-0000-0000-000000000001", name: "SafeGuard" },
  { id: "a0000000-0000-0000-0000-000000000002", name: "HealthFirst" },
  { id: "a0000000-0000-0000-0000-000000000003", name: "GovHealth" },
];

export const TENANT_NAME: Record<string, string> = Object.fromEntries(
  TENANTS.map((t) => [t.id, t.name]),
);

export const STATE_LABEL: Record<ClaimState, string> = {
  SUBMITTED: "Submitted",
  DOCUMENTS_VERIFIED: "Documents Verified",
  UNDER_ASSESSMENT: "Under Assessment",
  PENDING_INFO: "Pending Info",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  PAYMENT_INITIATED: "Payment Initiated",
  CLOSED: "Closed",
};

export const STATE_COLOR: Record<ClaimState, string> = {
  SUBMITTED: "default",
  DOCUMENTS_VERIFIED: "cyan",
  UNDER_ASSESSMENT: "processing",
  PENDING_INFO: "warning",
  APPROVED: "success",
  REJECTED: "error",
  PAYMENT_INITIATED: "blue",
  CLOSED: "default",
};

export const ROLE_LABEL: Record<string, string> = {
  document_clerk: "Document Clerk",
  assessor: "Assessor",
  team_lead: "Team Lead",
  manager: "Manager",
  director: "Director",
  committee: "Committee",
  finance: "Finance",
  admin: "Admin",
};

export function stateLabel(state: string): string {
  return STATE_LABEL[state as ClaimState] ?? state;
}

export function stateColor(state: string): string {
  return STATE_COLOR[state as ClaimState] ?? "default";
}

export function roleLabel(role: string | null | undefined): string {
  if (!role) return "—";
  return ROLE_LABEL[role] ?? role;
}

// Map a target state to a friendly action verb for transition buttons.
export function transitionActionLabel(to: ClaimState): string {
  switch (to) {
    case "DOCUMENTS_VERIFIED":
      return "Verify Documents";
    case "UNDER_ASSESSMENT":
      return "Start Assessment";
    case "PENDING_INFO":
      return "Request Info";
    case "APPROVED":
      return "Approve";
    case "REJECTED":
      return "Reject";
    case "PAYMENT_INITIATED":
      return "Initiate Payment";
    case "CLOSED":
      return "Close";
    default:
      return `Move to ${stateLabel(to)}`;
  }
}
