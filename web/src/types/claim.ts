import type { ClaimType } from "@/constants";

export interface ClaimInput {
  claim_id: string;
  policy_id: string;
  member_id: string;
  claim_type: ClaimType;
  sub_benefit: string;
  diagnosis_code: string;
  diagnosis_description: string;
  procedure_codes: string[];
  amount: number;
  claim_date: string;
  provider: string;
  submitted_document_ids: string[];
}
