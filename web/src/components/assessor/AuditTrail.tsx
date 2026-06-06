"use client";

import { Timeline, Typography, Tag, Empty, Space } from "antd";
import {
  ArrowRightOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import type { TransitionAuditEntry } from "@/lib/assessorApi";
import { stateLabel, stateColor, roleLabel } from "./constants";
import { humanizeKey, humanizeValue } from "@/lib/humanize";

interface Props {
  entries: TransitionAuditEntry[];
}

function fmtDate(s: string): string {
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString();
}

function hasSideEffects(
  se: TransitionAuditEntry["side_effects"],
): boolean {
  if (!se) return false;
  if (Array.isArray(se)) return se.length > 0;
  return Object.keys(se).length > 0;
}

function SideEffects({ se }: { se: TransitionAuditEntry["side_effects"] }) {
  if (!hasSideEffects(se)) return null;

  let items: string[];
  if (Array.isArray(se)) {
    items = se.map((v) => (typeof v === "string" ? humanizeKey(v) : humanizeValue(v)));
  } else {
    items = Object.entries(se as Record<string, unknown>).map(
      ([k, v]) => `${humanizeKey(k)}: ${humanizeValue(v)}`,
    );
  }

  return (
    <div style={{ marginTop: 4 }}>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        Side-effects:
      </Typography.Text>{" "}
      <Space size={[4, 4]} wrap>
        {items.map((it, i) => (
          <Tag key={i} color="geekblue" style={{ fontSize: 11 }}>
            {it}
          </Tag>
        ))}
      </Space>
    </div>
  );
}

export default function AuditTrail({ entries }: Props) {
  if (!entries || entries.length === 0) {
    return <Empty description="No transitions yet" />;
  }

  // Newest first.
  const ordered = [...entries].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  const items = ordered.map((e) => ({
    key: String(e.id),
    color: stateColor(e.to_state),
    dot: <ClockCircleOutlined style={{ fontSize: 13 }} />,
    children: (
      <div style={{ paddingBottom: 6 }}>
        <Space size={6} align="center" wrap>
          {e.from_state ? (
            <>
              <Tag color={stateColor(e.from_state)}>
                {stateLabel(e.from_state)}
              </Tag>
              <ArrowRightOutlined style={{ color: "#999" }} />
            </>
          ) : (
            <Tag>(initial)</Tag>
          )}
          <Tag color={stateColor(e.to_state)}>{stateLabel(e.to_state)}</Tag>
        </Space>

        <div style={{ marginTop: 4 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {roleLabel(e.triggered_by_role)}
            {e.triggered_by ? ` · ${e.triggered_by}` : ""} · {fmtDate(e.created_at)}
          </Typography.Text>
        </div>

        {e.reason && (
          <div style={{ marginTop: 2 }}>
            <Typography.Text style={{ fontSize: 12 }}>
              Reason: {e.reason}
            </Typography.Text>
          </div>
        )}
        {e.notes && (
          <div style={{ marginTop: 2 }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {e.notes}
            </Typography.Text>
          </div>
        )}

        <SideEffects se={e.side_effects} />
      </div>
    ),
  }));

  return <Timeline items={items} />;
}
