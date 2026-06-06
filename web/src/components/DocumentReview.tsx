"use client";

import { Table, Tag } from "antd";
import type { DocumentReviewItem } from "@/types";

const STATUS_COLOR: Record<string, string> = {
  COMPLETE: "success",
  INCOMPLETE: "warning",
  MISSING: "error",
  TYPE_MISMATCH: "error",
};

const columns = [
  {
    title: "Document ID",
    dataIndex: "document_id",
    key: "document_id",
  },
  {
    title: "Type",
    dataIndex: "type",
    key: "type",
    render: (v: string) => v.replace(/_/g, " "),
  },
  {
    title: "Status",
    dataIndex: "status",
    key: "status",
    render: (v: string) => <Tag color={STATUS_COLOR[v] ?? "default"}>{v}</Tag>,
  },
  {
    title: "Issues",
    dataIndex: "issues",
    key: "issues",
    render: (v: string) => (v === "None" || !v ? "—" : v),
  },
];

interface Props {
  items: DocumentReviewItem[];
}

export default function DocumentReview({ items }: Props) {
  return (
    <Table
      columns={columns}
      dataSource={items}
      rowKey="document_id"
      pagination={false}
      size="small"
    />
  );
}
