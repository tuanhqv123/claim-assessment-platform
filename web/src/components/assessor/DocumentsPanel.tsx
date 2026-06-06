"use client";

import { Collapse, Tag, Typography, Empty, Space, Flex, Table } from "antd";
import { FileTextOutlined } from "@ant-design/icons";
import type { DocumentRow } from "@/lib/assessorApi";
import { humanizeValue } from "@/lib/humanize";

interface Props {
  documents: DocumentRow[];
}

const STATUS_COLOR: Record<string, string> = {
  COMPLETE: "success",
  INCOMPLETE: "warning",
  MISSING: "error",
  TYPE_MISMATCH: "error",
};

/** A single OCR field as persisted: `{ value, confidence }`. */
interface OcrFieldValue {
  value: unknown;
  confidence?: number;
}

function isOcrField(v: unknown): v is OcrFieldValue {
  return (
    typeof v === "object" &&
    v !== null &&
    "value" in (v as Record<string, unknown>)
  );
}

function isImageName(name?: string | null): boolean {
  return !!name && /\.(png|jpe?g|gif|webp|bmp)$/i.test(name);
}

function confidenceColor(c: number): string {
  if (c >= 0.85) return "#52c41a";
  if (c >= 0.6) return "#faad14";
  return "#ff4d4f";
}

/** Confidence as a plain coloured percentage (no progress bar). */
function Confidence({ value }: { value: number }) {
  const pct = Math.round((value ?? 0) * 100);
  const color = confidenceColor(value ?? 0);
  return (
    <Typography.Text
      style={{
        fontSize: 12,
        color,
        fontWeight: 600,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {pct}%
    </Typography.Text>
  );
}

const ITEM_COLUMNS = [
  { title: "Description", dataIndex: "description", key: "description" },
  {
    title: "Qty",
    dataIndex: "quantity",
    key: "quantity",
    align: "right" as const,
    width: 60,
  },
  {
    title: "Unit price",
    dataIndex: "unit_price",
    key: "unit_price",
    align: "right" as const,
    render: (v: unknown) => humanizeValue(v),
  },
  {
    title: "Total",
    dataIndex: "total",
    key: "total",
    align: "right" as const,
    render: (v: unknown) => humanizeValue(v),
  },
];

/** Renders an array of line-item objects as a compact nested table. */
function ItemsTable({ items }: { items: Record<string, unknown>[] }) {
  return (
    <Table
      size="small"
      pagination={false}
      rowKey={(_, i) => String(i)}
      columns={ITEM_COLUMNS}
      dataSource={items}
      style={{ marginTop: 6 }}
    />
  );
}

function FieldRow({ name, field }: { name: string; field: OcrFieldValue }) {
  const value = field.value;
  const confidence = field.confidence ?? 0;
  const isItemArray =
    Array.isArray(value) &&
    value.length > 0 &&
    typeof value[0] === "object" &&
    value[0] !== null;

  return (
    <div style={{ padding: "7px 0", borderBottom: "1px solid #f5f5f5" }}>
      <Flex align="center" gap={12}>
        <Typography.Text
          type="secondary"
          style={{ fontSize: 12, flex: "0 0 150px", textTransform: "capitalize" }}
        >
          {name.replace(/_/g, " ")}
        </Typography.Text>
        <div style={{ flex: 1, minWidth: 0 }}>
          {isItemArray ? (
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>
              {(value as unknown[]).length} line items
            </Typography.Text>
          ) : (
            <Typography.Text
              style={{
                fontSize: 13,
                display: "block",
                whiteSpace: "pre-line",
                wordBreak: "break-word",
              }}
            >
              {humanizeValue(value)}
            </Typography.Text>
          )}
        </div>
        <div style={{ flex: "0 0 46px", textAlign: "right" }}>
          <Confidence value={confidence} />
        </div>
      </Flex>
      {isItemArray && (
        <ItemsTable items={value as Record<string, unknown>[]} />
      )}
    </div>
  );
}

function OcrFields({ ocr }: { ocr: Record<string, unknown> | null }) {
  if (!ocr) {
    return <Typography.Text type="secondary">No OCR result.</Typography.Text>;
  }

  // The OCR pipeline returns {document_type, confidence, fields, validation_errors}.
  const fields = (ocr.fields as Record<string, unknown> | undefined) ?? null;
  const validationErrors = (ocr.validation_errors as unknown[] | undefined) ?? [];
  const classification = typeof ocr.confidence === "number" ? ocr.confidence : null;
  const fieldEntries = fields ? Object.entries(fields) : [];

  return (
    <Space direction="vertical" size={10} style={{ width: "100%" }}>
      <Flex align="center" gap={12} wrap="wrap">
        {ocr.document_type != null && (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            Detected type: <Tag>{String(ocr.document_type)}</Tag>
          </Typography.Text>
        )}
        {classification != null && (
          <Flex align="center" gap={6}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              Classification confidence
            </Typography.Text>
            <Confidence value={classification} />
          </Flex>
        )}
      </Flex>

      {fieldEntries.length > 0 ? (
        <div>
          <Typography.Text
            type="secondary"
            style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.4 }}
          >
            EXTRACTED FIELDS ({fieldEntries.length})
          </Typography.Text>
          <div style={{ marginTop: 4 }}>
            {fieldEntries.map(([k, v]) => (
              <FieldRow
                key={k}
                name={k}
                field={isOcrField(v) ? v : { value: v }}
              />
            ))}
          </div>
        </div>
      ) : (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          No extracted fields.
        </Typography.Text>
      )}

      {Array.isArray(validationErrors) && validationErrors.length > 0 && (
        <div>
          <Typography.Text type="danger" style={{ fontSize: 12 }}>
            Validation errors:
          </Typography.Text>{" "}
          <Space size={[4, 4]} wrap>
            {validationErrors.map((e, i) => (
              <Tag key={i} color="error" style={{ fontSize: 11 }}>
                {typeof e === "string" ? e : humanizeValue(e)}
              </Tag>
            ))}
          </Space>
        </div>
      )}
    </Space>
  );
}

export default function DocumentsPanel({ documents }: Props) {
  if (!documents || documents.length === 0) {
    return <Empty description="No documents uploaded" />;
  }

  const items = documents.map((doc) => ({
    key: doc.id,
    label: (
      <Space size={8}>
        <FileTextOutlined />
        <Typography.Text strong>
          {doc.file_name ?? doc.document_type ?? doc.id}
        </Typography.Text>
        {doc.document_type && <Tag>{doc.document_type}</Tag>}
        <Tag color={STATUS_COLOR[doc.status] ?? "default"}>{doc.status}</Tag>
        {doc.confidence != null && <Confidence value={doc.confidence} />}
      </Space>
    ),
    children: (
      <Space direction="vertical" size={10} style={{ width: "100%" }}>
        {doc.file_url &&
          (isImageName(doc.file_name) ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={doc.file_url}
              alt={doc.file_name ?? "document"}
              style={{
                maxWidth: "100%",
                maxHeight: 380,
                objectFit: "contain",
                border: "1px solid #f0f0f0",
                borderRadius: 8,
                background: "#fafafa",
              }}
            />
          ) : (
            <Typography.Link href={doc.file_url} target="_blank" rel="noreferrer">
              Open file ↗
            </Typography.Link>
          ))}

        {doc.issues && doc.issues.length > 0 && (
          <div>
            <Typography.Text type="warning" style={{ fontSize: 12 }}>
              Issues:
            </Typography.Text>{" "}
            <Space size={[4, 4]} wrap>
              {doc.issues.map((iss, i) => (
                <Tag key={i} color="warning" style={{ fontSize: 11 }}>
                  {iss}
                </Tag>
              ))}
            </Space>
          </div>
        )}

        <OcrFields ocr={doc.ocr_result} />
      </Space>
    ),
  }));

  return <Collapse items={items} defaultActiveKey={documents.map((d) => d.id)} />;
}
