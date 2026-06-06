"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Descriptions,
  Typography,
  Tag,
  Button,
  Space,
  Spin,
  Result,
  Empty,
  Divider,
  Flex,
  App,
} from "antd";
import {
  ThunderboltOutlined,
  ReloadOutlined,
  FileSearchOutlined,
  ProfileOutlined,
} from "@ant-design/icons";
import {
  getClaim,
  runAssessmentStream,
  type ClaimDetail as ClaimDetailType,
  type AssessmentRecord,
  type AssessStepEvent,
  type Role,
  ApiError,
} from "@/lib/assessorApi";
import { AssessmentReport, ToolCallTimeline, RecommendationBadge } from "@/components";
import type { Recommendation } from "@/constants";
import { TENANT_NAME, stateLabel, stateColor } from "./constants";
import DocumentsPanel from "./DocumentsPanel";
import WorkflowPanel from "./WorkflowPanel";
import GuardFlags from "./GuardFlags";
import AssessmentSteps from "./AssessmentSteps";

interface Props {
  claimId: string;
  role: Role;
}

function fmtDate(s: string | null): string {
  if (!s) return "—";
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString();
}

function SectionTitle({
  icon,
  title,
  extra,
}: {
  icon: React.ReactNode;
  title: string;
  extra?: React.ReactNode;
}) {
  return (
    <Flex align="center" justify="space-between" gap={8} style={{ marginBottom: 16 }}>
      <Flex align="center" gap={8}>
        <span style={{ color: "#0d9488", fontSize: 15, display: "flex" }}>{icon}</span>
        <Typography.Text strong style={{ fontSize: 14, whiteSpace: "nowrap" }}>
          {title}
        </Typography.Text>
      </Flex>
      {extra}
    </Flex>
  );
}

export default function ClaimDetail({ claimId, role }: Props) {
  const { message } = App.useApp();
  const [detail, setDetail] = useState<ClaimDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [assessing, setAssessing] = useState(false);
  const [steps, setSteps] = useState<AssessStepEvent[]>([]);
  const [freshAssessment, setFreshAssessment] = useState<AssessmentRecord | null>(
    null,
  );

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await getClaim(claimId);
      setDetail(data);
    } catch (err) {
      setLoadError(
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Failed to load claim",
      );
    } finally {
      setLoading(false);
    }
  }, [claimId]);

  useEffect(() => {
    load();
  }, [load]);

  // Refresh only the workflow/transitions section in the background (no spinner,
  // no report reset) after a streamed assessment changes claim state.
  const refreshWorkflow = useCallback(async () => {
    try {
      const data = await getClaim(claimId);
      setDetail((prev) =>
        prev
          ? {
              ...prev,
              claim: data.claim,
              transitions: data.transitions,
              available_transitions: data.available_transitions,
            }
          : data,
      );
    } catch {
      // Non-fatal: the streamed report is already shown.
    }
  }, [claimId]);

  const handleAssess = async () => {
    setAssessing(true);
    setSteps([]);
    setFreshAssessment(null);
    try {
      const res = await runAssessmentStream(claimId, (ev) => {
        setSteps((prev) => [...prev, ev]);
      });
      // Render the report straight from the stream — no whole-claim refetch.
      setFreshAssessment({
        recommendation: res.recommendation,
        recommendation_reason: res.recommendation_reason,
        report: res.report,
        tool_call_log: res.tool_call_log,
        guard_flags: res.guard_flags,
      });
      message.success("Assessment complete");
      // Refresh workflow/transitions in place (state may have advanced).
      refreshWorkflow();
    } catch (err) {
      const msg =
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Assessment failed";
      message.error(msg);
    } finally {
      setAssessing(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 64 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (loadError || !detail) {
    return (
      <Result
        status="error"
        title="Could not load claim"
        subTitle={loadError ?? "Unknown error"}
        extra={
          <Button icon={<ReloadOutlined />} onClick={load}>
            Retry
          </Button>
        }
      />
    );
  }

  const { claim, documents, transitions, available_transitions } = detail;
  // Prefer the just-run assessment, else the persisted one from the detail.
  const assessment = freshAssessment ?? detail.assessment;

  return (
    <Flex align="flex-start" gap={32} wrap="wrap">
      <div style={{ flex: "1 1 560px", minWidth: 0 }}>
        <Flex align="center" gap={10} wrap="wrap" style={{ marginBottom: 16 }}>
          <Typography.Text strong style={{ fontSize: 18 }}>
            {claim.claim_number}
          </Typography.Text>
          <Tag color={stateColor(claim.state)}>{stateLabel(claim.state)}</Tag>
          {assessment?.recommendation && (
            <RecommendationBadge
              value={assessment.recommendation as Recommendation}
              size="small"
            />
          )}
        </Flex>

        <Descriptions column={{ xs: 1, sm: 2 }} size="small">
            <Descriptions.Item label="Tenant">
              {TENANT_NAME[claim.tenant_id] ?? claim.tenant_id}
            </Descriptions.Item>
            <Descriptions.Item label="Policy">
              {claim.policy_id ?? "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Member">
              {claim.member_id ?? "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Type">
              <Tag>{claim.claim_type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Sub-benefit">
              {claim.sub_benefit ?? "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Amount">
              <Typography.Text strong>
                {Number(claim.amount).toLocaleString()} THB
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Claim date">
              {fmtDate(claim.claim_date)}
            </Descriptions.Item>
            <Descriptions.Item label="Provider">
              {claim.provider ?? "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Diagnosis">
              {claim.diagnosis_code ? <Tag>{claim.diagnosis_code}</Tag> : null}{" "}
              {claim.diagnosis_description ?? "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Procedure codes">
              {claim.procedure_codes?.length
                ? claim.procedure_codes.map((p) => <Tag key={p}>{p}</Tag>)
                : "—"}
            </Descriptions.Item>
            <Descriptions.Item label="SLA deadline">
              {fmtDate(claim.sla_deadline)}
            </Descriptions.Item>
          <Descriptions.Item label="Info requests">
            {claim.info_request_count}
          </Descriptions.Item>
        </Descriptions>

        <Divider style={{ margin: "28px 0" }} />

        <SectionTitle icon={<FileSearchOutlined />} title="Documents & OCR" />
        <DocumentsPanel documents={documents} />

        <Divider style={{ margin: "28px 0" }} />

        <SectionTitle
          icon={<ProfileOutlined />}
          title="Assessment"
          extra={
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              loading={assessing}
              onClick={handleAssess}
            >
              {assessment ? "Re-run assessment" : "Run assessment"}
            </Button>
          }
        />
        <div>
          {assessing && (
            <div style={{ padding: "8px 0 16px" }}>
              <Typography.Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
                Agent is assessing the claim — steps appear live as each tool runs.
              </Typography.Text>
              <AssessmentSteps steps={steps} active={assessing} />
            </div>
          )}

          {!assessing && !assessment && (
            <Empty description="No assessment yet. Run the agent to generate a report." />
          )}

          {!assessing && assessment && (
            <Space direction="vertical" size={16} style={{ width: "100%" }}>
              {assessment.recommendation && (
                <Space>
                  <RecommendationBadge
                    value={assessment.recommendation as Recommendation}
                  />
                  <Typography.Text type="secondary">
                    {assessment.recommendation_reason}
                  </Typography.Text>
                </Space>
              )}

              <div>
                <Typography.Text strong>Guard flags</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <GuardFlags flags={assessment.guard_flags ?? null} />
                </div>
              </div>

              {assessment.report && (
                <div>
                  <Typography.Text strong>Report</Typography.Text>
                  <div style={{ marginTop: 8 }}>
                    <AssessmentReport report={assessment.report} />
                  </div>
                </div>
              )}

              {assessment.tool_call_log && assessment.tool_call_log.length > 0 && (
                <div>
                  <Typography.Text strong>
                    Agent activity ({assessment.tool_call_log.length} tool calls)
                  </Typography.Text>
                  <div style={{ marginTop: 8 }}>
                    <ToolCallTimeline entries={assessment.tool_call_log} />
                  </div>
                </div>
              )}
            </Space>
          )}
        </div>
      </div>

      <div
        style={{
          flex: "1 1 340px",
          flexGrow: 0,
          minWidth: 320,
          maxWidth: 380,
        }}
      >
        <WorkflowPanel
          claimId={claimId}
          currentState={claim.state}
          audit={transitions}
          available={available_transitions}
          role={role}
          onTransitioned={load}
        />
      </div>
    </Flex>
  );
}
