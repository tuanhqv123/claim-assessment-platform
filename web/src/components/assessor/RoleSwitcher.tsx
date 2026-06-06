"use client";

import { Select, Space, Typography, Tag } from "antd";
import { UserSwitchOutlined } from "@ant-design/icons";
import { ROLES, type Role } from "@/lib/assessorApi";
import { ROLE_LABEL } from "./constants";

interface Props {
  value: Role;
  onChange: (role: Role) => void;
  size?: "small" | "middle" | "large";
}

/**
 * Picks the role sent as the `X-Role` header on workflow transitions.
 * Switching to an unauthorized role lets you demonstrate the backend's
 * role enforcement (Challenge 14).
 */
export default function RoleSwitcher({ value, onChange, size = "middle" }: Props) {
  return (
    <Space size={8} align="center">
      <UserSwitchOutlined style={{ color: "#1677ff" }} />
      <Typography.Text type="secondary">Acting as</Typography.Text>
      <Select<Role>
        value={value}
        onChange={onChange}
        size={size}
        style={{ minWidth: 180 }}
        options={ROLES.map((r) => ({
          value: r,
          label: ROLE_LABEL[r] ?? r,
        }))}
      />
      <Tag color="blue" style={{ fontFamily: "monospace" }}>
        X-Role: {value}
      </Tag>
    </Space>
  );
}
