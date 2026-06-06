import type { Recommendation } from "@/constants";

export interface DocumentReviewItem {
  document_id: string;
  type: string;
  status: string;
  issues: string;
}

export interface PolicyVerification {
  policy_active: boolean;
  member_covered: boolean;
  claim_type_covered: boolean;
  coverage_period_valid: boolean;
  details: string;
}

export interface MedicalNecessity {
  is_appropriate: boolean | null;
  reasoning: string;
  warnings: string[];
}

export interface BenefitCalculation {
  submitted_amount: string;
  covered_amount: string;
  copay_amount: string;
  member_pays: string;
  remaining_limit: string;
  breakdown: string;
}

export interface RecommendationSection {
  decision: string;
  reasoning: string;
  next_steps: string;
}

export interface PolicyCitation {
  clause: string;
  relevance: string;
}

export interface AssessmentReport {
  document_review: DocumentReviewItem[];
  policy_verification: PolicyVerification;
  medical_necessity: MedicalNecessity;
  benefit_calculation: BenefitCalculation;
  recommendation: RecommendationSection;
  policy_citations: PolicyCitation[];
}

export interface AssessmentResult {
  claim_id: string;
  recommendation: Recommendation;
  recommendation_reason: string;
  report: AssessmentReport;
  tool_call_log: ToolCallEntry[];
}

export interface ToolCallEntry {
  tool_name: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
}
