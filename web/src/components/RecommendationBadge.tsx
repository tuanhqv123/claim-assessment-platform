"use client";

import { Tag } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import {
  RECOMMENDATION,
  RECOMMENDATION_LABEL,
  RECOMMENDATION_COLOR,
  type Recommendation,
} from "@/constants";

const ICONS: Record<Recommendation, React.ReactNode> = {
  [RECOMMENDATION.APPROVE]: <CheckCircleOutlined />,
  [RECOMMENDATION.REJECT]: <CloseCircleOutlined />,
  [RECOMMENDATION.REQUEST_MORE_INFO]: <ExclamationCircleOutlined />,
};

interface Props {
  value: Recommendation;
  size?: "small" | "default";
}

export default function RecommendationBadge({ value, size = "default" }: Props) {
  return (
    <Tag
      icon={ICONS[value]}
      color={RECOMMENDATION_COLOR[value]}
      style={size === "default" ? { fontSize: 14, padding: "4px 12px" } : undefined}
    >
      {RECOMMENDATION_LABEL[value]}
    </Tag>
  );
}
