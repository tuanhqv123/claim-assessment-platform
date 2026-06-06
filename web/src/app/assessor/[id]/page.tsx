"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Flex, Button } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { PageBody } from "@/components/ui/PageHeader";
import { ClaimDetail, RoleSwitcher } from "@/components/assessor";
import type { Role } from "@/lib/assessorApi";

const ROLE_KEY = "assessor.role";
const DEFAULT_ROLE: Role = "assessor";

export default function AssessorClaimDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [role, setRole] = useState<Role>(DEFAULT_ROLE);

  // Persist the acting role across navigations.
  useEffect(() => {
    const stored = window.localStorage.getItem(ROLE_KEY) as Role | null;
    if (stored) setRole(stored);
  }, []);

  const handleRoleChange = (next: Role) => {
    setRole(next);
    window.localStorage.setItem(ROLE_KEY, next);
  };

  return (
    <PageBody>
      <Flex align="center" justify="space-between" gap={12} style={{ marginBottom: 20 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => router.push("/assessor")}
        >
          Back to Queue
        </Button>
        <RoleSwitcher value={role} onChange={handleRoleChange} />
      </Flex>

      <ClaimDetail claimId={id} role={role} />
    </PageBody>
  );
}
