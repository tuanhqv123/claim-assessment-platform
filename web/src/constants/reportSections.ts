export const REPORT_SECTION = {
  DOCUMENT_REVIEW: "document_review",
  POLICY_VERIFICATION: "policy_verification",
  MEDICAL_NECESSITY: "medical_necessity",
  BENEFIT_CALCULATION: "benefit_calculation",
  RECOMMENDATION: "recommendation",
  POLICY_CITATIONS: "policy_citations",
} as const;

export type ReportSectionKey =
  (typeof REPORT_SECTION)[keyof typeof REPORT_SECTION];

export const REPORT_SECTION_LABEL: Record<ReportSectionKey, string> = {
  document_review: "Document Review",
  policy_verification: "Policy Verification",
  medical_necessity: "Medical Necessity",
  benefit_calculation: "Benefit Calculation",
  recommendation: "Recommendation",
  policy_citations: "Policy Citations",
};

export const REPORT_SECTION_ICON: Record<ReportSectionKey, string> = {
  document_review: "FileTextOutlined",
  policy_verification: "SafetyCertificateOutlined",
  medical_necessity: "MedicineBoxOutlined",
  benefit_calculation: "CalculatorOutlined",
  recommendation: "AuditOutlined",
  policy_citations: "BookOutlined",
};
