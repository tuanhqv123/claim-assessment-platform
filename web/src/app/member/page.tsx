"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Flex, Spin, Alert, Divider, Typography, Button, App as AntApp } from "antd";
import { FormOutlined, ThunderboltOutlined, ArrowLeftOutlined, AuditOutlined } from "@ant-design/icons";
import { PageBody } from "@/components/ui/PageHeader";
import {
  listTenants,
  getActiveConfig,
  createClaim,
  attachDocument,
  previewClaim,
  type TenantSummary,
  type TenantConfig,
  type ClaimRow,
  type RuntimePreview,
  type DocumentRow,
} from "@/lib/memberApi";
import {
  TenantPicker,
  ClaimSubmitForm,
  DocumentUploadCard,
  ClaimConfirmation,
  RequiredDocsChecklist,
  type ClaimFormValues,
  type UploadedDoc,
} from "@/components/member";
import { deriveClaimPrefill } from "@/components/member/ocrAutofill";
import { listPolicies, type PolicySummary } from "@/lib/policyApi";
import { listMembers } from "@/lib/membersDirectoryApi";

const { Text } = Typography;

function SectionTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <Flex align="center" gap={8} style={{ marginBottom: 16 }}>
      <span style={{ color: "#0d9488", fontSize: 15, display: "flex" }}>{icon}</span>
      <Text strong style={{ fontSize: 14 }}>
        {title}
      </Text>
    </Flex>
  );
}

export default function MemberPage() {
  const { message } = AntApp.useApp();
  const router = useRouter();

  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [tenantsLoading, setTenantsLoading] = useState(true);
  const [tenantId, setTenantId] = useState<string | undefined>();

  const [config, setConfig] = useState<TenantConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(false);

  const [policies, setPolicies] = useState<PolicySummary[]>([]);
  const [memberNames, setMemberNames] = useState<Record<string, string>>({});

  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);

  // Live-selected claim type (from the form's Select / prefill), used to drive
  // the required-documents checklist before the claim is submitted.
  const [selectedClaimType, setSelectedClaimType] = useState<string | undefined>();

  // OCR-classified document types of everything uploaded so far.
  const uploadedTypes = useMemo(
    () => uploadedDocs.map((d) => d.result.document_type),
    [uploadedDocs],
  );

  // Derive a claim-form prefill from the first OCR-extracted document.
  const prefillSource = useMemo(() => {
    const firstDoc = uploadedDocs.find((d) => d.result);
    if (!firstDoc) return null;
    const prefill = deriveClaimPrefill(firstDoc.result);
    if (Object.keys(prefill).length === 0) return null;
    return { prefill, fileName: firstDoc.fileName };
  }, [uploadedDocs]);

  const [submitting, setSubmitting] = useState(false);
  const [claim, setClaim] = useState<ClaimRow | null>(null);
  const [preview, setPreview] = useState<RuntimePreview | null>(null);

  const [attached, setAttached] = useState<DocumentRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await listTenants();
        if (!cancelled) setTenants(list);
      } catch (err) {
        if (!cancelled) message.error(`Failed to load insurers: ${(err as Error).message}`);
      } finally {
        if (!cancelled) setTenantsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [message]);

  const handleTenantChange = (next: string) => {
    setConfig(null);
    setClaim(null);
    setPreview(null);
    setAttached([]);
    setUploadedDocs([]);
    setSelectedClaimType(undefined);
    setConfigLoading(true);
    setTenantId(next);
  };

  useEffect(() => {
    if (!tenantId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await getActiveConfig(tenantId);
        if (!cancelled) setConfig(res.config);
      } catch (err) {
        if (!cancelled) message.error(`Failed to load tenant config: ${(err as Error).message}`);
      } finally {
        if (!cancelled) setConfigLoading(false);
      }
      // Policies (for the Policy dropdown) + member directory (for nicer labels).
      try {
        const [pols, mems] = await Promise.all([
          listPolicies(tenantId),
          listMembers(tenantId),
        ]);
        if (!cancelled) {
          setPolicies(pols);
          setMemberNames(
            Object.fromEntries(
              mems.map((m) => [m.member_code || "", m.full_name || ""]),
            ),
          );
        }
      } catch {
        if (!cancelled) {
          setPolicies([]);
          setMemberNames({});
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tenantId, message]);

  const handleSubmit = async (values: ClaimFormValues) => {
    if (!tenantId) return;
    setSubmitting(true);
    try {
      const procedureCodes = values.procedure_codes
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const claimPayload = {
        policy_number: values.policy_number,
        member_id: values.member_id,
        claim_type: values.claim_type,
        sub_benefit: values.sub_benefit,
        diagnosis_code: values.diagnosis_code,
        diagnosis_description: values.diagnosis_description,
        procedure_codes: procedureCodes,
        amount: values.amount,
        claim_date: values.claim_date,
        provider: values.provider,
        custom_fields: values.custom_fields,
      };
      const created = await createClaim({ tenant_id: tenantId, ...claimPayload });
      setClaim(created);
      message.success(`Claim ${created.claim_number} created`);

      // Auto-attach the uploaded documents so the assessor sees them right away
      // (no separate manual "attach" step needed).
      if (uploadedDocs.length > 0) {
        try {
          const rows: DocumentRow[] = [];
          for (const doc of uploadedDocs) {
            rows.push(await attachDocument(created.id, doc.file));
          }
          setAttached(rows);
        } catch (err) {
          message.warning(
            `Some documents could not be attached: ${(err as Error).message}`,
          );
        }
      }

      try {
        const pv = await previewClaim(tenantId, claimPayload);
        setPreview(pv);
      } catch (err) {
        message.warning(`Could not load routing preview: ${(err as Error).message}`);
        setPreview(null);
      }
    } catch (err) {
      message.error(`Submission failed: ${(err as Error).message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setClaim(null);
    setPreview(null);
    setAttached([]);
    setUploadedDocs([]);
  };

  // After submit: show the confirmation as its own screen (not below the form).
  if (claim) {
    return (
      <PageBody>
        <Flex vertical gap={16}>
          <Flex align="center" justify="space-between" wrap="wrap" gap={8}>
            <Button icon={<ArrowLeftOutlined />} onClick={handleReset}>
              Submit another claim
            </Button>
            <Button
              type="link"
              icon={<AuditOutlined />}
              onClick={() => router.push(`/assessor/${claim.id}`)}
            >
              View in Assessor
            </Button>
          </Flex>
          <ClaimConfirmation
            claim={claim}
            preview={preview}
            uploadedDocs={uploadedDocs}
            attached={attached}
          />
        </Flex>
      </PageBody>
    );
  }

  return (
    <PageBody>
      <Flex vertical gap={16}>
        <TenantPicker
          tenants={tenants}
          loading={tenantsLoading}
          value={tenantId}
          onChange={handleTenantChange}
        />

        {tenantId ? (
          <div style={{ display: "flex", alignItems: "stretch" }}>
            <div style={{ flex: "1 1 340px", minWidth: 0, paddingInlineEnd: 28 }}>
              <SectionTitle icon={<FormOutlined />} title="Claim Details" />
              {prefillSource && (
                <Text
                  style={{ fontSize: 12, color: "#0d9488", display: "block", marginBottom: 12 }}
                >
                  <ThunderboltOutlined /> Auto-filled from {prefillSource.fileName} — review &amp; edit.
                </Text>
              )}
              {configLoading ? (
                <Flex justify="center" style={{ padding: 32 }}>
                  <Spin />
                </Flex>
              ) : config ? (
                <ClaimSubmitForm
                  key={tenantId}
                  claimTypes={config.claim_types}
                  customFields={config.custom_fields}
                  loading={submitting}
                  onSubmit={handleSubmit}
                  prefill={prefillSource?.prefill}
                  onClaimTypeChange={setSelectedClaimType}
                  policies={policies}
                  memberNames={memberNames}
                />
              ) : (
                <Alert type="warning" showIcon title="Tenant configuration unavailable." />
              )}
            </div>

            <Divider type="vertical" style={{ height: "auto", margin: 0, alignSelf: "stretch" }} />

            <div style={{ flex: "1.6 1 440px", minWidth: 0, paddingInlineStart: 28 }}>
              <div style={{ marginBottom: 16 }}>
                <RequiredDocsChecklist
                  tenantId={tenantId}
                  claimType={selectedClaimType}
                  uploadedTypes={uploadedTypes}
                />
              </div>
              <DocumentUploadCard onDocsChange={setUploadedDocs} />
            </div>
          </div>
        ) : (
          !tenantsLoading && (
            <Alert
              type="info"
              showIcon
              title="Select an insurer to begin"
              description="Pick an insurer above to load its claim types, custom fields, and document requirements."
            />
          )
        )}
      </Flex>
    </PageBody>
  );
}
