"use client";

import { Descriptions, Typography } from "antd";
import type { BenefitCalculation as BenefitCalculationType } from "@/types";

const FIELDS: { key: keyof BenefitCalculationType; label: string }[] = [
  { key: "submitted_amount", label: "Submitted" },
  { key: "covered_amount", label: "Covered" },
  { key: "copay_amount", label: "Copay" },
  { key: "member_pays", label: "Member Pays" },
  { key: "remaining_limit", label: "Remaining Limit" },
];

interface Props {
  data: BenefitCalculationType;
}

export default function BenefitCalculation({ data }: Props) {
  return (
    <div>
      <Descriptions column={2} size="small" bordered>
        {FIELDS.map((f) => (
          <Descriptions.Item key={f.key} label={f.label}>
            <strong>{data[f.key]}</strong>
          </Descriptions.Item>
        ))}
      </Descriptions>
      <Typography.Paragraph
        type="secondary"
        style={{ marginTop: 12, fontSize: 13 }}
      >
        {data.breakdown}
      </Typography.Paragraph>
    </div>
  );
}
