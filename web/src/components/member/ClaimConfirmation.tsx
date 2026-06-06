"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Card,
  Result,
  Descriptions,
  Tag,
  Space,
  Typography,
  List,
  Alert,
  Flex,
  Spin,
} from "antd";
import {
  CheckCircleOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  PaperClipOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import {
  checkDocuments,
  type ClaimRow,
  type RuntimePreview,
  type DocumentRow,
  type CheckDocumentsResult,
} from "@/lib/memberApi";
import { humanizeKey } from "@/lib/humanize";
import type { UploadedDoc } from "./DocumentUploadCard";

const { Text } = Typography;

const GREEN = "#16a34a";
const RED = "#dc2626";
const AMBER = "#b45309";

interface Props {
  claim: ClaimRow;
  /** Runtime-derived routing/SLA/required docs for this claim. May be null if preview failed. */
  preview: RuntimePreview | null;
  /** Docs the member uploaded during intake (auto-attached on submit). */
  uploadedDocs: UploadedDoc[];
  /** Documents attached to the claim (populated by the auto-attach on submit). */
  attached: DocumentRow[];
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  // Accept either a date (YYYY-MM-DD) or full ISO timestamp.
  return value.length > 10 ? value.slice(0, 10) : value;
}

export default function ClaimConfirmation({
  claim,
  preview,
  uploadedDocs,
  attached,
}: Props) {
  const routing = preview?.approval_routing;
  const slaDeadline = preview?.sla_deadline ?? claim.sla_deadline;
  const attachedUids = new Set(attached.map((a) => a.file_name));

  // Live document-completeness for this submitted claim, based on the OCR types
  // of everything the member uploaded during intake.
  const uploadedTypes = useMemo(
    () => uploadedDocs.map((d) => d.result.document_type),
    [uploadedDocs],
  );
  const uploadedKey = uploadedTypes.join("|");

  const [check, setCheck] = useState<CheckDocumentsResult | null>(null);
  const [checkLoading, setCheckLoading] = useState(false);

  useEffect(() => {
    if (!claim.claim_type) return;
    let cancelled = false;
    setCheckLoading(true);
    (async () => {
      try {
        const res = await checkDocuments({
          tenant_id: claim.tenant_id,
          claim_type: claim.claim_type,
          uploaded_types: uploadedKey ? uploadedKey.split("|") : [],
        });
        if (!cancelled) setCheck(res);
      } catch {
        if (!cancelled) setCheck(null);
      } finally {
        if (!cancelled) setCheckLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [claim.tenant_id, claim.claim_type, uploadedKey]);

  const satisfiedSet = new Set(check?.satisfied ?? []);

  return (
    <>
      <Card style={{ marginBottom: 16 }}>
        <Result
          status="success"
          icon={<CheckCircleOutlined />}
          title={`Claim ${claim.claim_number} submitted`}
          subTitle={
            <Space>
              <Text type="secondary">State:</Text>
              <Tag color="processing">{claim.state}</Tag>
            </Space>
          }
        />

        <Descriptions
          bordered
          size="small"
          column={1}
          style={{ marginTop: 8 }}
        >
          <Descriptions.Item label="SLA Deadline">
            {formatDate(slaDeadline)}
          </Descriptions.Item>
          <Descriptions.Item label="Approval Routing">
            {routing ? (
              <Space>
                <Tag color={routing.auto_approved ? "success" : "blue"}>
                  {routing.tier_role}
                </Tag>
                {routing.auto_approved && (
                  <Text type="secondary">auto-approved</Text>
                )}
              </Space>
            ) : (
              <Text type="secondary">—</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Amount">
            {Number(claim.amount).toLocaleString()} THB
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title={
          <Space>
            <FileTextOutlined style={{ color: "#1677ff" }} />
            <span>Document completeness</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {checkLoading && !check ? (
          <Flex align="center" gap={8}>
            <Spin size="small" />
            <Text type="secondary">Checking documents…</Text>
          </Flex>
        ) : !check ? (
          <Text type="secondary">No required documents for this claim type.</Text>
        ) : (
          <Flex vertical gap={12}>
            {check.complete ? (
              <Alert
                type="success"
                showIcon
                title="All required documents attached"
              />
            ) : (
              <Alert
                type="warning"
                showIcon
                title={`Still missing: ${check.missing
                  .map((d) => humanizeKey(d))
                  .join(", ")}`}
                description="The assessor can request these from you — or submit another claim with the missing documents attached."
              />
            )}

            <Flex vertical gap={4}>
              {check.required.map((doc) => {
                const ok = satisfiedSet.has(doc);
                return (
                  <Flex key={doc} align="center" gap={8}>
                    {ok ? (
                      <CheckCircleFilled style={{ color: GREEN, fontSize: 14 }} />
                    ) : (
                      <CloseCircleFilled style={{ color: RED, fontSize: 14 }} />
                    )}
                    <Text style={{ fontSize: 13 }}>{humanizeKey(doc)}</Text>
                  </Flex>
                );
              })}
            </Flex>

            {check.optional.length > 0 && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {check.optional.map((d) => humanizeKey(d)).join(", ")} — optional
              </Text>
            )}

            {check.mismatches.length > 0 && (
              <Text style={{ fontSize: 12, color: AMBER }}>
                Uploaded but not recognized for this claim type:{" "}
                {check.mismatches.map((d) => humanizeKey(d)).join(", ")} — these
                won&apos;t count.
              </Text>
            )}
          </Flex>
        )}
      </Card>

      <Card
        title={
          <Space>
            <PaperClipOutlined style={{ color: "#1677ff" }} />
            <span>Documents</span>
          </Space>
        }
      >
        {uploadedDocs.length === 0 ? (
          <Alert
            type="info"
            showIcon
            title="No documents were uploaded with this claim."
            description="You can attach documents later from the claim detail view."
          />
        ) : (
          <List
            size="small"
            dataSource={uploadedDocs}
            renderItem={(d) => {
              const isAttached = attachedUids.has(d.fileName);
              return (
                <List.Item
                  actions={[
                    isAttached ? (
                      <Tag key="s" color="success" icon={<CheckCircleOutlined />}>
                        attached
                      </Tag>
                    ) : (
                      <Tag key="s">pending</Tag>
                    ),
                  ]}
                >
                  <List.Item.Meta
                    avatar={<FileTextOutlined />}
                    title={d.fileName}
                    description={
                      <Tag style={{ fontSize: 11 }}>
                        {d.result.document_type}
                      </Tag>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Card>
    </>
  );
}
