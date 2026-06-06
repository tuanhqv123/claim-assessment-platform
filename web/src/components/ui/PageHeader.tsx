"use client";

import { Flex, Typography } from "antd";

const { Title, Text } = Typography;

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  extra?: React.ReactNode;
}

/** Consistent slim page header. Replaces per-page Layout.Header duplication. */
export function PageHeader({ title, subtitle, icon, extra }: PageHeaderProps) {
  return (
    <Flex
      align="center"
      justify="space-between"
      wrap="wrap"
      gap={12}
      style={{
        padding: "16px 28px",
        background: "#fff",
        borderBottom: "1px solid #edf0f2",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <Flex align="center" gap={14}>
        {icon && (
          <Flex
            align="center"
            justify="center"
            style={{
              width: 38,
              height: 38,
              borderRadius: 10,
              background: "#e6f4f2",
              color: "#0d9488",
              fontSize: 19,
            }}
          >
            {icon}
          </Flex>
        )}
        <div>
          <Title level={4} style={{ margin: 0, lineHeight: 1.25 }}>
            {title}
          </Title>
          {subtitle && (
            <Text type="secondary" style={{ fontSize: 13 }}>
              {subtitle}
            </Text>
          )}
        </div>
      </Flex>
      {extra && <div>{extra}</div>}
    </Flex>
  );
}

/** Padded, max-width content region for page bodies. */
export function PageBody({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ padding: "24px 28px 48px", maxWidth: 1360, width: "100%", margin: "0 auto" }}>
      {children}
    </div>
  );
}

export default PageHeader;
