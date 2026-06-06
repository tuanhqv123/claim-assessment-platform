"use client";

import { useState } from "react";
import {
  List,
  Tag,
  Button,
  Flex,
  Space,
  Spin,
  Typography,
  Modal,
  Popconfirm,
  Empty,
  Alert,
} from "antd";
import { EyeOutlined, RollbackOutlined } from "@ant-design/icons";
import type { ConfigVersionMeta, TenantConfig } from "@/lib/adminApi";

const { Text } = Typography;

interface Props {
  versions: ConfigVersionMeta[];
  loading?: boolean;
  rollingBack?: boolean;
  /** Loads + returns the config for a given version (for the "view" modal). */
  onViewVersion: (version: number) => Promise<TenantConfig>;
  onRollback: (version: number) => void;
}

export default function VersionHistory({
  versions,
  loading = false,
  rollingBack = false,
  onViewVersion,
  onRollback,
}: Props) {
  const [viewing, setViewing] = useState<number | null>(null);
  const [viewConfig, setViewConfig] = useState<TenantConfig | null>(null);
  const [viewLoading, setViewLoading] = useState(false);
  const [viewError, setViewError] = useState<string | null>(null);

  const handleView = async (version: number) => {
    setViewing(version);
    setViewConfig(null);
    setViewError(null);
    setViewLoading(true);
    try {
      const cfg = await onViewVersion(version);
      setViewConfig(cfg);
    } catch (e) {
      setViewError(e instanceof Error ? e.message : String(e));
    } finally {
      setViewLoading(false);
    }
  };

  return (
    <>
      {loading ? (
        <Flex justify="center" style={{ padding: 32 }}>
          <Spin />
        </Flex>
      ) : versions.length === 0 ? (
        <Empty description="No versions yet." />
      ) : (
        <List
          dataSource={[...versions].sort((a, b) => b.version - a.version)}
          renderItem={(v) => (
            <List.Item
              actions={[
                <Button
                  key="view"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => handleView(v.version)}
                >
                  View
                </Button>,
                v.is_active ? (
                  <Tag key="active" color="success">
                    active
                  </Tag>
                ) : (
                  <Popconfirm
                    key="rollback"
                    title={`Roll back to version ${v.version}?`}
                    description="This creates a new active version copying this config."
                    onConfirm={() => onRollback(v.version)}
                    okText="Roll back"
                  >
                    <Button
                      size="small"
                      danger
                      icon={<RollbackOutlined />}
                      loading={rollingBack}
                    >
                      Roll back
                    </Button>
                  </Popconfirm>
                ),
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>Version {v.version}</Text>
                    {v.is_active && <Tag color="success">active</Tag>}
                  </Space>
                }
                description={
                  <Text type="secondary">
                    {new Date(v.created_at).toLocaleString()}
                  </Text>
                }
              />
            </List.Item>
          )}
        />
      )}

      <Modal
        open={viewing !== null}
        title={`Configuration — Version ${viewing ?? ""}`}
        onCancel={() => setViewing(null)}
        footer={[
          <Button key="close" onClick={() => setViewing(null)}>
            Close
          </Button>,
          viewing !== null &&
          !versions.find((v) => v.version === viewing)?.is_active ? (
            <Popconfirm
              key="rb"
              title={`Roll back to version ${viewing}?`}
              onConfirm={() => {
                if (viewing !== null) onRollback(viewing);
                setViewing(null);
              }}
              okText="Roll back"
            >
              <Button danger icon={<RollbackOutlined />}>
                Roll back to this version
              </Button>
            </Popconfirm>
          ) : null,
        ]}
        width={720}
      >
        {viewLoading ? (
          <Flex justify="center" style={{ padding: 32 }}>
            <Spin />
          </Flex>
        ) : viewError ? (
          <Alert type="warning" showIcon title="Cannot display version" description={viewError} />
        ) : viewConfig ? (
          <pre
            style={{
              maxHeight: 480,
              overflow: "auto",
              background: "#f5f5f5",
              padding: 12,
              borderRadius: 6,
              fontSize: 12,
            }}
          >
            {JSON.stringify(viewConfig, null, 2)}
          </pre>
        ) : (
          <Empty description="No config loaded." />
        )}
      </Modal>
    </>
  );
}
