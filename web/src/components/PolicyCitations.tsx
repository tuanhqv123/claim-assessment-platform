"use client";

import { List, Typography } from "antd";
import { BookOutlined } from "@ant-design/icons";
import type { PolicyCitation } from "@/types";

interface Props {
  items: PolicyCitation[];
}

export default function PolicyCitations({ items }: Props) {
  return (
    <List
      size="small"
      dataSource={items}
      renderItem={(item) => (
        <List.Item>
          <List.Item.Meta
            avatar={<BookOutlined style={{ color: "#1677ff" }} />}
            title={<Typography.Text strong>{item.clause}</Typography.Text>}
            description={item.relevance}
          />
        </List.Item>
      )}
    />
  );
}
