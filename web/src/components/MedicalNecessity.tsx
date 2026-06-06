"use client";

import { Alert, Typography } from "antd";
import type { MedicalNecessity as MedicalNecessityType } from "@/types";

interface Props {
  data: MedicalNecessityType;
}

export default function MedicalNecessity({ data }: Props) {
  const isAvailable = data.is_appropriate !== null;

  if (!isAvailable) {
    return (
      <Alert
        type="info"
        title="Not yet assessed"
        description="Medical necessity check was not performed — pending document completion."
        showIcon
      />
    );
  }

  return (
    <div>
      <Alert
        type={data.is_appropriate ? "success" : "error"}
        title={data.is_appropriate ? "Clinically Appropriate" : "Not Clinically Appropriate"}
        description={data.reasoning}
        showIcon
        style={{ marginBottom: data.warnings.length > 0 ? 12 : 0 }}
      />
      {data.warnings.map((w, i) => (
        <Alert key={i} type="warning" title={w} showIcon style={{ marginTop: 8 }} />
      ))}
    </div>
  );
}
