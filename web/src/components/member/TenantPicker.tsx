"use client";

import { Select, Flex, Typography, Tag } from "antd";
import { BankOutlined } from "@ant-design/icons";
import type { TenantSummary } from "@/lib/memberApi";

const { Text } = Typography;

interface Props {
  tenants: TenantSummary[];
  loading: boolean;
  value?: string;
  onChange: (tenantId: string) => void;
}

export default function TenantPicker({ tenants, loading, value, onChange }: Props) {
  const selected = tenants.find((t) => t.id === value);

  return (
    <Flex align="center" gap={12} wrap="wrap">
      <Flex align="center" gap={8}>
        <BankOutlined style={{ color: "#0d9488" }} />
        <Text strong style={{ fontSize: 13 }}>
          Insurer
        </Text>
      </Flex>
      <Select
        size="small"
        placeholder="Select an insurer"
        loading={loading}
        value={value}
        onChange={onChange}
        style={{ minWidth: 240 }}
        options={tenants.map((t) => ({ value: t.id, label: t.name }))}
      />
      {selected && (
        <Flex gap={4} wrap="wrap">
          {selected.config_summary.claim_types.map((ct) => (
            <Tag key={ct} color="cyan" style={{ fontSize: 11, marginInlineEnd: 0 }}>
              {ct}
            </Tag>
          ))}
        </Flex>
      )}
    </Flex>
  );
}
