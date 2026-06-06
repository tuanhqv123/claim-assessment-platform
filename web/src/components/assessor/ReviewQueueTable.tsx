"use client";

import { Table, Tag, Typography, Button } from "antd";
import type { ColumnsType } from "antd/es/table";
import { RightOutlined } from "@ant-design/icons";
import type { ClaimListItem } from "@/lib/assessorApi";
import { TENANT_NAME, stateLabel, stateColor } from "./constants";

interface Props {
  claims: ClaimListItem[];
  loading?: boolean;
  onOpen: (id: string) => void;
}

function fmtAmount(n: number): string {
  return `${Number(n).toLocaleString()} THB`;
}

function fmtDate(s: string): string {
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString();
}

export default function ReviewQueueTable({ claims, loading, onOpen }: Props) {
  const columns: ColumnsType<ClaimListItem> = [
    {
      title: "Claim #",
      dataIndex: "claim_number",
      key: "claim_number",
      sorter: (a, b) => a.claim_number.localeCompare(b.claim_number),
      render: (v: string) => <Typography.Text strong>{v}</Typography.Text>,
    },
    {
      title: "Tenant",
      dataIndex: "tenant_id",
      key: "tenant_id",
      filters: Object.entries(TENANT_NAME).map(([id, name]) => ({
        text: name,
        value: id,
      })),
      onFilter: (value, record) => record.tenant_id === value,
      render: (id: string) => TENANT_NAME[id] ?? id,
    },
    {
      title: "Type",
      dataIndex: "claim_type",
      key: "claim_type",
      filters: Array.from(new Set(claims.map((c) => c.claim_type))).map((t) => ({
        text: t,
        value: t,
      })),
      onFilter: (value, record) => record.claim_type === value,
      render: (t: string) => <Tag>{t}</Tag>,
    },
    {
      title: "Member",
      dataIndex: "member_id",
      key: "member_id",
      render: (v: string | null) => v ?? "—",
    },
    {
      title: "Amount",
      dataIndex: "amount",
      key: "amount",
      align: "right",
      sorter: (a, b) => a.amount - b.amount,
      render: (v: number) => fmtAmount(v),
    },
    {
      title: "State",
      dataIndex: "state",
      key: "state",
      filters: Array.from(new Set(claims.map((c) => c.state))).map((s) => ({
        text: stateLabel(s),
        value: s,
      })),
      onFilter: (value, record) => record.state === value,
      render: (s: string) => <Tag color={stateColor(s)}>{stateLabel(s)}</Tag>,
    },
    {
      title: "Created",
      dataIndex: "created_at",
      key: "created_at",
      defaultSortOrder: "descend",
      sorter: (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      render: (v: string) => (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {fmtDate(v)}
        </Typography.Text>
      ),
    },
    {
      title: "",
      key: "action",
      align: "right",
      render: (_, record) => (
        <Button
          type="link"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(record.id);
          }}
        >
          Review <RightOutlined />
        </Button>
      ),
    },
  ];

  return (
    <Table<ClaimListItem>
      rowKey="id"
      columns={columns}
      dataSource={claims}
      loading={loading}
      onRow={(record) => ({
        onClick: () => onOpen(record.id),
        style: { cursor: "pointer" },
      })}
      pagination={{ pageSize: 12, showSizeChanger: true }}
      size="middle"
    />
  );
}
