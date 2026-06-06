"use client";

import { Timeline, Typography, Tag } from "antd";
import {
  SafetyCertificateOutlined,
  FileTextOutlined,
  MedicineBoxOutlined,
  CalculatorOutlined,
} from "@ant-design/icons";
import type { ToolCallEntry } from "@/types";
import { humanizeValue } from "@/lib/humanize";

const TOOL_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  lookupPolicy: {
    label: "Policy Lookup",
    icon: <SafetyCertificateOutlined />,
    color: "blue",
  },
  verifyDocument: {
    label: "Document Verification",
    icon: <FileTextOutlined />,
    color: "cyan",
  },
  checkMedicalNecessity: {
    label: "Medical Necessity",
    icon: <MedicineBoxOutlined />,
    color: "purple",
  },
  calculateBenefit: {
    label: "Benefit Calculation",
    icon: <CalculatorOutlined />,
    color: "green",
  },
};

interface Props {
  entries: ToolCallEntry[];
}

export default function ToolCallTimeline({ entries }: Props) {
  const items = entries.map((entry, i) => {
    const config = TOOL_CONFIG[entry.tool_name] ?? {
      label: entry.tool_name,
      icon: null,
      color: "gray",
    };

    return {
      key: i,
      dot: config.icon,
      color: config.color,
      children: (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <Typography.Text strong>{config.label}</Typography.Text>
            <Tag>{entry.tool_name}</Tag>
          </div>
          <Typography.Text
            type="secondary"
            style={{ fontSize: 12, whiteSpace: "pre-line" }}
          >
            {humanizeValue(entry.inputs)}
          </Typography.Text>
        </div>
      ),
    };
  });

  return <Timeline items={items} />;
}
