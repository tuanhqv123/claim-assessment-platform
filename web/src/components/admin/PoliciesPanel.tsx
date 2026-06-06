"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  App,
  Button,
  Card,
  Descriptions,
  Divider,
  Empty,
  Flex,
  Input,
  Modal,
  Form,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  Upload,
} from "antd";
import {
  CloudUploadOutlined,
  FileTextOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  UserAddOutlined,
} from "@ant-design/icons";
import type { UploadProps } from "antd/es/upload";
import {
  listPolicies,
  getPolicy,
  createPolicy,
  uploadPolicyDocument,
  addMember,
  removeMember,
  type PolicySummary,
  type PolicyDetail,
} from "@/lib/policyApi";
import { listMembers, type Member } from "@/lib/membersDirectoryApi";

const { Text, Paragraph } = Typography;
const TEAL = "#0d9488";

interface Props {
  tenants: { id: string; name: string }[];
  loadingTenants?: boolean;
}

function statusColor(s: string | null | undefined): string {
  if (s === "ACTIVE") return "success";
  if (s === "EXPIRED" || s === "CANCELLED") return "error";
  return "default";
}

function fmtMoney(v: number | null): string {
  return v == null ? "—" : `${v.toLocaleString()} THB`;
}

export default function PoliciesPanel({ tenants, loadingTenants }: Props) {
  const { message } = App.useApp();

  const [tenantId, setTenantId] = useState<string | undefined>();
  const [policies, setPolicies] = useState<PolicySummary[]>([]);
  const [listLoading, setListLoading] = useState(false);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<PolicyDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [newMember, setNewMember] = useState("");
  const [memberBusy, setMemberBusy] = useState(false);
  const [directory, setDirectory] = useState<Member[]>([]);

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();

  // Default to the first tenant.
  useEffect(() => {
    if (!tenantId && tenants.length > 0) setTenantId(tenants[0].id);
  }, [tenants, tenantId]);

  const loadList = useCallback(
    async (tid: string) => {
      setListLoading(true);
      try {
        const rows = await listPolicies(tid);
        setPolicies(rows);
        setSelectedId((prev) => prev ?? (rows[0]?.id ?? null));
      } catch (e) {
        message.error(`Failed to load policies: ${(e as Error).message}`);
      } finally {
        setListLoading(false);
      }
    },
    [message],
  );

  useEffect(() => {
    if (!tenantId) return;
    setSelectedId(null);
    setDetail(null);
    loadList(tenantId);
    listMembers(tenantId)
      .then(setDirectory)
      .catch(() => setDirectory([]));
  }, [tenantId, loadList]);

  const loadDetail = useCallback(
    async (pid: string) => {
      setDetailLoading(true);
      try {
        setDetail(await getPolicy(pid));
      } catch (e) {
        message.error(`Failed to load policy: ${(e as Error).message}`);
      } finally {
        setDetailLoading(false);
      }
    },
    [message],
  );

  useEffect(() => {
    if (selectedId) loadDetail(selectedId);
  }, [selectedId, loadDetail]);

  const refreshBoth = useCallback(async () => {
    if (tenantId) await loadList(tenantId);
    if (selectedId) await loadDetail(selectedId);
  }, [tenantId, selectedId, loadList, loadDetail]);

  const uploadProps: UploadProps = useMemo(
    () => ({
      showUploadList: false,
      accept: "image/*,application/pdf,.txt,.md",
      customRequest: async ({ file, onSuccess, onError }) => {
        if (!selectedId) return;
        setUploading(true);
        try {
          const res = await uploadPolicyDocument(selectedId, file as File);
          message.success(
            `Document indexed — ${res.clause_count} searchable clauses (${res.document_chars} chars).`,
          );
          await refreshBoth();
          onSuccess?.(res);
        } catch (e) {
          message.error(`Upload failed: ${(e as Error).message}`);
          onError?.(e as Error);
        } finally {
          setUploading(false);
        }
      },
    }),
    [selectedId, message, refreshBoth],
  );

  const handleAddMember = async () => {
    if (!selectedId || !newMember.trim()) return;
    setMemberBusy(true);
    try {
      await addMember(selectedId, newMember.trim());
      setNewMember("");
      await refreshBoth();
    } catch (e) {
      message.error(`Add member failed: ${(e as Error).message}`);
    } finally {
      setMemberBusy(false);
    }
  };

  const handleRemoveMember = async (mid: string) => {
    if (!selectedId) return;
    setMemberBusy(true);
    try {
      await removeMember(selectedId, mid);
      await refreshBoth();
    } catch (e) {
      message.error(`Remove member failed: ${(e as Error).message}`);
    } finally {
      setMemberBusy(false);
    }
  };

  const handleCreate = async () => {
    const values = await form.validateFields();
    if (!tenantId) return;
    setCreating(true);
    try {
      const data: Record<string, unknown> = {
        policy_id: values.policy_number,
        policyholder_name: values.policyholder_name,
        policyholder_type: values.policyholder_type,
        status: "ACTIVE",
        currency: "THB",
        effective_date: values.effective_date || undefined,
        expiry_date: values.expiry_date || undefined,
        member_ids: [],
        benefits: values.annual_limit
          ? [{ type: values.benefit_type, annual_limit: Number(values.annual_limit) }]
          : [],
        exclusions: [],
      };
      const created = await createPolicy(tenantId, values.policy_number, data);
      message.success(`Policy ${created.policy_number} created`);
      setCreateOpen(false);
      form.resetFields();
      await loadList(tenantId);
      setSelectedId(created.id);
    } catch (e) {
      if ((e as { errorFields?: unknown }).errorFields) return; // form validation
      message.error(`Create failed: ${(e as Error).message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <Flex gap={28} align="stretch" wrap="wrap">
      {/* ---- Left: tenant + policy list ---- */}
      <div style={{ flex: "0 1 320px", minWidth: 280 }}>
        <Flex align="center" gap={8} style={{ marginBottom: 12 }}>
          <Text type="secondary">Insurer:</Text>
          <Select
            style={{ flex: 1 }}
            placeholder="Select insurer"
            loading={loadingTenants}
            value={tenantId}
            onChange={setTenantId}
            options={tenants.map((t) => ({ value: t.id, label: t.name }))}
          />
        </Flex>

        <Flex align="center" justify="space-between" style={{ marginBottom: 8 }}>
          <Text strong>
            <SafetyCertificateOutlined style={{ color: TEAL, marginInlineEnd: 6 }} />
            Policies
          </Text>
          <Button
            size="small"
            icon={<PlusOutlined />}
            onClick={() => setCreateOpen(true)}
            disabled={!tenantId}
          >
            New
          </Button>
        </Flex>

        {listLoading ? (
          <Flex justify="center" style={{ padding: 24 }}>
            <Spin />
          </Flex>
        ) : policies.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No policies yet" />
        ) : (
          <Flex vertical gap={8}>
            {policies.map((p) => {
              const active = p.id === selectedId;
              return (
                <Card
                  key={p.id}
                  size="small"
                  hoverable
                  onClick={() => setSelectedId(p.id)}
                  style={{
                    cursor: "pointer",
                    borderColor: active ? TEAL : undefined,
                    borderWidth: active ? 1.5 : 1,
                  }}
                  styles={{ body: { padding: 12 } }}
                >
                  <Flex align="center" justify="space-between" gap={8}>
                    <div style={{ minWidth: 0 }}>
                      <Text strong style={{ fontSize: 13 }}>
                        {p.policy_number}
                      </Text>
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }} ellipsis>
                          {p.policyholder_name}
                        </Text>
                      </div>
                    </div>
                    <Flex vertical align="end" gap={2}>
                      <Tag color={statusColor(p.status)} style={{ marginInlineEnd: 0 }}>
                        {p.status ?? "—"}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {p.member_count} member{p.member_count === 1 ? "" : "s"}
                      </Text>
                    </Flex>
                  </Flex>
                </Card>
              );
            })}
          </Flex>
        )}
      </div>

      {/* ---- Right: policy detail ---- */}
      <div style={{ flex: "1 1 520px", minWidth: 0 }}>
        {!selectedId ? (
          <Empty description="Select a policy to manage its document and members." />
        ) : detailLoading && !detail ? (
          <Flex justify="center" style={{ padding: 48 }}>
            <Spin />
          </Flex>
        ) : detail ? (
          <Flex vertical gap={20}>
            {/* Overview */}
            <div>
              <Flex align="center" justify="space-between" wrap="wrap" gap={8} style={{ marginBottom: 12 }}>
                <Text strong style={{ fontSize: 15 }}>
                  {detail.policy_number} — {detail.policyholder_name}
                </Text>
                <Tag color={statusColor(detail.status)}>{detail.status}</Tag>
              </Flex>
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="Type">
                  {detail.policyholder_type ?? "—"}
                </Descriptions.Item>
                <Descriptions.Item label="Members">{detail.member_ids.length}</Descriptions.Item>
                <Descriptions.Item label="Effective">
                  {detail.effective_date ?? "—"}
                </Descriptions.Item>
                <Descriptions.Item label="Expiry">{detail.expiry_date ?? "—"}</Descriptions.Item>
                <Descriptions.Item label="Benefits" span={2}>
                  <Space wrap>
                    {detail.benefits.length === 0
                      ? "—"
                      : detail.benefits.map((b) => (
                          <Tag key={b.type} color="blue">
                            {b.type}: {fmtMoney(b.annual_limit)}
                          </Tag>
                        ))}
                  </Space>
                </Descriptions.Item>
              </Descriptions>
            </div>

            {/* Members */}
            <div>
              <Flex align="center" gap={8} style={{ marginBottom: 10 }}>
                <TeamOutlined style={{ color: TEAL }} />
                <Text strong>Members covered</Text>
                <Tag>{detail.member_ids.length}</Tag>
              </Flex>
              <Space.Compact style={{ width: "100%", maxWidth: 420, marginBottom: 10 }}>
                <Select
                  showSearch
                  style={{ width: "100%" }}
                  placeholder="Select a member to enroll"
                  value={newMember || undefined}
                  onChange={(v) => setNewMember(v)}
                  optionFilterProp="label"
                  notFoundContent={
                    directory.length === 0
                      ? "No members in this tenant's directory yet"
                      : "All directory members already enrolled"
                  }
                  options={directory
                    .filter((m) => !detail.member_ids.includes(m.member_code || ""))
                    .map((m) => ({
                      value: m.member_code || "",
                      label: m.full_name
                        ? `${m.member_code} — ${m.full_name}`
                        : m.member_code || "",
                    }))}
                />
                <Button
                  type="primary"
                  icon={<UserAddOutlined />}
                  loading={memberBusy}
                  disabled={!newMember}
                  onClick={handleAddMember}
                >
                  Add
                </Button>
              </Space.Compact>
              {detail.member_ids.length === 0 ? (
                <Text type="secondary">No members enrolled.</Text>
              ) : (
                <Flex wrap="wrap" gap={8}>
                  {detail.member_ids.map((m) => (
                    <Tag
                      key={m}
                      closable
                      onClose={(e) => {
                        e.preventDefault();
                        handleRemoveMember(m);
                      }}
                      style={{ paddingBlock: 4, fontSize: 13 }}
                    >
                      {m}
                    </Tag>
                  ))}
                </Flex>
              )}
            </div>

            <Divider style={{ margin: 0 }} />

            {/* Policy document / RAG corpus */}
            <div>
              <Flex align="center" justify="space-between" wrap="wrap" gap={8} style={{ marginBottom: 10 }}>
                <Flex align="center" gap={8}>
                  <FileTextOutlined style={{ color: TEAL }} />
                  <Text strong>Policy document</Text>
                  <Tag color={detail.document_uploaded ? "green" : "default"}>
                    {detail.document_uploaded ? "uploaded" : "auto-generated"}
                  </Tag>
                  <Tag color="purple">{detail.clause_count} searchable clauses</Tag>
                </Flex>
                <Upload {...uploadProps}>
                  <Button icon={<CloudUploadOutlined />} loading={uploading}>
                    Upload document
                  </Button>
                </Upload>
              </Flex>
              <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
                The assessment agent retrieves clauses from this document (exclusions,
                definitions, conditions) when adjudicating claims. Upload the signed
                policy (PDF / image / text) to replace the auto-generated terms.
                {detail.document_url && (
                  <>
                    {" "}
                    <a href={detail.document_url} target="_blank" rel="noreferrer">
                      View uploaded file
                    </a>
                  </>
                )}
              </Paragraph>
              <div
                style={{
                  maxHeight: 320,
                  overflow: "auto",
                  background: "#fafafa",
                  border: "1px solid #f0f0f0",
                  borderRadius: 8,
                  padding: 16,
                  fontSize: 12.5,
                  whiteSpace: "pre-wrap",
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                  lineHeight: 1.6,
                }}
              >
                {detail.document_text}
              </div>
            </div>
          </Flex>
        ) : null}
      </div>

      {/* ---- Create policy modal ---- */}
      <Modal
        title="New policy"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        confirmLoading={creating}
        okText="Create policy"
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ policyholder_type: "CORPORATE", benefit_type: "OUTPATIENT" }}
        >
          <Form.Item
            name="policy_number"
            label="Policy number"
            rules={[{ required: true, message: "Policy number is required" }]}
          >
            <Input placeholder="POL-004" />
          </Form.Item>
          <Form.Item
            name="policyholder_name"
            label="Policyholder"
            rules={[{ required: true, message: "Policyholder is required" }]}
          >
            <Input placeholder="Acme Corporation Ltd." />
          </Form.Item>
          <Form.Item name="policyholder_type" label="Type">
            <Select
              options={[
                { value: "CORPORATE", label: "Corporate (group)" },
                { value: "INDIVIDUAL", label: "Individual" },
              ]}
            />
          </Form.Item>
          <Flex gap={12}>
            <Form.Item name="effective_date" label="Effective date" style={{ flex: 1 }}>
              <Input placeholder="2026-01-01" />
            </Form.Item>
            <Form.Item name="expiry_date" label="Expiry date" style={{ flex: 1 }}>
              <Input placeholder="2026-12-31" />
            </Form.Item>
          </Flex>
          <Flex gap={12}>
            <Form.Item name="benefit_type" label="Benefit" style={{ flex: 1 }}>
              <Select
                options={[
                  { value: "OUTPATIENT", label: "Outpatient" },
                  { value: "INPATIENT", label: "Inpatient" },
                  { value: "DENTAL", label: "Dental" },
                ]}
              />
            </Form.Item>
            <Form.Item name="annual_limit" label="Annual limit (THB)" style={{ flex: 1 }}>
              <Input type="number" placeholder="100000" />
            </Form.Item>
          </Flex>
          <Text type="secondary" style={{ fontSize: 12 }}>
            You can upload the full policy document and add members after creating.
          </Text>
        </Form>
      </Modal>
    </Flex>
  );
}
