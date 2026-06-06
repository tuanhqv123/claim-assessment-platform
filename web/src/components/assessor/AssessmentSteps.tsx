"use client";

import { Flex, Typography, Tag } from "antd";
import {
  CheckCircleFilled,
  LoadingOutlined,
  SafetyCertificateOutlined,
  FileTextOutlined,
  MedicineBoxOutlined,
  CalculatorOutlined,
} from "@ant-design/icons";
import type { AssessStepEvent } from "@/lib/assessorApi";

const { Text } = Typography;

const TOOL_CONFIG: Record<
  string,
  { label: string; icon: React.ReactNode; color: string }
> = {
  lookupPolicy: {
    label: "Policy Lookup",
    icon: <SafetyCertificateOutlined style={{ color: "#0d9488", fontSize: 13 }} />,
    color: "#0d9488",
  },
  verifyDocument: {
    label: "Document Verification",
    icon: <FileTextOutlined style={{ color: "#0d9488", fontSize: 13 }} />,
    color: "#0d9488",
  },
  checkMedicalNecessity: {
    label: "Medical Necessity",
    icon: <MedicineBoxOutlined style={{ color: "#0d9488", fontSize: 13 }} />,
    color: "#0d9488",
  },
  calculateBenefit: {
    label: "Benefit Calculation",
    icon: <CalculatorOutlined style={{ color: "#0d9488", fontSize: 13 }} />,
    color: "#0d9488",
  },
};

function asStr(v: unknown): string | null {
  return v === null || v === undefined ? null : String(v);
}

/** A short result tag summarising the tool's output for the live feed. */
function stepSummary(step: AssessStepEvent): string {
  const out = (step.data?.outputs as Record<string, unknown>) ?? step.data ?? {};
  switch (step.tool) {
    case "lookupPolicy": {
      const status = asStr(out.status);
      const id = asStr(out.policy_id);
      return [id, status].filter(Boolean).join(" · ") || "looked up";
    }
    case "verifyDocument": {
      const type = asStr(out.document_type);
      const status = asStr(out.status);
      return [type, status].filter(Boolean).join(" · ") || "verified";
    }
    case "checkMedicalNecessity": {
      const ok = out.is_medically_necessary ?? out.is_appropriate;
      if (ok === true) return "appropriate";
      if (ok === false) return "not appropriate";
      return "checked";
    }
    case "calculateBenefit": {
      const decision = asStr(out.decision);
      if (decision && decision.toUpperCase() !== "COVERED") {
        return asStr(out.reason) ?? decision;
      }
      const covered = out.covered_amount;
      if (covered !== null && covered !== undefined) {
        return `covered ${Number(covered).toLocaleString()} THB`;
      }
      return decision ?? "calculated";
    }
    default:
      return "done";
  }
}

interface Props {
  /** Completed steps, in arrival order. */
  steps: AssessStepEvent[];
  /** Whether the agent is still running (shows a spinner for the next step). */
  active: boolean;
}

export default function AssessmentSteps({ steps, active }: Props) {
  return (
    <Flex vertical gap={8} style={{ paddingInlineStart: 4 }}>
      {steps.map((step, i) => {
        const config = TOOL_CONFIG[step.tool] ?? {
          label: step.tool,
          icon: null,
          color: "#8c8c8c",
        };
        return (
          <Flex key={`${step.tool}-${i}`} align="center" gap={8}>
            <CheckCircleFilled style={{ color: "#52c41a", fontSize: 13 }} />
            <Text style={{ fontSize: 13 }}>{config.label}</Text>
            <Tag style={{ marginInlineStart: "auto", marginInlineEnd: 0 }}>
              {stepSummary(step)}
            </Tag>
          </Flex>
        );
      })}
      {active && (
        <Flex align="center" gap={8}>
          <LoadingOutlined spin style={{ color: "#0d9488", fontSize: 13 }} />
          <Text type="secondary" style={{ fontSize: 13 }}>
            {steps.length === 0 ? "Starting assessment…" : "Running…"}
          </Text>
        </Flex>
      )}
    </Flex>
  );
}
