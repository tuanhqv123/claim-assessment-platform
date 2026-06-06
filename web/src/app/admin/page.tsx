"use client";

import { useCallback, useEffect, useState } from "react";
import {
  App,
  Flex,
  Typography,
  Tabs,
  Select,
  Space,
  Tag,
  Spin,
  Row,
  Col,
  Empty,
} from "antd";
import {
  PlusOutlined,
  ExperimentOutlined,
  SwapOutlined,
  HistoryOutlined,
  FormOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { PageBody } from "@/components/ui/PageHeader";
import {
  TenantConfigForm,
  ConfigPreview,
  ConfigDiff,
  VersionHistory,
  PoliciesPanel,
  MembersPanel,
} from "@/components/admin";
import {
  listTenants,
  getActiveConfig,
  listConfigVersions,
  saveConfig,
  rollbackConfig,
  previewClaim,
  diffConfigs,
  createTenant,
  blankConfig,
  ApiError,
  type TenantSummary,
  type TenantConfig,
  type ConfigVersionMeta,
  type PreviewResult,
  type PreviewClaim,
  type DiffEntry,
} from "@/lib/adminApi";

const { Text } = Typography;

/** Small bold section title on white, with optional right-aligned controls. */
function SectionTitle({
  icon,
  title,
  extra,
}: {
  icon?: React.ReactNode;
  title: string;
  extra?: React.ReactNode;
}) {
  return (
    <Flex align="center" justify="space-between" wrap="wrap" gap={12} style={{ marginBottom: 16 }}>
      <Flex align="center" gap={8}>
        {icon && <span style={{ color: "#0d9488", fontSize: 15, display: "flex" }}>{icon}</span>}
        <Text strong style={{ fontSize: 14 }}>
          {title}
        </Text>
      </Flex>
      {extra && <div>{extra}</div>}
    </Flex>
  );
}

function errMessages(e: unknown): string[] {
  if (e instanceof ApiError) {
    return e.errors.length > 0 ? e.errors : [e.message];
  }
  if (e instanceof Error) return [e.message];
  return [String(e)];
}

function AdminConsole() {
  const { message } = App.useApp();

  // --- Tenant list ---
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [tenantsLoading, setTenantsLoading] = useState(true);

  // --- Edit / config tab ---
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  const [activeConfig, setActiveConfig] = useState<TenantConfig | null>(null);
  const [activeVersion, setActiveVersion] = useState<number | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveErrors, setSaveErrors] = useState<string[]>([]);

  // --- Versions ---
  const [versions, setVersions] = useState<ConfigVersionMeta[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);

  // --- Preview ---
  const [previewTenantId, setPreviewTenantId] = useState<string | null>(null);
  const [previewConfig, setPreviewConfig] = useState<TenantConfig | null>(null);
  const [previewConfigLoading, setPreviewConfigLoading] = useState(false);
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [previewRunning, setPreviewRunning] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // --- Diff ---
  const [diffA, setDiffA] = useState<string | null>(null);
  const [diffB, setDiffB] = useState<string | null>(null);
  const [diff, setDiff] = useState<DiffEntry[] | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);

  // --- Create ---
  const [creating, setCreating] = useState(false);
  const [createErrors, setCreateErrors] = useState<string[]>([]);

  // ------------------------------------------------------------------
  // Loaders
  // ------------------------------------------------------------------

  const refreshTenants = useCallback(async (): Promise<TenantSummary[]> => {
    setTenantsLoading(true);
    try {
      const list = await listTenants();
      setTenants(list);
      return list;
    } catch (e) {
      message.error(`Failed to load tenants: ${errMessages(e).join("; ")}`);
      return [];
    } finally {
      setTenantsLoading(false);
    }
  }, [message]);

  const loadConfigFor = useCallback(
    async (tenantId: string) => {
      setConfigLoading(true);
      setActiveConfig(null);
      setSaveErrors([]);
      try {
        const res = await getActiveConfig(tenantId);
        setActiveConfig(res.config);
        setActiveVersion(res.version);
      } catch (e) {
        message.error(`Failed to load config: ${errMessages(e).join("; ")}`);
      } finally {
        setConfigLoading(false);
      }
    },
    [message],
  );

  const loadVersions = useCallback(
    async (tenantId: string) => {
      setVersionsLoading(true);
      try {
        const v = await listConfigVersions(tenantId);
        setVersions(v);
      } catch (e) {
        message.error(`Failed to load versions: ${errMessages(e).join("; ")}`);
      } finally {
        setVersionsLoading(false);
      }
    },
    [message],
  );

  // Data-fetch effects: these synchronize React state with an external API on
  // mount / dependency change. setState here is intentional (loading flags +
  // fetched data), so the set-state-in-effect heuristic is suppressed.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refreshTenants().then((list) => {
      if (list.length > 0) setSelectedTenantId(list[0].id);
    });
  }, [refreshTenants]);

  // Load active config + versions when the selected tenant changes.
  useEffect(() => {
    if (selectedTenantId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadConfigFor(selectedTenantId);
      loadVersions(selectedTenantId);
    }
  }, [selectedTenantId, loadConfigFor, loadVersions]);

  // Load the preview tenant's active config so the preview form knows the
  // enabled claim types + custom fields.
  useEffect(() => {
    if (!previewTenantId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPreviewConfig(null);
      return;
    }
    setPreviewConfigLoading(true);
    setPreviewResult(null);
    setPreviewError(null);
    getActiveConfig(previewTenantId)
      .then((res) => setPreviewConfig(res.config))
      .catch((e) =>
        message.error(`Failed to load tenant config: ${errMessages(e).join("; ")}`),
      )
      .finally(() => setPreviewConfigLoading(false));
  }, [previewTenantId, message]);

  // ------------------------------------------------------------------
  // Actions
  // ------------------------------------------------------------------

  const handleSave = async (config: TenantConfig) => {
    if (!selectedTenantId) return;
    setSaving(true);
    setSaveErrors([]);
    try {
      const res = await saveConfig(selectedTenantId, config);
      setActiveConfig(res.config);
      setActiveVersion(res.version);
      message.success(`Saved configuration as version ${res.version}`);
      await Promise.all([loadVersions(selectedTenantId), refreshTenants()]);
    } catch (e) {
      const msgs = errMessages(e);
      if (e instanceof ApiError && e.status === 422) {
        setSaveErrors(msgs);
        message.error("Configuration rejected — see validation errors.");
      } else {
        message.error(`Save failed: ${msgs.join("; ")}`);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleRollback = async (version: number) => {
    if (!selectedTenantId) return;
    setRollingBack(true);
    try {
      const res = await rollbackConfig(selectedTenantId, version);
      setActiveConfig(res.config);
      setActiveVersion(res.version);
      message.success(`Rolled back to version ${version} (new version ${res.version})`);
      await Promise.all([loadVersions(selectedTenantId), refreshTenants()]);
    } catch (e) {
      message.error(`Rollback failed: ${errMessages(e).join("; ")}`);
    } finally {
      setRollingBack(false);
    }
  };

  const handleViewVersion = useCallback(
    async (version: number): Promise<TenantConfig> => {
      // The contract's /config/versions endpoint returns metadata; some
      // backends also include the per-version `config` body, which we prefer.
      // For the active version we can always fetch the body via /config.
      const meta = versions.find((v) => v.version === version);
      if (meta?.config) return meta.config;
      if (!selectedTenantId) throw new Error("No tenant selected");
      const res = await getActiveConfig(selectedTenantId);
      if (res.version === version) return res.config;
      throw new Error(
        `Version ${version} body is not available from the API ` +
          `(only metadata is returned). Roll back to inspect it.`,
      );
    },
    [versions, selectedTenantId],
  );

  const handlePreview = async (claim: PreviewClaim) => {
    if (!previewTenantId) return;
    setPreviewRunning(true);
    setPreviewError(null);
    setPreviewResult(null);
    try {
      const res = await previewClaim(previewTenantId, claim);
      setPreviewResult(res);
    } catch (e) {
      setPreviewError(errMessages(e).join("; "));
    } finally {
      setPreviewRunning(false);
    }
  };

  const handleDiff = async () => {
    if (!diffA || !diffB) return;
    setDiffLoading(true);
    setDiffError(null);
    setDiff(null);
    try {
      const res = await diffConfigs(diffA, diffB);
      setDiff(res);
    } catch (e) {
      setDiffError(errMessages(e).join("; "));
    } finally {
      setDiffLoading(false);
    }
  };

  const handleCreate = async (config: TenantConfig, meta: { slug?: string; name?: string }) => {
    setCreating(true);
    setCreateErrors([]);
    try {
      await createTenant({ slug: meta.slug ?? "", name: meta.name ?? "", config });
      message.success(`Tenant "${meta.name}" onboarded`);
      const list = await refreshTenants();
      // Select the freshly created tenant in the edit tab.
      const created = list.find((t) => t.slug === meta.slug);
      if (created) setSelectedTenantId(created.id);
    } catch (e) {
      const msgs = errMessages(e);
      if (e instanceof ApiError && e.status === 422) {
        setCreateErrors(msgs);
        message.error("Tenant config rejected — see validation errors.");
      } else {
        message.error(`Create failed: ${msgs.join("; ")}`);
      }
    } finally {
      setCreating(false);
    }
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  const tenantOptions = tenants.map((t) => ({ value: t.id, label: t.name }));

  return (
    <PageBody>
      <Tabs
        defaultActiveKey="edit"
        items={[
            // ===== Configure / CRUD =====
            {
              key: "edit",
              label: (
                <Space>
                  <FormOutlined />
                  Configure
                </Space>
              ),
              children: (
                <Row gutter={40}>
                  <Col span={24} xl={16}>
                    <SectionTitle
                      icon={<FormOutlined />}
                      title="Tenant Configuration"
                      extra={
                        <Space>
                          <Text type="secondary">Tenant:</Text>
                          <Select
                            style={{ width: 220 }}
                            placeholder="Select a tenant"
                            loading={tenantsLoading}
                            value={selectedTenantId ?? undefined}
                            onChange={setSelectedTenantId}
                            options={tenantOptions}
                          />
                          {activeVersion !== null && (
                            <Tag color="blue">v{activeVersion} active</Tag>
                          )}
                        </Space>
                      }
                    />
                    {configLoading ? (
                      <div style={{ textAlign: "center", padding: 48 }}>
                        <Spin />
                      </div>
                    ) : activeConfig ? (
                      <TenantConfigForm
                        key={`${selectedTenantId}:${activeVersion}`}
                        initialConfig={activeConfig}
                        saving={saving}
                        backendErrors={saveErrors}
                        onSubmit={(cfg) => handleSave(cfg)}
                        submitLabel="Save New Version"
                      />
                    ) : (
                      <Empty description="Select a tenant to edit its configuration." />
                    )}
                  </Col>
                  <Col span={24} xl={8}>
                    <SectionTitle icon={<HistoryOutlined />} title="Configuration History" />
                    {selectedTenantId ? (
                      <VersionHistory
                        versions={versions}
                        loading={versionsLoading}
                        rollingBack={rollingBack}
                        onViewVersion={handleViewVersion}
                        onRollback={handleRollback}
                      />
                    ) : (
                      <Empty description="Select a tenant." />
                    )}
                  </Col>
                </Row>
              ),
            },
            // ===== Policies & members =====
            {
              key: "policies",
              label: (
                <Space>
                  <SafetyCertificateOutlined />
                  Policies
                </Space>
              ),
              children: (
                <>
                  <SectionTitle
                    icon={<SafetyCertificateOutlined />}
                    title="Policies, Members & Documents"
                  />
                  <PoliciesPanel
                    tenants={tenants.map((t) => ({ id: t.id, name: t.name }))}
                    loadingTenants={tenantsLoading}
                  />
                </>
              ),
            },
            // ===== Members directory =====
            {
              key: "members",
              label: (
                <Space>
                  <TeamOutlined />
                  Members
                </Space>
              ),
              children: (
                <>
                  <SectionTitle
                    icon={<TeamOutlined />}
                    title="Members Directory"
                  />
                  <MembersPanel
                    tenants={tenants.map((t) => ({ id: t.id, name: t.name }))}
                    loadingTenants={tenantsLoading}
                  />
                </>
              ),
            },
            // ===== Create tenant =====
            {
              key: "create",
              label: (
                <Space>
                  <PlusOutlined />
                  Create Tenant
                </Space>
              ),
              children: (
                <>
                  <SectionTitle icon={<PlusOutlined />} title="Onboard a New Tenant (zero code)" />
                  <TenantConfigForm
                    initialConfig={blankConfig()}
                    isCreate
                    saving={creating}
                    backendErrors={createErrors}
                    onSubmit={handleCreate}
                    submitLabel="Create Tenant"
                  />
                </>
              ),
            },
            // ===== Preview =====
            {
              key: "preview",
              label: (
                <Space>
                  <ExperimentOutlined />
                  Preview
                </Space>
              ),
              children: (
                <ConfigPreview
                  tenants={tenants}
                  activeConfig={previewConfig}
                  selectedTenantId={previewTenantId}
                  onSelectTenant={setPreviewTenantId}
                  loadingConfig={previewConfigLoading}
                  running={previewRunning}
                  result={previewResult}
                  error={previewError}
                  onPreview={handlePreview}
                />
              ),
            },
            // ===== Diff =====
            {
              key: "diff",
              label: (
                <Space>
                  <SwapOutlined />
                  Diff
                </Space>
              ),
              children: (
                <ConfigDiff
                  tenants={tenants}
                  tenantA={diffA}
                  tenantB={diffB}
                  onSelectA={setDiffA}
                  onSelectB={setDiffB}
                  onRun={handleDiff}
                  loading={diffLoading}
                  diff={diff}
                  error={diffError}
                />
              ),
            },
            // ===== History (dedicated, full-width) =====
            {
              key: "history",
              label: (
                <Space>
                  <HistoryOutlined />
                  History
                </Space>
              ),
              children: (
                <>
                  <SectionTitle
                    icon={<HistoryOutlined />}
                    title="Configuration History & Rollback"
                    extra={
                      <Space>
                        <Text type="secondary">Tenant:</Text>
                        <Select
                          style={{ width: 220 }}
                          placeholder="Select a tenant"
                          loading={tenantsLoading}
                          value={selectedTenantId ?? undefined}
                          onChange={setSelectedTenantId}
                          options={tenantOptions}
                        />
                      </Space>
                    }
                  />
                  {selectedTenantId ? (
                    <VersionHistory
                      versions={versions}
                      loading={versionsLoading}
                      rollingBack={rollingBack}
                      onViewVersion={handleViewVersion}
                      onRollback={handleRollback}
                    />
                  ) : (
                    <Empty description="Select a tenant to view its history." />
                  )}
                </>
              ),
            },
          ]}
        />
    </PageBody>
  );
}

export default function AdminPage() {
  // Wrap in AntD App for context-aware message/notification (AntD v6).
  return (
    <App>
      <AdminConsole />
    </App>
  );
}
