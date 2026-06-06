"use client";

import { Form, Input, InputNumber, Select, DatePicker, Button, Space } from "antd";
import { SendOutlined } from "@ant-design/icons";
import { CLAIM_TYPE, CLAIM_TYPE_LABEL, type ClaimType } from "@/constants";
import type { ClaimInput } from "@/types";

const CLAIM_TYPE_OPTIONS = Object.values(CLAIM_TYPE).map((v) => ({
  value: v,
  label: CLAIM_TYPE_LABEL[v as ClaimType],
}));

const DOCUMENT_OPTIONS = [
  { value: "DOC-001", label: "DOC-001 (Medical Receipt)" },
  { value: "DOC-002", label: "DOC-002 (Prescription)" },
  { value: "DOC-010", label: "DOC-010 (Medical Receipt)" },
  { value: "DOC-011", label: "DOC-011 (Consultation Notes)" },
  { value: "DOC-020", label: "DOC-020 (Medical Receipt)" },
  { value: "DOC-021", label: "DOC-021 (Itemized Bill)" },
];

interface Props {
  onSubmit: (claim: ClaimInput) => void;
  loading: boolean;
  initialValues?: Partial<ClaimInput>;
}

export default function ClaimForm({ onSubmit, loading, initialValues }: Props) {
  const [form] = Form.useForm();

  const handleFinish = (values: Record<string, unknown>) => {
    const claim: ClaimInput = {
      claim_id: values.claim_id as string,
      policy_id: values.policy_id as string,
      member_id: values.member_id as string,
      claim_type: values.claim_type as ClaimType,
      sub_benefit: values.sub_benefit as string,
      diagnosis_code: values.diagnosis_code as string,
      diagnosis_description: values.diagnosis_description as string,
      procedure_codes: (values.procedure_codes as string).split(",").map((s: string) => s.trim()),
      amount: values.amount as number,
      claim_date: values.claim_date as string,
      provider: values.provider as string,
      submitted_document_ids: values.submitted_document_ids as string[],
    };
    onSubmit(claim);
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleFinish}
      initialValues={initialValues}
      size="middle"
    >
      <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
        <Form.Item name="claim_id" label="Claim ID" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0 }}>
          <Input placeholder="CLM-001" />
        </Form.Item>
        <Form.Item name="policy_id" label="Policy ID" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}>
          <Input placeholder="POL-001" />
        </Form.Item>
        <Form.Item name="member_id" label="Member ID" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}>
          <Input placeholder="MBR-001" />
        </Form.Item>
      </Space.Compact>

      <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
        <Form.Item name="claim_type" label="Claim Type" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0 }}>
          <Select options={CLAIM_TYPE_OPTIONS} placeholder="Select type" />
        </Form.Item>
        <Form.Item name="sub_benefit" label="Sub-benefit" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}>
          <Input placeholder="Doctor Visit" />
        </Form.Item>
        <Form.Item name="amount" label="Amount (THB)" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}>
          <InputNumber style={{ width: "100%" }} min={0} placeholder="2500" />
        </Form.Item>
      </Space.Compact>

      <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
        <Form.Item name="diagnosis_code" label="ICD-10 Code" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0 }}>
          <Input placeholder="J06.9" />
        </Form.Item>
        <Form.Item name="diagnosis_description" label="Diagnosis Description" rules={[{ required: true }]} style={{ flex: 2, marginBottom: 0, marginLeft: 8 }}>
          <Input placeholder="Acute upper respiratory infection" />
        </Form.Item>
      </Space.Compact>

      <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
        <Form.Item name="procedure_codes" label="Procedure Codes (comma-separated)" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0 }}>
          <Input placeholder="99213" />
        </Form.Item>
        <Form.Item name="provider" label="Provider" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}>
          <Input placeholder="Bangkok Hospital" />
        </Form.Item>
        <Form.Item name="claim_date" label="Claim Date" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}>
          <Input placeholder="2024-03-15" />
        </Form.Item>
      </Space.Compact>

      <Form.Item name="submitted_document_ids" label="Submitted Documents" rules={[{ required: true }]}>
        <Select mode="multiple" options={DOCUMENT_OPTIONS} placeholder="Select documents" />
      </Form.Item>

      <Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} icon={<SendOutlined />} block size="large">
          {loading ? "Assessing Claim..." : "Submit for Assessment"}
        </Button>
      </Form.Item>
    </Form>
  );
}
