"use client";

import {
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Space,
  Divider,
  Typography,
} from "antd";
import { useEffect } from "react";
import { SendOutlined } from "@ant-design/icons";
import type { CustomFieldSpec } from "@/lib/memberApi";
import type { ClaimPrefill } from "./ocrAutofill";

const { Text } = Typography;

export interface ClaimFormValues {
  policy_number: string;
  member_id: string;
  claim_type: string;
  sub_benefit: string;
  diagnosis_code: string;
  diagnosis_description: string;
  procedure_codes: string; // comma-separated in the form, split on submit
  amount: number;
  claim_date: string;
  provider: string;
  custom_fields: Record<string, unknown>;
}

interface PolicyOption {
  policy_number: string | null;
  policyholder_name?: string | null;
  member_ids: string[];
}

interface Props {
  /** Enabled claim types for the selected tenant. */
  claimTypes: string[];
  /** Tenant-specific dynamic custom fields. */
  customFields: CustomFieldSpec[];
  loading: boolean;
  onSubmit: (values: ClaimFormValues) => void;
  /** OCR-derived values to pre-fill (only the provided keys are set). */
  prefill?: ClaimPrefill;
  /** Fired with the live claim type (Select change or prefill) so the page can
   * drive the required-documents checklist. */
  onClaimTypeChange?: (claimType: string) => void;
  /** Tenant policies (drives the Policy dropdown + member filtering). */
  policies?: PolicyOption[];
  /** Tenant member directory (member_code -> full_name for nicer labels). */
  memberNames?: Record<string, string>;
}

function renderCustomFieldInput(field: CustomFieldSpec) {
  switch (field.type) {
    case "number":
      return <InputNumber style={{ width: "100%" }} placeholder={field.label} />;
    case "date":
      return <Input placeholder="YYYY-MM-DD" />;
    default:
      return <Input placeholder={field.label} />;
  }
}

export default function ClaimSubmitForm({
  claimTypes,
  customFields,
  loading,
  onSubmit,
  prefill,
  onClaimTypeChange,
  policies = [],
  memberNames = {},
}: Props) {
  const [form] = Form.useForm();
  const selectedPolicyNumber = Form.useWatch("policy_number", form);

  // Apply OCR-derived values whenever a new prefill arrives. setFieldsValue only
  // touches the keys present in `prefill`, leaving everything else (including
  // anything the member already typed) untouched.
  useEffect(() => {
    if (prefill && Object.keys(prefill).length > 0) {
      form.setFieldsValue(prefill);
      // If the prefill carries a claim type, surface it live too.
      const prefillClaimType = (prefill as Record<string, unknown>).claim_type;
      if (typeof prefillClaimType === "string" && prefillClaimType) {
        onClaimTypeChange?.(prefillClaimType);
      }
    }
  }, [prefill, form, onClaimTypeChange]);

  const claimTypeOptions = claimTypes.map((ct) => ({ value: ct, label: ct }));

  const policyOptions = policies.map((p) => ({
    value: p.policy_number || "",
    label: p.policyholder_name
      ? `${p.policy_number} — ${p.policyholder_name}`
      : p.policy_number || "",
  }));

  // Members enrolled in the currently-selected policy (so a member can only be
  // chosen if they're actually covered by that policy).
  const selectedPolicy = policies.find(
    (p) => p.policy_number === selectedPolicyNumber,
  );
  const memberOptions = (selectedPolicy?.member_ids || []).map((code) => ({
    value: code,
    label: memberNames[code] ? `${code} — ${memberNames[code]}` : code,
  }));

  const handleFinish = (values: Record<string, unknown>) => {
    const custom: Record<string, unknown> = {};
    for (const f of customFields) {
      custom[f.key] = (values[`cf_${f.key}`] as unknown) ?? "";
    }
    onSubmit({
      policy_number: values.policy_number as string,
      member_id: values.member_id as string,
      claim_type: values.claim_type as string,
      sub_benefit: values.sub_benefit as string,
      diagnosis_code: values.diagnosis_code as string,
      diagnosis_description: values.diagnosis_description as string,
      procedure_codes: values.procedure_codes as string,
      amount: values.amount as number,
      claim_date: values.claim_date as string,
      provider: values.provider as string,
      custom_fields: custom,
    });
  };

  return (
    <Form form={form} layout="vertical" onFinish={handleFinish} size="middle">
      <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
        <Form.Item
          name="policy_number"
          label="Policy"
          rules={[{ required: true }]}
          style={{ flex: 1, marginBottom: 0 }}
        >
          <Select
            showSearch
            optionFilterProp="label"
            placeholder={policyOptions.length ? "Select policy" : "POL-001"}
            options={policyOptions}
            onChange={() => form.setFieldValue("member_id", undefined)}
          />
        </Form.Item>
        <Form.Item
          name="member_id"
          label="Member"
          rules={[{ required: true }]}
          style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}
        >
          <Select
            showSearch
            optionFilterProp="label"
            disabled={!selectedPolicyNumber}
            placeholder={
              selectedPolicyNumber ? "Select member" : "Select a policy first"
            }
            notFoundContent="No members enrolled in this policy"
            options={memberOptions}
          />
        </Form.Item>
      </Space.Compact>

      <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
        <Form.Item
          name="claim_type"
          label="Claim Type"
          rules={[{ required: true }]}
          style={{ flex: 1, marginBottom: 0 }}
        >
          <Select
            options={claimTypeOptions}
            placeholder="Select type"
            onChange={(value) => onClaimTypeChange?.(value as string)}
          />
        </Form.Item>
        <Form.Item
          name="sub_benefit"
          label="Sub-benefit"
          rules={[{ required: true }]}
          style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}
        >
          <Input placeholder="Doctor Visit" />
        </Form.Item>
        <Form.Item
          name="amount"
          label="Amount (THB)"
          rules={[{ required: true }]}
          style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}
        >
          <InputNumber style={{ width: "100%" }} min={0} placeholder="2500" />
        </Form.Item>
      </Space.Compact>

      <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
        <Form.Item
          name="diagnosis_code"
          label="ICD-10 Code"
          rules={[{ required: true }]}
          style={{ flex: 1, marginBottom: 0 }}
        >
          <Input placeholder="J06.9" />
        </Form.Item>
        <Form.Item
          name="diagnosis_description"
          label="Diagnosis Description"
          rules={[{ required: true }]}
          style={{ flex: 2, marginBottom: 0, marginLeft: 8 }}
        >
          <Input placeholder="Acute upper respiratory infection" />
        </Form.Item>
      </Space.Compact>

      <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
        <Form.Item
          name="procedure_codes"
          label="Procedure Codes"
          tooltip="Separate multiple codes with commas"
          rules={[{ required: true }]}
          style={{ flex: 1, marginBottom: 0 }}
        >
          <Input placeholder="99213, 99214" />
        </Form.Item>
        <Form.Item
          name="provider"
          label="Provider"
          rules={[{ required: true }]}
          style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}
        >
          <Input placeholder="Bangkok Hospital" />
        </Form.Item>
        <Form.Item
          name="claim_date"
          label="Claim Date"
          rules={[{ required: true }]}
          style={{ flex: 1, marginBottom: 0, marginLeft: 8 }}
        >
          <Input placeholder="2024-03-15" />
        </Form.Item>
      </Space.Compact>

      {customFields.length > 0 && (
        <>
          <Divider titlePlacement="start" style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Insurer-specific fields
            </Text>
          </Divider>
          {customFields.map((field) => (
            <Form.Item
              key={field.key}
              name={`cf_${field.key}`}
              label={field.label}
              rules={
                field.required
                  ? [{ required: true, message: `${field.label} is required` }]
                  : undefined
              }
            >
              {renderCustomFieldInput(field)}
            </Form.Item>
          ))}
        </>
      )}

      <Form.Item style={{ marginTop: 8, marginBottom: 0 }}>
        <Button
          type="primary"
          htmlType="submit"
          loading={loading}
          icon={<SendOutlined />}
          block
          size="large"
        >
          {loading ? "Submitting Claim..." : "Submit Claim"}
        </Button>
      </Form.Item>
    </Form>
  );
}
