"use client";

import { useMemo } from "react";
import { Select, Table, Typography, Tag, Flex, Space, Empty, Alert, Button, Divider } from "antd";
import { SwapOutlined } from "@ant-design/icons";
import type { TenantSummary, DiffEntry } from "@/lib/adminApi";
import { DIFF_ABSENT } from "@/lib/adminApi";

const { Text } = Typography;

interface Props {
  tenants: TenantSummary[];
  tenantA: string | null;
  tenantB: string | null;
  onSelectA: (id: string) => void;
  onSelectB: (id: string) => void;
  onRun: () => void;
  loading?: boolean;
  diff: DiffEntry[] | null;
  error?: string | null;
}

function renderValue(v: unknown): React.ReactNode {
  if (v === DIFF_ABSENT) {
    return <Tag>absent</Tag>;
  }
  if (v === null) {
    return <Text type="secondary">null</Text>;
  }
  if (typeof v === "object") {
    return (
      <Text code style={{ fontSize: 12 }}>
        {JSON.stringify(v)}
      </Text>
    );
  }
  return <Text code>{String(v)}</Text>;
}

export default function ConfigDiff({
  tenants,
  tenantA,
  tenantB,
  onSelectA,
  onSelectB,
  onRun,
  loading = false,
  diff,
  error,
}: Props) {
  const options = tenants.map((t) => ({ value: t.id, label: t.name }));

  const nameA = useMemo(
    () => tenants.find((t) => t.id === tenantA)?.name ?? "Config A",
    [tenants, tenantA],
  );
  const nameB = useMemo(
    () => tenants.find((t) => t.id === tenantB)?.name ?? "Config B",
    [tenants, tenantB],
  );

  return (
    <Flex vertical gap={24} style={{ width: "100%" }}>
      <div>
        <Text strong style={{ fontSize: 14, display: "block", marginBottom: 16 }}>
          Compare Two Tenant Configs
        </Text>
        <Space wrap align="end">
          <div>
            <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>
              Tenant A
            </Text>
            <Select
              style={{ width: 220 }}
              placeholder="Select tenant A"
              value={tenantA ?? undefined}
              onChange={onSelectA}
              options={options}
            />
          </div>
          <SwapOutlined style={{ fontSize: 18, color: "#999", marginBottom: 8 }} />
          <div>
            <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>
              Tenant B
            </Text>
            <Select
              style={{ width: 220 }}
              placeholder="Select tenant B"
              value={tenantB ?? undefined}
              onChange={onSelectB}
              options={options}
            />
          </div>
          <Button
            type="primary"
            onClick={onRun}
            loading={loading}
            disabled={!tenantA || !tenantB || tenantA === tenantB}
          >
            Compare
          </Button>
        </Space>
        {tenantA && tenantB && tenantA === tenantB && (
          <Alert
            style={{ marginTop: 12 }}
            type="info"
            showIcon
            title="Select two different tenants to compare."
          />
        )}
      </div>

      {error && <Alert type="error" showIcon title="Diff failed" description={error} />}

      {diff !== null &&
        (diff.length === 0 ? (
          <Empty description="No differences — the two configs are identical." />
        ) : (
          <div>
            <Divider titlePlacement="start" plain>
              {`${diff.length} difference(s)`}
            </Divider>
            <Table<DiffEntry>
              dataSource={diff.map((d, i) => ({ ...d, key: i }))}
              pagination={false}
              size="small"
              columns={[
                {
                  title: "Path",
                  dataIndex: "path",
                  key: "path",
                  render: (p: string) => <Text code>{p}</Text>,
                },
                {
                  title: nameA,
                  dataIndex: "a_value",
                  key: "a_value",
                  render: (v) => renderValue(v),
                },
                {
                  title: nameB,
                  dataIndex: "b_value",
                  key: "b_value",
                  render: (v) => renderValue(v),
                },
              ]}
            />
          </div>
        ))}

      {diff === null && !error && (
        <Empty description="Pick two tenants and compare to see a side-by-side diff." />
      )}
    </Flex>
  );
}
