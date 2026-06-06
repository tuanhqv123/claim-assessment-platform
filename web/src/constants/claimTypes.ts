export const CLAIM_TYPE = {
  OUTPATIENT: "OUTPATIENT",
  INPATIENT: "INPATIENT",
  DENTAL: "DENTAL",
  MATERNITY: "MATERNITY",
} as const;

export type ClaimType = (typeof CLAIM_TYPE)[keyof typeof CLAIM_TYPE];

export const CLAIM_TYPE_LABEL: Record<ClaimType, string> = {
  OUTPATIENT: "Outpatient",
  INPATIENT: "Inpatient",
  DENTAL: "Dental",
  MATERNITY: "Maternity",
};

export const CLAIM_TYPE_COLOR: Record<ClaimType, string> = {
  OUTPATIENT: "blue",
  INPATIENT: "purple",
  DENTAL: "cyan",
  MATERNITY: "magenta",
};
