"use client";

import { Collapse } from "antd";
import {
  FileTextOutlined,
  SafetyCertificateOutlined,
  MedicineBoxOutlined,
  CalculatorOutlined,
  AuditOutlined,
  BookOutlined,
} from "@ant-design/icons";
import { REPORT_SECTION, REPORT_SECTION_LABEL } from "@/constants";
import type { AssessmentReport as AssessmentReportType } from "@/types";
import DocumentReview from "./DocumentReview";
import PolicyVerification from "./PolicyVerification";
import MedicalNecessity from "./MedicalNecessity";
import BenefitCalculation from "./BenefitCalculation";
import PolicyCitations from "./PolicyCitations";
import { Alert, Typography } from "antd";

const SECTION_ICONS: Record<string, React.ReactNode> = {
  [REPORT_SECTION.DOCUMENT_REVIEW]: <FileTextOutlined />,
  [REPORT_SECTION.POLICY_VERIFICATION]: <SafetyCertificateOutlined />,
  [REPORT_SECTION.MEDICAL_NECESSITY]: <MedicineBoxOutlined />,
  [REPORT_SECTION.BENEFIT_CALCULATION]: <CalculatorOutlined />,
  [REPORT_SECTION.RECOMMENDATION]: <AuditOutlined />,
  [REPORT_SECTION.POLICY_CITATIONS]: <BookOutlined />,
};

interface Props {
  report: AssessmentReportType;
}

export default function AssessmentReport({ report }: Props) {
  const items = [
    {
      key: REPORT_SECTION.DOCUMENT_REVIEW,
      label: (
        <span>
          {SECTION_ICONS[REPORT_SECTION.DOCUMENT_REVIEW]}{" "}
          {REPORT_SECTION_LABEL[REPORT_SECTION.DOCUMENT_REVIEW]}
        </span>
      ),
      children: <DocumentReview items={report.document_review} />,
    },
    {
      key: REPORT_SECTION.POLICY_VERIFICATION,
      label: (
        <span>
          {SECTION_ICONS[REPORT_SECTION.POLICY_VERIFICATION]}{" "}
          {REPORT_SECTION_LABEL[REPORT_SECTION.POLICY_VERIFICATION]}
        </span>
      ),
      children: <PolicyVerification data={report.policy_verification} />,
    },
    {
      key: REPORT_SECTION.MEDICAL_NECESSITY,
      label: (
        <span>
          {SECTION_ICONS[REPORT_SECTION.MEDICAL_NECESSITY]}{" "}
          {REPORT_SECTION_LABEL[REPORT_SECTION.MEDICAL_NECESSITY]}
        </span>
      ),
      children: <MedicalNecessity data={report.medical_necessity} />,
    },
    {
      key: REPORT_SECTION.BENEFIT_CALCULATION,
      label: (
        <span>
          {SECTION_ICONS[REPORT_SECTION.BENEFIT_CALCULATION]}{" "}
          {REPORT_SECTION_LABEL[REPORT_SECTION.BENEFIT_CALCULATION]}
        </span>
      ),
      children: <BenefitCalculation data={report.benefit_calculation} />,
    },
    {
      key: REPORT_SECTION.RECOMMENDATION,
      label: (
        <span>
          {SECTION_ICONS[REPORT_SECTION.RECOMMENDATION]}{" "}
          {REPORT_SECTION_LABEL[REPORT_SECTION.RECOMMENDATION]}
        </span>
      ),
      children: (
        <div>
          <Alert
            type={
              report.recommendation.decision === "APPROVE"
                ? "success"
                : report.recommendation.decision === "REJECT"
                ? "error"
                : "warning"
            }
            title={report.recommendation.reasoning}
            showIcon
            style={{ marginBottom: 12 }}
          />
          <Typography.Paragraph type="secondary">
            <strong>Next Steps:</strong> {report.recommendation.next_steps}
          </Typography.Paragraph>
        </div>
      ),
    },
    {
      key: REPORT_SECTION.POLICY_CITATIONS,
      label: (
        <span>
          {SECTION_ICONS[REPORT_SECTION.POLICY_CITATIONS]}{" "}
          {REPORT_SECTION_LABEL[REPORT_SECTION.POLICY_CITATIONS]}
        </span>
      ),
      children: <PolicyCitations items={report.policy_citations} />,
    },
  ];

  return (
    <Collapse
      items={items}
      defaultActiveKey={[
        REPORT_SECTION.RECOMMENDATION,
        REPORT_SECTION.BENEFIT_CALCULATION,
        REPORT_SECTION.DOCUMENT_REVIEW,
      ]}
    />
  );
}
