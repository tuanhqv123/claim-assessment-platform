"use client";

import { useCallback, useEffect, useState } from "react";
import {
  App,
  Button,
  Card,
  Flex,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import {
  listMembers,
  createMember,
  updateMember,
  deleteMember,
  type Member,
  type MemberInput,
} from "@/lib/membersDirectoryApi";

const { Text } = Typography;
const TEAL = "#0d9488";

interface Props {
  tenants: { id: string; name: string }[];
  loadingTenants?: boolean;
}

function statusColor(s: string | null | undefined): string {
  return s === "ACTIVE" ? "success" : "default";
}

export default function MembersPanel({ tenants, loadingTenants }: Props) {
  const { message } = App.useApp();

  const [tenantId, setTenantId] = useState<string | undefined>();
  const [members, setMembers] = useState<Member[]>([]);
  const [listLoading, setListLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Member | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<MemberInput>();

  // Default to the first tenant.
  useEffect(() => {
    if (!tenantId && tenants.length > 0) setTenantId(tenants[0].id);
  }, [tenants, tenantId]);

  const load = useCallback(
    async (tid: string) => {
      setListLoading(true);
      try {
        setMembers(await listMembers(tid));
      } catch (e) {
        message.error(`Failed to load members: ${(e as Error).message}`);
      } finally {
        setListLoading(false);
      }
    },
    [message],
  );

  useEffect(() => {
    if (tenantId) load(tenantId);
  }, [tenantId, load]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue?.({ status: "ACTIVE" });
    form.setFieldValue("status", "ACTIVE");
    setModalOpen(true);
  };

  const openEdit = (m: Member) => {
    setEditing(m);
    form.setFieldsValue({
      member_code: m.member_code ?? "",
      full_name: m.full_name ?? "",
      email: m.email ?? "",
      phone: m.phone ?? "",
      status: m.status ?? "ACTIVE",
      note: m.note ?? "",
    });
    setModalOpen(true);
  };

  const submit = async () => {
    if (!tenantId) return;
    let values: MemberInput;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await updateMember(editing.id, values);
        message.success(`Updated ${values.member_code}`);
      } else {
        await createMember(tenantId, values);
        message.success(`Added ${values.member_code}`);
      }
      setModalOpen(false);
      await load(tenantId);
    } catch (e) {
      message.error(`Save failed: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (m: Member) => {
    if (!tenantId) return;
    try {
      await deleteMember(m.id);
      message.success(`Removed ${m.member_code}`);
      await load(tenantId);
    } catch (e) {
      message.error(`Delete failed: ${(e as Error).message}`);
    }
  };

  const columns: ColumnsType<Member> = [
    {
      title: "Code",
      dataIndex: "member_code",
      key: "member_code",
      width: 130,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    { title: "Full name", dataIndex: "full_name", key: "full_name" },
    {
      title: "Contact",
      key: "contact",
      render: (_: unknown, m: Member) => (
        <Space direction="vertical" size={0}>
          {m.email && <Text type="secondary">{m.email}</Text>}
          {m.phone && <Text type="secondary">{m.phone}</Text>}
          {!m.email && !m.phone && <Text type="secondary">—</Text>}
        </Space>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (s: string) => <Tag color={statusColor(s)}>{s ?? "—"}</Tag>,
    },
    {
      title: "",
      key: "actions",
      width: 110,
      render: (_: unknown, m: Member) => (
        <Space>
          <Button
            size="small"
            type="text"
            icon={<EditOutlined />}
            onClick={() => openEdit(m)}
          />
          <Popconfirm
            title={`Remove ${m.member_code}?`}
            okText="Remove"
            okButtonProps={{ danger: true }}
            onConfirm={() => onDelete(m)}
          >
            <Button size="small" type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card variant="outlined">
      <Flex justify="space-between" align="center" wrap gap={12} style={{ marginBottom: 16 }}>
        <Space align="center">
          <TeamOutlined style={{ color: TEAL, fontSize: 18 }} />
          <Text strong style={{ fontSize: 16 }}>
            Members directory
          </Text>
          <Select
            value={tenantId}
            onChange={setTenantId}
            loading={loadingTenants}
            style={{ minWidth: 220 }}
            options={tenants.map((t) => ({ value: t.id, label: t.name }))}
            placeholder="Select tenant"
          />
        </Space>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          style={{ background: TEAL }}
          disabled={!tenantId}
          onClick={openCreate}
        >
          Add member
        </Button>
      </Flex>

      <Text type="secondary">
        Insured persons covered by this insurer. This is a people directory; assigning a
        member to a specific policy is done in the Policies tab.
      </Text>

      <Table<Member>
        rowKey="id"
        style={{ marginTop: 16 }}
        loading={listLoading}
        columns={columns}
        dataSource={members}
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
      />

      <Modal
        title={editing ? `Edit ${editing.member_code}` : "Add member"}
        open={modalOpen}
        onOk={submit}
        confirmLoading={saving}
        onCancel={() => setModalOpen(false)}
        okText={editing ? "Save" : "Add"}
        okButtonProps={{ style: { background: TEAL } }}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" requiredMark={false}>
          <Form.Item
            name="member_code"
            label="Member code"
            rules={[{ required: true, message: "Member code is required" }]}
          >
            <Input placeholder="MBR-001" />
          </Form.Item>
          <Form.Item
            name="full_name"
            label="Full name"
            rules={[{ required: true, message: "Full name is required" }]}
          >
            <Input placeholder="Jane Doe" />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input placeholder="jane@example.com" />
          </Form.Item>
          <Form.Item name="phone" label="Phone">
            <Input placeholder="+66 ..." />
          </Form.Item>
          <Form.Item name="status" label="Status" initialValue="ACTIVE">
            <Select
              options={[
                { value: "ACTIVE", label: "ACTIVE" },
                { value: "INACTIVE", label: "INACTIVE" },
              ]}
            />
          </Form.Item>
          <Form.Item name="note" label="Note">
            <Input.TextArea rows={2} placeholder="Optional" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
