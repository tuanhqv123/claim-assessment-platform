"use client";

import { useEffect, useMemo } from "react";
import {
  Form,
  Select,
  InputNumber,
  Input,
  Button,
  Descriptions,
  Tag,
  Flex,
  Space,
  Typography,
  Alert,
  Empty,
  Divider,
} from "antd";
import { ExperimentOutlined } from "@ant-design/icons";
import type {
  TenantSummary,
  TenantConfig,
  PreviewResult,
  PreviewClaim,
} from "@/lib/adminApi";

const { Text } = Typography;

interface Props {
  tenants: TenantSummary[];
  /** Active config of the currently selected tenant, used to drive form options. */
  activeConfig: TenantConfig | null;
  selectedTenantId: string | null;
  onSelectTenant: (id: string) => void;
  loadingConfig?: boolean;
  running?: boolean;
  result: PreviewResult | null;
  error?: string | null;
  onPreview: (claim: PreviewClaim) => void;
}

export default function ConfigPreview({
  tenants,
  activeConfig,
  selectedTenantId,
  onSelectTenant,
  loadingConfig = false,
  running = false,
  result,
  error,
  onPreview,
}: Props) {
  const [form] = Form.useForm();

  const claimTypeOptions = useMemo(
    () => (activeConfig?.claim_types ?? []).map((v) => ({ value: v, label: v })),
    [activeConfig],
  );
  const customFields = activeConfig?.custom_fields ?? [];

  // Reset the form when the selected tenant changes.
  useEffect(() => {
    form.resetFields();
  }, [form, selectedTenantId]);

  const handleFinish = (values: Record<string, unknown>) => {
    const custom: Record<string, unknown> = {};
    for (const f of customFields) {
      const raw = values[`cf_${f.key}`];
      if (raw !== undefined && raw !== null && raw !== "") {
        custom[f.key] = raw;
      }
    }
    onPreview({
      claim_type: values.claim_type as string,
      amount: Number(values.amount),
      custom_fields: custom,
    });
  };

  return (
    <Flex vertical gap={24} style={{ width: "100%" }}>
      <div>
        <Text strong style={{ fontSize: 14, display: "block", marginBottom: 16 }}>
          Preview a Sample Claim
        </Text>
        <Form form={form} layout="vertical" onFinish={handleFinish}>
          <Form.Item label="Tenant" required>
            <Select
              placeholder="Select a tenant"
              value={selectedTenantId ?? undefined}
              onChange={onSelectTenant}
              options={tenants.map((t) => ({ value: t.id, label: t.name }))}
              loading={loadingConfig}
            />
          </Form.Item>

          <Space style={{ display: "flex" }} align="start">
            <Form.Item
              name="claim_type"
              label="Claim Type"
              rules={[{ required: true, message: "Required" }]}
              style={{ minWidth: 220 }}
            >
              <Select
                options={claimTypeOptions}
                placeholder="Select claim type"
                disabled={!activeConfig}
              />
            </Form.Item>
            <Form.Item
              name="amount"
              label="Amount (THB)"
              rules={[
                { required: true, message: "Required" },
                { type: "number", min: 0, message: "Amount must be >= 0" },
              ]}
              style={{ minWidth: 200 }}
            >
              <InputNumber style={{ width: "100%" }} min={0} step={1000} />
            </Form.Item>
          </Space>

          {customFields.length > 0 && (
            <>
              <Divider titlePlacement="start" plain>
                Custom Fields
              </Divider>
              {customFields.map((f) => (
                <Form.Item
                  key={f.key}
                  name={`cf_${f.key}`}
                  label={
                    <Space size={4}>
                      {f.label}
                      {f.required && <Tag color="red">required</Tag>}
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        ({f.type})
                      </Text>
                    </Space>
                  }
                >
                  {f.type === "number" ? (
                    <InputNumber style={{ width: "100%" }} />
                  ) : (
                    <Input placeholder={f.key} />
                  )}
                </Form.Item>
              ))}
            </>
          )}

          <Button
            type="primary"
            htmlType="submit"
            icon={<ExperimentOutlined />}
            loading={running}
            disabled={!activeConfig}
          >
            Run Preview
          </Button>
        </Form>
      </div>

      {error && <Alert type="error" showIcon title="Preview failed" description={error} />}

      {result ? (
        <div>
          <Divider titlePlacement="start" plain>
            Preview Result
          </Divider>
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Required Documents">
              {result.required_documents.length > 0 ? (
                <Space wrap>
                  {result.required_documents.map((d) => (
                    <Tag key={d} color="blue">
                      {d}
                    </Tag>
                  ))}
                </Space>
              ) : (
                <Text type="secondary">None</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Approval Routing">
              <Space>
                <Tag color="geekblue">role: {result.approval_routing.tier_role}</Tag>
                {result.approval_routing.auto_approved ? (
                  <Tag color="success">auto-approved</Tag>
                ) : (
                  <Tag color="orange">manual review</Tag>
                )}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="SLA Deadline">
              <Text strong>{result.sla_deadline}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Notifications">
              <Space direction="vertical" size={2}>
                {Object.entries(result.notifications).map(([ev, channels]) => (
                  <div key={ev}>
                    <Text type="secondary">{ev}: </Text>
                    {channels.length > 0 ? (
                      channels.map((c) => (
                        <Tag key={c} color="cyan">
                          {c}
                        </Tag>
                      ))
                    ) : (
                      <Text type="secondary">—</Text>
                    )}
                  </div>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="Custom-field Validation">
              {result.custom_fields.valid ? (
                <Tag color="success">valid</Tag>
              ) : (
                <Space direction="vertical">
                  <Tag color="error">invalid</Tag>
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    {result.custom_fields.errors.map((e, i) => (
                      <li key={i}>
                        <Text type="danger">{e}</Text>
                      </li>
                    ))}
                  </ul>
                </Space>
              )}
              {result.custom_fields.required.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <Text type="secondary">Required keys: </Text>
                  {result.custom_fields.required.map((k) => (
                    <Tag key={k}>{k}</Tag>
                  ))}
                </div>
              )}
            </Descriptions.Item>
          </Descriptions>
        </div>
      ) : (
        !error && (
          <Empty description="Run a preview to see required docs, routing, SLA, notifications, and custom-field validation." />
        )
      )}
    </Flex>
  );
}
