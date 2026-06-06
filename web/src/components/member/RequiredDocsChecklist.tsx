"use client";

import { useEffect, useState } from "react";
import { Flex, Spin, Typography, Alert } from "antd";
import { CheckCircleFilled, CloseCircleFilled } from "@ant-design/icons";
import { checkDocuments, type CheckDocumentsResult } from "@/lib/memberApi";
import { humanizeKey } from "@/lib/humanize";

const { Text } = Typography;

const GREEN = "#16a34a";
const RED = "#dc2626";
const AMBER = "#b45309";

interface Props {
  tenantId: string;
  /** Live-selected claim type. When unset, the checklist prompts the member to pick one. */
  claimType?: string;
  /** OCR-classified document_type of each uploaded doc, e.g. ["receipt"]. */
  uploadedTypes: string[];
}

export default function RequiredDocsChecklist({
  tenantId,
  claimType,
  uploadedTypes,
}: Props) {
  const [result, setResult] = useState<CheckDocumentsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-fetch whenever the claim type or the set of uploaded types changes.
  // Serialize uploadedTypes so the effect re-runs on content change, not identity.
  const uploadedKey = uploadedTypes.join("|");

  useEffect(() => {
    if (!claimType) {
      setResult(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const res = await checkDocuments({
          tenant_id: tenantId,
          claim_type: claimType,
          uploaded_types: uploadedKey ? uploadedKey.split("|") : [],
        });
        if (!cancelled) setResult(res);
      } catch (err) {
        if (!cancelled) {
          setResult(null);
          setError((err as Error).message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tenantId, claimType, uploadedKey]);

  // No claim type chosen yet: render nothing (no placeholder).
  if (!claimType) return null;

  if (loading && !result) {
    return (
      <Flex align="center" gap={8} style={{ padding: "8px 0" }}>
        <Spin size="small" />
        <Text type="secondary" style={{ fontSize: 13 }}>
          Checking required documents…
        </Text>
      </Flex>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        showIcon
        title="Could not load required documents."
        description={error}
      />
    );
  }

  if (!result) return null;

  const satisfied = new Set(result.satisfied);

  return (
    <Flex vertical gap={8}>
      <Text strong style={{ fontSize: 13 }}>
        Required documents for {humanizeKey(result.claim_type)}
      </Text>

      <Flex vertical gap={4}>
        {result.required.map((doc) => {
          const ok = satisfied.has(doc);
          return (
            <Flex key={doc} align="center" gap={8}>
              {ok ? (
                <CheckCircleFilled style={{ color: GREEN, fontSize: 14 }} />
              ) : (
                <CloseCircleFilled style={{ color: RED, fontSize: 14 }} />
              )}
              <Text style={{ fontSize: 13, color: ok ? undefined : "#374151" }}>
                {humanizeKey(doc)}
              </Text>
            </Flex>
          );
        })}
      </Flex>

      {result.optional.length > 0 && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {result.optional.map((d) => humanizeKey(d)).join(", ")} — optional
        </Text>
      )}

      {result.mismatches.length > 0 && (
        <Text style={{ fontSize: 12, color: AMBER }}>
          Uploaded but not a recognized document for this claim type:{" "}
          {result.mismatches.map((d) => humanizeKey(d)).join(", ")} — these
          won&apos;t count.
        </Text>
      )}

      {result.complete ? (
        <Flex align="center" gap={6}>
          <CheckCircleFilled style={{ color: GREEN, fontSize: 14 }} />
          <Text strong style={{ fontSize: 13, color: GREEN }}>
            All required documents provided
          </Text>
        </Flex>
      ) : (
        <Text strong style={{ fontSize: 13, color: AMBER }}>
          Missing {result.missing.length} required document
          {result.missing.length === 1 ? "" : "(s)"} — please upload them.
        </Text>
      )}
    </Flex>
  );
}
