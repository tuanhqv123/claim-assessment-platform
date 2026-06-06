"use client";

import { Tag, Typography, Flex, Button } from "antd";
import {
  FileSearchOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import type { OcrExtractResult, OcrField } from "@/lib/memberApi";
import DocumentPreview from "./DocumentPreview";
import { humanizeValue } from "@/lib/humanize";

const { Text } = Typography;

const DOC_TYPE_LABEL: Record<string, string> = {
  receipt: "Receipt",
  discharge_summary: "Discharge Summary",
  lab_report: "Lab Report",
  prescription: "Prescription",
};

const DOC_TYPE_COLOR: Record<string, string> = {
  receipt: "blue",
  discharge_summary: "purple",
  lab_report: "cyan",
  prescription: "green",
};

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
    <Text style={{ fontSize: 12, color, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
      {pct}%
    </Text>
  );
}

function FieldRow({ name, field }: { name: string; field: OcrField }) {
  return (
    <Flex
      align="center"
      gap={12}
      style={{ padding: "7px 0", borderBottom: "1px solid #f5f5f5" }}
    >
      <Text
        type="secondary"
        style={{ fontSize: 12, flex: "0 0 140px", textTransform: "capitalize" }}
      >
        {name.replace(/_/g, " ")}
      </Text>
      <Text
        style={{
          fontSize: 13,
          flex: 1,
          minWidth: 0,
          whiteSpace: "pre-line",
          wordBreak: "break-word",
        }}
      >
        {humanizeValue(field.value)}
      </Text>
      <div style={{ flex: "0 0 46px", textAlign: "right" }}>
        <Confidence value={field.confidence ?? 0} />
      </div>
    </Flex>
  );
}

interface Props {
  fileName: string;
  result: OcrExtractResult;
  fileUrl?: string;
  onRemove?: () => void;
}

export default function ExtractionResult({ fileName, result, fileUrl, onRemove }: Props) {
  const docType = result.document_type;
  const fieldEntries = Object.entries(result.fields ?? {});
  const errors = result.validation_errors ?? [];
  const layout = result.layout ?? [];
  const imageSize: [number, number] = result.image_size ?? [0, 0];
  const showPreview = Boolean(fileUrl);

  const fieldsBlock = (
    <Flex vertical gap={12}>
      <Flex align="center" justify="space-between" gap={12} wrap="wrap">
        <Flex align="center" gap={8}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Classification confidence
          </Text>
          <Confidence value={result.confidence ?? 0} />
        </Flex>
        {errors.length > 0 ? (
          <Tag icon={<WarningOutlined />} color="warning">
            {errors.length} issue{errors.length > 1 ? "s" : ""}
          </Tag>
        ) : (
          <Tag icon={<CheckCircleOutlined />} color="success">
            Valid
          </Tag>
        )}
      </Flex>

      {errors.length > 0 && (
        <Flex vertical gap={4}>
          {errors.map((e, i) => (
            <Text key={i} style={{ color: "#fa8c16", fontSize: 12.5, lineHeight: 1.5 }}>
              <WarningOutlined style={{ marginInlineEnd: 6 }} />
              {e}
            </Text>
          ))}
        </Flex>
      )}

      <div>
        <Text type="secondary" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.4 }}>
          EXTRACTED FIELDS ({fieldEntries.length})
        </Text>
        <div style={{ marginTop: 4 }}>
          {fieldEntries.length === 0 ? (
            <Text type="secondary">No fields extracted.</Text>
          ) : (
            fieldEntries.map(([name, field]) => (
              <FieldRow key={name} name={name} field={field} />
            ))
          )}
        </div>
      </div>
    </Flex>
  );

  return (
    <Flex vertical gap={16}>
      <Flex align="center" justify="space-between" gap={8}>
        <Flex align="center" gap={8}>
          <FileSearchOutlined style={{ color: "#0d9488" }} />
          <Text strong style={{ fontSize: 13 }}>
            {fileName}
          </Text>
        </Flex>
        <Flex align="center" gap={6}>
          <Tag color="success" icon={<CheckCircleOutlined />} style={{ marginInlineEnd: 0 }}>
            Extracted
          </Tag>
          <Tag color={DOC_TYPE_COLOR[docType] ?? "default"} style={{ marginInlineEnd: 0 }}>
            {DOC_TYPE_LABEL[docType] ?? docType}
          </Tag>
          {onRemove && (
            <Button size="small" type="text" icon={<DeleteOutlined />} onClick={onRemove} />
          )}
        </Flex>
      </Flex>
      {showPreview && (
        <DocumentPreview fileUrl={fileUrl as string} layout={layout} imageSize={imageSize} />
      )}
      {fieldsBlock}
    </Flex>
  );
}
