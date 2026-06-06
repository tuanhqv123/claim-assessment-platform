export const RECOMMENDATION = {
  APPROVE: "APPROVE",
  REJECT: "REJECT",
  REQUEST_MORE_INFO: "REQUEST_MORE_INFO",
} as const;

export type Recommendation =
  (typeof RECOMMENDATION)[keyof typeof RECOMMENDATION];

export const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  APPROVE: "Approved",
  REJECT: "Rejected",
  REQUEST_MORE_INFO: "More Info Needed",
};

export const RECOMMENDATION_COLOR: Record<Recommendation, string> = {
  APPROVE: "success",
  REJECT: "error",
  REQUEST_MORE_INFO: "warning",
};

export const RECOMMENDATION_ICON: Record<Recommendation, string> = {
  APPROVE: "CheckCircleOutlined",
  REJECT: "CloseCircleOutlined",
  REQUEST_MORE_INFO: "ExclamationCircleOutlined",
};
