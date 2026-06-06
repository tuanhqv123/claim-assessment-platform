"use client";

import { useState } from "react";
import {
  Space,
  Typography,
  Tag,
  Button,
  Divider,
  Empty,
  Flex,
  Input,
  Tooltip,
  Modal,
  notification,
} from "antd";
import {
  ApartmentOutlined,
  HistoryOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import {
  postTransition,
  type AvailableTransition,
  type ClaimState,
  type Role,
  type TransitionAuditEntry,
  ApiError,
} from "@/lib/assessorApi";
import {
  stateLabel,
  stateColor,
  roleLabel,
  transitionActionLabel,
} from "./constants";
import AuditTrail from "./AuditTrail";
import { humanizeKey } from "@/lib/humanize";

interface Props {
  claimId: string;
  currentState: ClaimState;
  audit: TransitionAuditEntry[];
  available: AvailableTransition[];
  /** The acting role chosen in the page header; sent as the X-Role header. */
  role: Role;
  /** Called after a successful transition so the parent can refetch. */
  onTransitioned: () => void;
}

export default function WorkflowPanel({
  claimId,
  currentState,
  audit,
  available,
  role,
  onTransitioned,
}: Props) {
  const [pendingTo, setPendingTo] = useState<ClaimState | null>(null);
  const [reason, setReason] = useState("");
  const [submittingTo, setSubmittingTo] = useState<ClaimState | null>(null);
  const [api, contextHolder] = notification.useNotification();

  const activeTransition =
    available.find((t) => t.to === pendingTo) ?? null;

  async function doTransition(to: ClaimState, reasonText: string) {
    setSubmittingTo(to);
    try {
      const res = await postTransition(
        claimId,
        { to_state: to, reason: reasonText || undefined, context: {} },
        role,
      );
      api.success({
        title: "Transition applied",
        description: `Claim moved to ${stateLabel(res.state)} as ${roleLabel(
          role,
        )}.`,
      });
      setPendingTo(null);
      setReason("");
      onTransitioned();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Transition failed";
      // Surface the backend's specific message (e.g. unauthorized role).
      api.error({
        title: "Transition rejected",
        description: message,
        duration: 8,
      });
    } finally {
      setSubmittingTo(null);
    }
  }

  function onClickTransition(t: AvailableTransition) {
    // Open a modal to collect an optional reason before submitting.
    setPendingTo(t.to);
    setReason("");
  }

  return (
    <>
      {contextHolder}
      <div>
        <Flex align="center" gap={8} style={{ marginBottom: 16 }}>
          <span style={{ color: "#0d9488", fontSize: 15, display: "flex" }}>
            <ApartmentOutlined />
          </span>
          <Typography.Text strong style={{ fontSize: 14, whiteSpace: "nowrap" }}>
            Workflow
          </Typography.Text>
        </Flex>

        <Space direction="vertical" size={4} style={{ width: "100%" }}>
          <Typography.Text type="secondary">Current state</Typography.Text>
          <div>
            <Tag
              color={stateColor(currentState)}
              style={{ fontSize: 14, padding: "4px 12px" }}
            >
              {stateLabel(currentState)}
            </Tag>
          </div>
        </Space>

        <Divider style={{ margin: "16px 0" }} />

        <Typography.Text strong>Available transitions</Typography.Text>
        <div style={{ marginTop: 12 }}>
          {available.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="No transitions available from this state"
            />
          ) : (
            <Space direction="vertical" size={10} style={{ width: "100%" }}>
              {available.map((t) => {
                const allowed = t.role === role;
                return (
                  <div
                    key={t.to}
                    style={{
                      padding: "10px 12px",
                      border: "1px solid #edf0f2",
                      borderRadius: 8,
                      background: "#fff",
                    }}
                  >
                    <Flex align="center" gap={6} wrap="wrap" style={{ marginBottom: 6 }}>
                      <Tag color={stateColor(t.to)} style={{ marginInlineEnd: 0 }}>
                        → {stateLabel(t.to)}
                      </Tag>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        requires
                      </Typography.Text>
                      <Tag
                        color={allowed ? "green" : "default"}
                        style={{ marginInlineEnd: 0 }}
                      >
                        {roleLabel(String(t.role))}
                      </Tag>
                    </Flex>
                    {t.preconditions && t.preconditions.length > 0 && (
                      <Typography.Text
                        type="secondary"
                        style={{ fontSize: 11, display: "block", marginBottom: 8 }}
                      >
                        Preconditions: {t.preconditions.map(humanizeKey).join(", ")}
                      </Typography.Text>
                    )}
                    <Tooltip
                      title={
                        allowed
                          ? undefined
                          : `Your current role (${roleLabel(role)}) is not ${roleLabel(
                              String(t.role),
                            )}. Submit anyway to see the backend rejection.`
                      }
                    >
                      <Button
                        block
                        type={allowed ? "primary" : "default"}
                        danger={t.to === "REJECTED"}
                        loading={submittingTo === t.to}
                        onClick={() => onClickTransition(t)}
                      >
                        {transitionActionLabel(t.to)}
                      </Button>
                    </Tooltip>
                  </div>
                );
              })}
            </Space>
          )}
        </div>

        <Divider style={{ margin: "16px 0" }} />

        <Space>
          <HistoryOutlined />
          <Typography.Text strong>Audit trail</Typography.Text>
        </Space>
        <div style={{ marginTop: 12 }}>
          <AuditTrail entries={audit} />
        </div>
      </div>

      <Modal
        open={pendingTo !== null}
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: "#faad14" }} />
            {pendingTo ? transitionActionLabel(pendingTo) : "Transition"}
          </Space>
        }
        okText="Confirm transition"
        confirmLoading={submittingTo !== null}
        onOk={() => pendingTo && doTransition(pendingTo, reason)}
        onCancel={() => {
          setPendingTo(null);
          setReason("");
        }}
      >
        {activeTransition && (
          <Space direction="vertical" size={8} style={{ width: "100%" }}>
            <Typography.Text>
              Move{" "}
              <Tag color={stateColor(currentState)}>
                {stateLabel(currentState)}
              </Tag>{" "}
              →{" "}
              <Tag color={stateColor(activeTransition.to)}>
                {stateLabel(activeTransition.to)}
              </Tag>
            </Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              Sending as <Tag>{roleLabel(role)}</Tag> (X-Role: {role}). Required
              role: <Tag>{roleLabel(String(activeTransition.role))}</Tag>
            </Typography.Text>
            <Input.TextArea
              rows={3}
              placeholder="Reason / notes (optional)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </Space>
        )}
      </Modal>
    </>
  );
}
