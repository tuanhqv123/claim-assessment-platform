"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Row,
  Col,
  Statistic,
  Flex,
  Divider,
  Typography,
  Spin,
  Alert,
  Tag,
  Table,
  Progress,
  Button,
  App as AntApp,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  DashboardOutlined,
  FileTextOutlined,
  FileSearchOutlined,
  BankOutlined,
  DollarOutlined,
  AppstoreOutlined,
  TeamOutlined,
  BarChartOutlined,
  ClockCircleOutlined,
  FormOutlined,
  AuditOutlined,
  SettingOutlined,
  RightOutlined,
  ArrowRightOutlined,
} from "@ant-design/icons";
import { PageBody } from "@/components/ui/PageHeader";
import { getStats, type PlatformStats, type RecentClaim } from "@/lib/dashboardApi";
import { TENANT_NAME, stateLabel, stateColor } from "@/components/assessor/constants";

const { Text } = Typography;

const TEAL = "#0d9488";

function SectionTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <Flex align="center" gap={8} style={{ marginBottom: 16 }}>
      <span style={{ color: TEAL, fontSize: 15, display: "flex" }}>{icon}</span>
      <Text strong style={{ fontSize: 14 }}>
        {title}
      </Text>
    </Flex>
  );
}

function tenantName(id: string): string {
  return TENANT_NAME[id] ?? id;
}

function fmtAmount(n: number): string {
  return `${Number(n).toLocaleString()} THB`;
}

function fmtDate(s: string): string {
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString();
}

// Progress stroke colors keyed off the AntD tag color used elsewhere.
const STATE_STROKE: Record<string, string> = {
  SUBMITTED: "#8c8c8c",
  DOCUMENTS_VERIFIED: "#13c2c2",
  UNDER_ASSESSMENT: "#1677ff",
  PENDING_INFO: "#faad14",
  APPROVED: "#52c41a",
  REJECTED: "#ff4d4f",
  PAYMENT_INITIATED: "#2f54eb",
  CLOSED: "#bfbfbf",
};

function stateStroke(state: string): string {
  return STATE_STROKE[state] ?? "#8c8c8c";
}

interface QuickLink {
  href: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const QUICK_LINKS: QuickLink[] = [
  {
    href: "/member",
    title: "Submit a Claim",
    description: "Member intake & document upload",
    icon: <FormOutlined />,
  },
  {
    href: "/assessor",
    title: "Review Queue",
    description: "Assess and action open claims",
    icon: <AuditOutlined />,
  },
  {
    href: "/admin",
    title: "Tenant Config",
    description: "Manage insurer configuration",
    icon: <SettingOutlined />,
  },
];

export default function DashboardPage() {
  const { message } = AntApp.useApp();
  const router = useRouter();

  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getStats();
        if (!cancelled) setStats(data);
      } catch (err) {
        const msg = (err as Error).message;
        if (!cancelled) {
          setError(msg);
          message.error(`Failed to load dashboard: ${msg}`);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [message]);

  const recentColumns: ColumnsType<RecentClaim> = [
    {
      title: "Claim #",
      dataIndex: "claim_number",
      key: "claim_number",
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: "Tenant",
      dataIndex: "tenant_id",
      key: "tenant_id",
      render: (id: string) => tenantName(id),
    },
    {
      title: "Type",
      dataIndex: "claim_type",
      key: "claim_type",
      render: (t: string) => <Tag>{t}</Tag>,
    },
    {
      title: "Amount",
      dataIndex: "amount",
      key: "amount",
      align: "right",
      render: (v: number) => fmtAmount(v),
    },
    {
      title: "State",
      dataIndex: "state",
      key: "state",
      render: (s: string) => <Tag color={stateColor(s)}>{stateLabel(s)}</Tag>,
    },
    {
      title: "Created",
      dataIndex: "created_at",
      key: "created_at",
      render: (v: string) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {fmtDate(v)}
        </Text>
      ),
    },
    {
      title: "",
      key: "action",
      align: "right",
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            router.push(`/assessor/${record.id}`);
          }}
        >
          Open <RightOutlined />
        </Button>
      ),
    },
  ];

  if (loading) {
    return (
      <PageBody>
        <Flex justify="center" align="center" style={{ padding: "96px 0" }}>
          <Spin size="large" />
        </Flex>
      </PageBody>
    );
  }

  if (error || !stats) {
    return (
      <PageBody>
        <Alert
          type="error"
          showIcon
          title="Could not load the dashboard"
          description={
            error ??
            "The stats service returned no data. Make sure the API is running."
          }
        />
      </PageBody>
    );
  }

  const stateEntries = Object.entries(stats.by_state).sort(
    (a, b) => b[1] - a[1],
  );
  const stateTotal = stateEntries.reduce((sum, [, n]) => sum + n, 0);
  const tenantMax = Math.max(1, ...stats.by_tenant.map((t) => t.count));

  return (
    <PageBody>
      <Flex align="center" gap={8} style={{ marginBottom: 4 }}>
        <span style={{ color: TEAL, fontSize: 18, display: "flex" }}>
          <DashboardOutlined />
        </span>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Platform Dashboard
        </Typography.Title>
      </Flex>
      <Text type="secondary" style={{ fontSize: 13, display: "block", marginBottom: 24 }}>
        A live overview of claims, documents, and tenants across the platform.
      </Text>

      {/* KPI stats */}
      <Row gutter={0} wrap>
        <Col xs={12} md={6}>
          <div style={{ padding: "4px 24px 4px 0", borderRight: "1px solid #edf0f2" }}>
            <Statistic
              title={
                <Flex align="center" gap={6}>
                  <FileTextOutlined style={{ color: TEAL }} />
                  <span>Total Claims</span>
                </Flex>
              }
              value={stats.total_claims}
              valueStyle={{ color: "#1f2937", fontWeight: 600 }}
            />
          </div>
        </Col>
        <Col xs={12} md={6}>
          <div style={{ padding: "4px 24px", borderRight: "1px solid #edf0f2" }}>
            <Statistic
              title={
                <Flex align="center" gap={6}>
                  <FileSearchOutlined style={{ color: TEAL }} />
                  <span>Documents Processed</span>
                </Flex>
              }
              value={stats.total_documents}
              valueStyle={{ color: "#1f2937", fontWeight: 600 }}
            />
          </div>
        </Col>
        <Col xs={12} md={6}>
          <div style={{ padding: "4px 24px", borderRight: "1px solid #edf0f2" }}>
            <Statistic
              title={
                <Flex align="center" gap={6}>
                  <BankOutlined style={{ color: TEAL }} />
                  <span>Tenants</span>
                </Flex>
              }
              value={stats.total_tenants}
              valueStyle={{ color: "#1f2937", fontWeight: 600 }}
            />
          </div>
        </Col>
        <Col xs={12} md={6}>
          <div style={{ padding: "4px 0 4px 24px" }}>
            <Statistic
              title={
                <Flex align="center" gap={6}>
                  <DollarOutlined style={{ color: TEAL }} />
                  <span>Total Claimed</span>
                </Flex>
              }
              value={stats.total_amount}
              precision={0}
              suffix="THB"
              valueStyle={{ color: TEAL, fontWeight: 600 }}
            />
          </div>
        </Col>
      </Row>

      <Divider titlePlacement="start" style={{ margin: "28px 0 20px" }}>
        <SectionTitle icon={<BarChartOutlined />} title="Claims by State" />
      </Divider>

      {stateEntries.length === 0 ? (
        <Text type="secondary">No claims yet.</Text>
      ) : (
        <Row gutter={[24, 12]}>
          {stateEntries.map(([state, count]) => {
            const pct = stateTotal ? Math.round((count / stateTotal) * 100) : 0;
            return (
              <Col xs={24} md={12} key={state}>
                <Flex align="center" gap={12}>
                  <div style={{ width: 168, flex: "0 0 auto" }}>
                    <Tag color={stateColor(state)} style={{ marginInlineEnd: 0 }}>
                      {stateLabel(state)}
                    </Tag>
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Progress
                      percent={pct}
                      strokeColor={stateStroke(state)}
                      format={() => (
                        <Text style={{ fontSize: 12 }}>{count}</Text>
                      )}
                    />
                  </div>
                </Flex>
              </Col>
            );
          })}
        </Row>
      )}

      <Divider titlePlacement="start" style={{ margin: "28px 0 20px" }}>
        <SectionTitle icon={<TeamOutlined />} title="By Tenant" />
      </Divider>

      {stats.by_tenant.length === 0 ? (
        <Text type="secondary">No tenant activity yet.</Text>
      ) : (
        <Flex vertical gap={10} style={{ maxWidth: 520 }}>
          {stats.by_tenant.map((t) => (
            <Flex key={t.tenant_id} align="center" gap={12}>
              <span style={{ color: TEAL, display: "flex" }}>
                <BankOutlined />
              </span>
              <Text style={{ flex: "0 0 160px" }}>{t.name || tenantName(t.tenant_id)}</Text>
              <div style={{ flex: 1, minWidth: 0 }}>
                <Progress
                  percent={Math.round((t.count / tenantMax) * 100)}
                  strokeColor={TEAL}
                  showInfo={false}
                  size="small"
                />
              </div>
              <Text strong style={{ flex: "0 0 auto", minWidth: 28, textAlign: "right" }}>
                {t.count}
              </Text>
            </Flex>
          ))}
        </Flex>
      )}

      <Divider titlePlacement="start" style={{ margin: "28px 0 20px" }}>
        <SectionTitle icon={<ClockCircleOutlined />} title="Recent Claims" />
      </Divider>

      <Table<RecentClaim>
        rowKey="id"
        columns={recentColumns}
        dataSource={stats.recent}
        pagination={false}
        size="middle"
        locale={{ emptyText: "No recent claims" }}
        onRow={(record) => ({
          onClick: () => router.push(`/assessor/${record.id}`),
          style: { cursor: "pointer" },
        })}
      />

      <Divider titlePlacement="start" style={{ margin: "28px 0 20px" }}>
        <SectionTitle icon={<AppstoreOutlined />} title="Quick Links" />
      </Divider>

      <Row gutter={[16, 16]}>
        {QUICK_LINKS.map((link) => (
          <Col xs={24} sm={12} lg={6} key={link.href}>
            <div
              role="button"
              tabIndex={0}
              onClick={() => router.push(link.href)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") router.push(link.href);
              }}
              style={{
                cursor: "pointer",
                border: "1px solid #edf0f2",
                borderRadius: 12,
                padding: "18px 18px",
                height: "100%",
                transition: "border-color 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = TEAL;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "#edf0f2";
              }}
            >
              <Flex
                align="center"
                justify="center"
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  background: "#e6f4f2",
                  color: TEAL,
                  fontSize: 19,
                  marginBottom: 12,
                }}
              >
                {link.icon}
              </Flex>
              <Flex align="center" justify="space-between" gap={8}>
                <Text strong style={{ fontSize: 14 }}>
                  {link.title}
                </Text>
                <ArrowRightOutlined style={{ color: TEAL, fontSize: 12 }} />
              </Flex>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {link.description}
              </Text>
            </div>
          </Col>
        ))}
      </Row>
    </PageBody>
  );
}
