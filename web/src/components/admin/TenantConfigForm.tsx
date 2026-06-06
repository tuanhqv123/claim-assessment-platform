"use client";

import { useEffect, useMemo } from "react";
import {
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Card,
  Space,
  Typography,
  Divider,
  Switch,
  Collapse,
  Alert,
  ColorPicker,
  Row,
  Col,
} from "antd";
import { PlusOutlined, DeleteOutlined, SaveOutlined } from "@ant-design/icons";
import type {
  TenantConfig,
  ApprovalTier,
  CustomField,
  DocumentRequirements,
} from "@/lib/adminApi";
import {
  ALL_CLAIM_TYPES,
  NOTIFICATION_EVENTS,
  NOTIFICATION_CHANNELS,
  APPROVAL_ROLES,
  CUSTOM_FIELD_TYPES,
} from "@/lib/adminApi";

const { Text } = Typography;

// Form values are a flattened/transformed view of TenantConfig that AntD Form
// can edit directly. documents/sla/notifications are kept as arrays of entries.
interface DocEntry {
  claim_type: string;
  required: string[];
  optional: string[];
}

interface SlaEntry {
  key: string;
  days: number;
}

interface FormValues {
  branding: {
    company_name: string;
    logo_url?: string | null;
    primary_color?: string | null;
    secondary_color?: string | null;
  };
  claim_types: string[];
  documents: DocEntry[];
  auto_approval_threshold: number;
  approval_tiers: ApprovalTier[];
  notifications: Record<string, string[]>;
  sla: SlaEntry[];
  custom_fields: CustomField[];
}

function configToForm(config: TenantConfig): FormValues {
  const documents: DocEntry[] = Object.entries(config.documents || {}).map(
    ([claim_type, reqs]) => ({
      claim_type,
      required: reqs.required ?? [],
      optional: reqs.optional ?? [],
    }),
  );
  const sla: SlaEntry[] = Object.entries(config.sla || {}).map(([key, days]) => ({
    key,
    days,
  }));
  const notifications: Record<string, string[]> = {};
  for (const ev of NOTIFICATION_EVENTS) {
    notifications[ev] = config.notifications?.[ev]?.channels ?? [];
  }
  return {
    branding: {
      company_name: config.branding?.company_name ?? "",
      logo_url: config.branding?.logo_url ?? null,
      primary_color: config.branding?.primary_color ?? "#1677ff",
      secondary_color: config.branding?.secondary_color ?? "#10243E",
    },
    claim_types: config.claim_types ?? [],
    documents,
    auto_approval_threshold: config.auto_approval_threshold ?? 0,
    approval_tiers: config.approval_tiers ?? [],
    notifications,
    sla,
    custom_fields: config.custom_fields ?? [],
  };
}

function colorToString(c: unknown): string | null {
  if (c == null) return null;
  if (typeof c === "string") return c;
  // AntD ColorPicker passes a Color object with toHexString().
  const obj = c as { toHexString?: () => string };
  if (typeof obj.toHexString === "function") return obj.toHexString();
  return null;
}

function formToConfig(values: FormValues): TenantConfig {
  const documents: Record<string, DocumentRequirements> = {};
  for (const d of values.documents ?? []) {
    if (!d?.claim_type) continue;
    documents[d.claim_type] = {
      required: d.required ?? [],
      optional: d.optional ?? [],
    };
  }
  const sla: Record<string, number> = {};
  for (const s of values.sla ?? []) {
    if (!s?.key) continue;
    sla[s.key] = Number(s.days);
  }
  const notifications = {
    claim_submitted: { channels: values.notifications?.claim_submitted ?? [] },
    approved: { channels: values.notifications?.approved ?? [] },
    rejected: { channels: values.notifications?.rejected ?? [] },
    payment_sent: { channels: values.notifications?.payment_sent ?? [] },
  };
  return {
    branding: {
      company_name: values.branding.company_name,
      logo_url: values.branding.logo_url || null,
      primary_color: colorToString(values.branding.primary_color),
      secondary_color: colorToString(values.branding.secondary_color),
    },
    claim_types: values.claim_types ?? [],
    documents,
    auto_approval_threshold: Number(values.auto_approval_threshold),
    approval_tiers: (values.approval_tiers ?? []).map((t) => ({
      min: Number(t.min),
      max: t.max === null || t.max === undefined ? null : Number(t.max),
      role: t.role,
    })),
    notifications,
    sla,
    custom_fields: (values.custom_fields ?? []).map((f) => ({
      key: f.key,
      label: f.label,
      type: f.type ?? "text",
      required: !!f.required,
    })),
  };
}

interface Props {
  initialConfig: TenantConfig;
  /** When true, render slug/name inputs (create a new tenant). */
  isCreate?: boolean;
  saving?: boolean;
  /** Backend 422 validation messages to surface at the top of the form. */
  backendErrors?: string[];
  onSubmit: (
    config: TenantConfig,
    meta: { slug?: string; name?: string },
  ) => void;
  submitLabel?: string;
}

const CLAIM_TYPE_OPTIONS = ALL_CLAIM_TYPES.map((v) => ({ value: v, label: v }));
const ROLE_OPTIONS = APPROVAL_ROLES.map((v) => ({ value: v, label: v }));
const CHANNEL_OPTIONS = NOTIFICATION_CHANNELS.map((v) => ({ value: v, label: v }));
const FIELD_TYPE_OPTIONS = CUSTOM_FIELD_TYPES.map((v) => ({ value: v, label: v }));
const EVENT_LABELS: Record<string, string> = {
  claim_submitted: "Claim Submitted",
  approved: "Approved",
  rejected: "Rejected",
  payment_sent: "Payment Sent",
};

export default function TenantConfigForm({
  initialConfig,
  isCreate = false,
  saving = false,
  backendErrors = [],
  onSubmit,
  submitLabel = "Save Configuration",
}: Props) {
  const [form] = Form.useForm<FormValues & { slug?: string; name?: string }>();
  const logoUrl = Form.useWatch(["branding", "logo_url"], form);

  const initialValues = useMemo(() => configToForm(initialConfig), [initialConfig]);

  // Reset the form when the source config changes (e.g. switching tenants).
  useEffect(() => {
    form.setFieldsValue(initialValues);
  }, [form, initialValues]);

  const handleFinish = (values: FormValues & { slug?: string; name?: string }) => {
    const config = formToConfig(values);
    onSubmit(config, { slug: values.slug, name: values.name });
  };

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={initialValues}
      onFinish={handleFinish}
      scrollToFirstError
    >
      {backendErrors.length > 0 && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          title="Configuration rejected by server"
          description={
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {backendErrors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          }
        />
      )}

      {isCreate && (
        <div style={{ marginBottom: 16 }}>
          <Divider titlePlacement="start" plain>
            Tenant Identity
          </Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Tenant Name"
                rules={[{ required: true, message: "Name is required" }]}
              >
                <Input placeholder="Acme Health" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="slug"
                label="Slug"
                rules={[
                  { required: true, message: "Slug is required" },
                  {
                    pattern: /^[a-z0-9-]+$/,
                    message: "Lowercase letters, numbers, and hyphens only",
                  },
                ]}
              >
                <Input placeholder="acme-health" />
              </Form.Item>
            </Col>
          </Row>
        </div>
      )}

      <Collapse
        defaultActiveKey={["branding", "claim_types", "documents", "approval"]}
        items={[
          // ---- Branding ----
          {
            key: "branding",
            label: "Branding",
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name={["branding", "company_name"]}
                    label="Company Name"
                    rules={[{ required: true, message: "Company name is required" }]}
                  >
                    <Input placeholder="SafeGuard Insurance" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={["branding", "logo_url"]}
                    label="Logo URL"
                    style={{ marginBottom: logoUrl ? 8 : undefined }}
                  >
                    <Input placeholder="https://…/logo.png" />
                  </Form.Item>
                  {logoUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      key={logoUrl}
                      src={logoUrl}
                      alt="Logo preview"
                      style={{
                        maxHeight: 48,
                        maxWidth: 180,
                        objectFit: "contain",
                        border: "1px solid #f0f0f0",
                        borderRadius: 6,
                        padding: 4,
                        background: "#fafafa",
                        marginBottom: 16,
                      }}
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.display = "none";
                      }}
                    />
                  )}
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={["branding", "primary_color"]}
                    label="Primary Color"
                  >
                    <ColorPicker showText format="hex" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={["branding", "secondary_color"]}
                    label="Secondary Color"
                  >
                    <ColorPicker showText format="hex" />
                  </Form.Item>
                </Col>
              </Row>
            ),
          },
          // ---- Claim types ----
          {
            key: "claim_types",
            label: "Claim Types",
            children: (
              <Form.Item
                name="claim_types"
                label="Enabled Claim Types"
                tooltip="At least one claim type must be enabled."
                rules={[
                  {
                    validator: (_, v: string[]) =>
                      v && v.length > 0
                        ? Promise.resolve()
                        : Promise.reject(
                            new Error("At least one claim type must be enabled"),
                          ),
                  },
                ]}
              >
                <Select
                  mode="multiple"
                  options={CLAIM_TYPE_OPTIONS}
                  placeholder="Select enabled claim types"
                />
              </Form.Item>
            ),
          },
          // ---- Documents per claim type ----
          {
            key: "documents",
            label: "Required / Optional Documents",
            children: (
              <Form.List name="documents">
                {(fields, { add, remove }) => (
                  <>
                    <Text type="secondary">
                      Define document requirements for each enabled claim type.
                    </Text>
                    {fields.map((field) => (
                      <Card
                        key={field.key}
                        size="small"
                        style={{ marginTop: 12 }}
                        extra={
                          <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => remove(field.name)}
                          />
                        }
                      >
                        <Row gutter={12}>
                          <Col span={6}>
                            <Form.Item
                              name={[field.name, "claim_type"]}
                              label="Claim Type"
                              rules={[{ required: true, message: "Required" }]}
                              style={{ marginBottom: 8 }}
                            >
                              <Select options={CLAIM_TYPE_OPTIONS} />
                            </Form.Item>
                          </Col>
                          <Col span={9}>
                            <Form.Item
                              name={[field.name, "required"]}
                              label="Required Documents"
                              style={{ marginBottom: 8 }}
                            >
                              <Select
                                mode="tags"
                                tokenSeparators={[","]}
                                placeholder="medical_receipt"
                              />
                            </Form.Item>
                          </Col>
                          <Col span={9}>
                            <Form.Item
                              name={[field.name, "optional"]}
                              label="Optional Documents"
                              style={{ marginBottom: 8 }}
                            >
                              <Select
                                mode="tags"
                                tokenSeparators={[","]}
                                placeholder="prescription"
                              />
                            </Form.Item>
                          </Col>
                        </Row>
                      </Card>
                    ))}
                    <Button
                      type="dashed"
                      onClick={() => add({ claim_type: undefined, required: [], optional: [] })}
                      icon={<PlusOutlined />}
                      style={{ marginTop: 12 }}
                      block
                    >
                      Add claim-type documents
                    </Button>
                  </>
                )}
              </Form.List>
            ),
          },
          // ---- Approval routing ----
          {
            key: "approval",
            label: "Approval Routing",
            children: (
              <>
                <Form.Item
                  name="auto_approval_threshold"
                  label="Auto-approval Threshold (THB)"
                  tooltip="Claims at or below this amount auto-approve. Must be >= 0."
                  rules={[
                    { required: true, message: "Threshold is required" },
                    {
                      type: "number",
                      min: 0,
                      message: "Threshold must be >= 0",
                    },
                  ]}
                >
                  <InputNumber style={{ width: 240 }} min={0} step={1000} />
                </Form.Item>

                <Divider titlePlacement="start" plain>
                  Approval Tiers
                </Divider>
                <Text type="secondary">
                  Tiers must be contiguous, start at min 0, and the highest tier
                  must be unbounded (leave Max empty). Any &quot;auto&quot; tier&apos;s max
                  must equal the threshold above.
                </Text>
                <Form.List name="approval_tiers">
                  {(fields, { add, remove }) => (
                    <>
                      {fields.map((field) => (
                        <Space
                          key={field.key}
                          align="baseline"
                          style={{ display: "flex", marginTop: 12 }}
                        >
                          <Form.Item
                            name={[field.name, "min"]}
                            label="Min"
                            rules={[{ required: true, message: "Required" }]}
                            style={{ marginBottom: 0 }}
                          >
                            <InputNumber min={0} style={{ width: 140 }} />
                          </Form.Item>
                          <Form.Item
                            name={[field.name, "max"]}
                            label="Max (empty = unbounded)"
                            style={{ marginBottom: 0 }}
                          >
                            <InputNumber min={0} style={{ width: 180 }} placeholder="∞" />
                          </Form.Item>
                          <Form.Item
                            name={[field.name, "role"]}
                            label="Role"
                            rules={[{ required: true, message: "Required" }]}
                            style={{ marginBottom: 0 }}
                          >
                            <Select options={ROLE_OPTIONS} style={{ width: 160 }} />
                          </Form.Item>
                          <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => remove(field.name)}
                          />
                        </Space>
                      ))}
                      <Button
                        type="dashed"
                        onClick={() => add({ min: 0, max: null, role: "assessor" })}
                        icon={<PlusOutlined />}
                        style={{ marginTop: 12 }}
                        block
                      >
                        Add approval tier
                      </Button>
                    </>
                  )}
                </Form.List>
              </>
            ),
          },
          // ---- Notifications ----
          {
            key: "notifications",
            label: "Notifications",
            children: (
              <Row gutter={16}>
                {NOTIFICATION_EVENTS.map((ev) => (
                  <Col span={12} key={ev}>
                    <Form.Item
                      name={["notifications", ev]}
                      label={EVENT_LABELS[ev]}
                    >
                      <Select
                        mode="multiple"
                        options={CHANNEL_OPTIONS}
                        placeholder="Channels"
                      />
                    </Form.Item>
                  </Col>
                ))}
              </Row>
            ),
          },
          // ---- SLA ----
          {
            key: "sla",
            label: "SLA (business days)",
            children: (
              <Form.List name="sla">
                {(fields, { add, remove }) => (
                  <>
                    <Text type="secondary">
                      Use key <code>default</code> for a fallback, or a claim type
                      (e.g. <code>OUTPATIENT</code>) for an override. Each value must
                      be a positive number of business days.
                    </Text>
                    {fields.map((field) => (
                      <Space
                        key={field.key}
                        align="baseline"
                        style={{ display: "flex", marginTop: 12 }}
                      >
                        <Form.Item
                          name={[field.name, "key"]}
                          label="Key"
                          rules={[{ required: true, message: "Required" }]}
                          style={{ marginBottom: 0 }}
                        >
                          <Input placeholder="default" style={{ width: 200 }} />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, "days"]}
                          label="Days"
                          rules={[
                            { required: true, message: "Required" },
                            {
                              type: "number",
                              min: 1,
                              message: "SLA must be positive",
                            },
                          ]}
                          style={{ marginBottom: 0 }}
                        >
                          <InputNumber min={1} style={{ width: 140 }} />
                        </Form.Item>
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(field.name)}
                        />
                      </Space>
                    ))}
                    <Button
                      type="dashed"
                      onClick={() => add({ key: "", days: 7 })}
                      icon={<PlusOutlined />}
                      style={{ marginTop: 12 }}
                      block
                    >
                      Add SLA entry
                    </Button>
                  </>
                )}
              </Form.List>
            ),
          },
          // ---- Custom fields ----
          {
            key: "custom_fields",
            label: "Custom Fields",
            children: (
              <Form.List name="custom_fields">
                {(fields, { add, remove }) => (
                  <>
                    {fields.map((field) => (
                      <Space
                        key={field.key}
                        align="baseline"
                        style={{ display: "flex", marginTop: 12 }}
                      >
                        <Form.Item
                          name={[field.name, "key"]}
                          label="Key"
                          rules={[{ required: true, message: "Required" }]}
                          style={{ marginBottom: 0 }}
                        >
                          <Input placeholder="employee_id" style={{ width: 160 }} />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, "label"]}
                          label="Label"
                          rules={[{ required: true, message: "Required" }]}
                          style={{ marginBottom: 0 }}
                        >
                          <Input placeholder="Employee ID" style={{ width: 180 }} />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, "type"]}
                          label="Type"
                          style={{ marginBottom: 0 }}
                        >
                          <Select options={FIELD_TYPE_OPTIONS} style={{ width: 120 }} />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, "required"]}
                          label="Required"
                          valuePropName="checked"
                          style={{ marginBottom: 0 }}
                        >
                          <Switch />
                        </Form.Item>
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(field.name)}
                        />
                      </Space>
                    ))}
                    <Button
                      type="dashed"
                      onClick={() =>
                        add({ key: "", label: "", type: "text", required: false })
                      }
                      icon={<PlusOutlined />}
                      style={{ marginTop: 12 }}
                      block
                    >
                      Add custom field
                    </Button>
                  </>
                )}
              </Form.List>
            ),
          },
        ]}
      />

      <Form.Item style={{ marginTop: 24 }}>
        <Button
          type="primary"
          htmlType="submit"
          icon={<SaveOutlined />}
          loading={saving}
          size="large"
        >
          {submitLabel}
        </Button>
      </Form.Item>
    </Form>
  );
}
