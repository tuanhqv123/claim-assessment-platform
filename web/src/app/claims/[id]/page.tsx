"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Layout,
  Card,
  Descriptions,
  Typography,
  Tag,
  Button,
  Space,
  Spin,
  Tabs,
  Row,
  Col,
} from "antd";
import { ArrowLeftOutlined, MedicineBoxOutlined } from "@ant-design/icons";
import { CLAIM_TYPE_LABEL, CLAIM_TYPE_COLOR } from "@/constants";
import type { ClaimInput } from "@/types";
import type { AssessmentResult } from "@/types";
import type { ClaimType } from "@/constants";
import { RecommendationBadge, AssessmentReport, ToolCallTimeline } from "@/components";

const { Header, Content } = Layout;

const CASE_FILES: Record<string, { claim: string; result: string }> = {
  "1": { claim: "/data/claim_1.json", result: "/data/case_1_approve.json" },
  "2": { claim: "/data/claim_2.json", result: "/data/case_2_reject.json" },
  "3": { claim: "/data/claim_3.json", result: "/data/case_3_request_info.json" },
};

export default function ClaimDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [claim, setClaim] = useState<ClaimInput | null>(null);
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const files = CASE_FILES[id];
    if (!files) {
      setLoading(false);
      return;
    }

    Promise.all([
      fetch(files.claim).then((r) => r.json()),
      fetch(files.result).then((r) => r.json()),
    ]).then(([c, r]) => {
      setClaim(c);
      setResult(r);
      setLoading(false);
    });
  }, [id]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!claim || !result) {
    return (
      <div style={{ padding: 48, textAlign: "center" }}>
        <Typography.Title level={3}>Claim not found</Typography.Title>
        <Button onClick={() => router.push("/")}>Back to Queue</Button>
      </div>
    );
  }

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "0 24px",
        }}
      >
        <MedicineBoxOutlined style={{ fontSize: 20, color: "#1677ff" }} />
        <Typography.Title level={4} style={{ margin: 0 }}>
          Claims Assessment
        </Typography.Title>
      </Header>

      <Content style={{ padding: 24, background: "#f5f5f5" }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => router.push("/")}
          style={{ marginBottom: 16 }}
        >
          Back to Queue
        </Button>

        <Row gutter={24}>
          <Col span={24} lg={16}>
            <Card
              title={
                <Space>
                  <Typography.Text strong style={{ fontSize: 18 }}>
                    {claim.claim_id}
                  </Typography.Text>
                  <RecommendationBadge value={result.recommendation} />
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              <Descriptions column={{ xs: 1, sm: 2 }} size="small">
                <Descriptions.Item label="Policy">{claim.policy_id}</Descriptions.Item>
                <Descriptions.Item label="Member">{claim.member_id}</Descriptions.Item>
                <Descriptions.Item label="Type">
                  <Tag color={CLAIM_TYPE_COLOR[claim.claim_type as ClaimType]}>
                    {CLAIM_TYPE_LABEL[claim.claim_type as ClaimType]}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Sub-benefit">{claim.sub_benefit}</Descriptions.Item>
                <Descriptions.Item label="Amount">
                  <Typography.Text strong>{claim.amount.toLocaleString()} THB</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label="Date">{claim.claim_date}</Descriptions.Item>
                <Descriptions.Item label="Provider">{claim.provider}</Descriptions.Item>
                <Descriptions.Item label="Diagnosis">
                  <Tag>{claim.diagnosis_code}</Tag> {claim.diagnosis_description}
                </Descriptions.Item>
              </Descriptions>

              <div style={{ marginTop: 16, padding: "12px 16px", background: "#fafafa", borderRadius: 8 }}>
                <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                  {result.recommendation_reason}
                </Typography.Text>
              </div>
            </Card>

            <Card title="Assessment Report">
              <AssessmentReport report={result.report} />
            </Card>
          </Col>

          <Col span={24} lg={8}>
            <Card title="Agent Activity Log" style={{ marginBottom: 24 }}>
              <Typography.Text type="secondary" style={{ display: "block", marginBottom: 16, fontSize: 13 }}>
                {result.tool_call_log.length} tool calls executed
              </Typography.Text>
              <ToolCallTimeline entries={result.tool_call_log} />
            </Card>

            <Card title="Actions">
              <Space direction="vertical" style={{ width: "100%" }}>
                <Button type="primary" block disabled={result.recommendation !== "APPROVE"}>
                  Confirm Approval
                </Button>
                <Button danger block disabled={result.recommendation === "APPROVE"}>
                  Override Decision
                </Button>
                <Button block>
                  Request Additional Review
                </Button>
              </Space>
            </Card>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
}
