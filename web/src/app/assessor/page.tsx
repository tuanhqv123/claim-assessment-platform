"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Flex,
  Typography,
  Select,
  Button,
  Alert,
  Divider,
} from "antd";
import {
  ReloadOutlined,
  FilterOutlined,
} from "@ant-design/icons";
import { PageBody } from "@/components/ui/PageHeader";
import {
  listClaims,
  CLAIM_STATES,
  type ClaimListItem,
  type ClaimState,
  ApiError,
} from "@/lib/assessorApi";
import { ReviewQueueTable } from "@/components/assessor";
import { TENANTS, stateLabel } from "@/components/assessor/constants";

const { Text } = Typography;

export default function AssessorQueuePage() {
  const router = useRouter();
  const [claims, setClaims] = useState<ClaimListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string>("");
  const [state, setState] = useState<ClaimState | "">("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listClaims({ tenantId, state });
      setClaims(data);
    } catch (err) {
      setError(
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Failed to load claims",
      );
    } finally {
      setLoading(false);
    }
  }, [tenantId, state]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <PageBody>
      <Flex vertical gap={16}>
        <Flex align="flex-end" justify="space-between" wrap="wrap" gap={16}>
          <Flex align="flex-end" gap={16} wrap="wrap">
            <Flex align="center" gap={8} style={{ alignSelf: "center" }}>
              <span style={{ color: "#0d9488", fontSize: 15, display: "flex" }}>
                <FilterOutlined />
              </span>
              <Text strong style={{ fontSize: 14 }}>
                Filters
              </Text>
            </Flex>
            <div style={{ minWidth: 200 }}>
              <Text type="secondary" style={{ display: "block", marginBottom: 4, fontSize: 12 }}>
                Tenant
              </Text>
              <Select
                allowClear
                style={{ width: "100%" }}
                placeholder="All tenants"
                value={tenantId || undefined}
                onChange={(v) => setTenantId(v ?? "")}
                options={TENANTS.map((t) => ({ value: t.id, label: t.name }))}
              />
            </div>
            <div style={{ minWidth: 200 }}>
              <Text type="secondary" style={{ display: "block", marginBottom: 4, fontSize: 12 }}>
                State
              </Text>
              <Select
                allowClear
                style={{ width: "100%" }}
                placeholder="All states"
                value={state || undefined}
                onChange={(v) => setState((v as ClaimState) ?? "")}
                options={CLAIM_STATES.map((s) => ({
                  value: s,
                  label: stateLabel(s),
                }))}
              />
            </div>
          </Flex>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            Refresh
          </Button>
        </Flex>

        {error && (
          <Alert
            type="error"
            showIcon
            title="Could not load the review queue"
            description={error}
            action={
              <Button size="small" onClick={load}>
                Retry
              </Button>
            }
          />
        )}

        <Divider style={{ margin: 0 }} />

        <ReviewQueueTable
          claims={claims}
          loading={loading}
          onOpen={(id) => router.push(`/assessor/${id}`)}
        />
      </Flex>
    </PageBody>
  );
}
