"use client";

import { useState } from "react";
import { App, ConfigProvider, Layout, Menu, theme as antdTheme } from "antd";
import {
  MedicineBoxOutlined,
  DashboardOutlined,
  FileAddOutlined,
  AuditOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { usePathname, useRouter } from "next/navigation";

const { Sider } = Layout;

const SIDER_WIDTH = 216;
const SIDER_COLLAPSED_WIDTH = 72;

const THEME = {
  token: {
    colorPrimary: "#0d9488",
    colorInfo: "#0d9488",
    colorLink: "#0d9488",
    borderRadius: 8,
    fontFamily:
      'var(--font-sans), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    colorBgLayout: "#ffffff",
    controlHeight: 36,
  },
  components: {
    Layout: { siderBg: "#0c1b2a", triggerBg: "#081320" },
    Menu: { darkItemBg: "transparent", darkSubMenuItemBg: "transparent" },
    Card: { boxShadowTertiary: "0 1px 2px rgba(16,24,40,0.04)" },
  },
};

const ITEMS = [
  { key: "/", icon: <DashboardOutlined />, label: "Dashboard" },
  { key: "/member", icon: <FileAddOutlined />, label: "Submit Claim" },
  { key: "/assessor", icon: <AuditOutlined />, label: "Assessor" },
  { key: "/admin", icon: <SettingOutlined />, label: "Admin" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);

  const selectedKey =
    [...ITEMS]
      .reverse()
      .find((i) => (i.key === "/" ? pathname === "/" : pathname.startsWith(i.key)))?.key ?? "/";

  return (
    <ConfigProvider theme={{ ...THEME, algorithm: antdTheme.defaultAlgorithm }}>
      <App>
        <Layout style={{ minHeight: "100vh" }} hasSider>
          <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={setCollapsed}
            width={SIDER_WIDTH}
            collapsedWidth={SIDER_COLLAPSED_WIDTH}
            breakpoint="lg"
            theme="dark"
            style={{
              overflow: "auto",
              height: "100vh",
              position: "fixed",
              insetInlineStart: 0,
              top: 0,
              bottom: 0,
            }}
          >
            <div
              style={{
                height: 56,
                paddingInline: collapsed ? 0 : 20,
                display: "flex",
                alignItems: "center",
                justifyContent: collapsed ? "center" : "flex-start",
                color: "#fff",
                fontWeight: 700,
                fontSize: 15,
                letterSpacing: 0.2,
                gap: 10,
                whiteSpace: "nowrap",
                overflow: "hidden",
              }}
            >
              <MedicineBoxOutlined style={{ fontSize: 22, color: "#2dd4bf" }} />
              {!collapsed && "Papaya Claims"}
            </div>
            <Menu
              theme="dark"
              mode="inline"
              selectedKeys={[selectedKey]}
              items={ITEMS}
              onClick={({ key }) => router.push(key)}
              style={{ borderInlineEnd: 0 }}
            />
          </Sider>
          <Layout
            style={{
              marginInlineStart: collapsed ? SIDER_COLLAPSED_WIDTH : SIDER_WIDTH,
              transition: "margin-inline-start 0.2s",
            }}
          >
            {children}
          </Layout>
        </Layout>
      </App>
    </ConfigProvider>
  );
}
