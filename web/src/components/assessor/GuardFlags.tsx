"use client";

import { Alert, Space, Tag, Typography } from "antd";
import { SafetyOutlined } from "@ant-design/icons";
import type { GuardFlags as GuardFlagsType } from "@/lib/assessorApi";
import { humanizeKey, humanizeValue } from "@/lib/humanize";

interface Props {
  flags: GuardFlagsType;
}

function isEmpty(flags: GuardFlagsType): boolean {
  if (!flags) return true;
  if (Array.isArray(flags)) return flags.length === 0;
  return Object.keys(flags).length === 0;
}

/**
 * Renders the guard/validation flags returned by the assessment guard.
 * Shape is intentionally loose (array of strings, or a record of checks),
 * so we render both forms gracefully.
 */
export default function GuardFlags({ flags }: Props) {
  if (isEmpty(flags)) {
    return (
      <Alert
        type="success"
        showIcon
        icon={<SafetyOutlined />}
        title="No guard flags raised"
      />
    );
  }

  if (Array.isArray(flags)) {
    return (
      <Space direction="vertical" size={6} style={{ width: "100%" }}>
        {flags.map((f, i) => (
          <Alert key={i} type="warning" showIcon title={humanizeValue(f)} />
        ))}
      </Space>
    );
  }

  return (
    <Space direction="vertical" size={6} style={{ width: "100%" }}>
      {Object.entries(flags as Record<string, unknown>).map(([key, value]) => {
        const truthy = value === true || (Array.isArray(value) && value.length > 0);
        return (
          <div key={key} style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
            <Tag color={truthy ? "warning" : "default"}>{humanizeKey(key)}</Tag>
            <Typography.Text
              type="secondary"
              style={{ fontSize: 12, whiteSpace: "pre-line", wordBreak: "break-word" }}
            >
              {humanizeValue(value)}
            </Typography.Text>
          </div>
        );
      })}
    </Space>
  );
}
