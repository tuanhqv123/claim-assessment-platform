"use client";

import { Descriptions, Tag } from "antd";
import { CheckOutlined, CloseOutlined } from "@ant-design/icons";
import type { PolicyVerification as PolicyVerificationType } from "@/types";

const CHECK_ITEMS: { key: keyof Omit<PolicyVerificationType, "details">; label: string }[] = [
  { key: "policy_active", label: "Policy Active" },
  { key: "member_covered", label: "Member Covered" },
  { key: "claim_type_covered", label: "Claim Type Covered" },
  { key: "coverage_period_valid", label: "Coverage Period Valid" },
];

interface Props {
  data: PolicyVerificationType;
}

export default function PolicyVerification({ data }: Props) {
  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {CHECK_ITEMS.map((item) => {
          const passed = data[item.key];
          return (
            <Tag
              key={item.key}
              icon={passed ? <CheckOutlined /> : <CloseOutlined />}
              color={passed ? "success" : "error"}
            >
              {item.label}
            </Tag>
          );
        })}
      </div>
      <Descriptions column={1} size="small">
        <Descriptions.Item label="Details">{data.details}</Descriptions.Item>
      </Descriptions>
    </div>
  );
}
