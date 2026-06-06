from __future__ import annotations

import json
from pathlib import Path


REQUIRED_DOCUMENTS: dict[str, list[str]] = {
    "OUTPATIENT": ["medical_receipt"],
    "INPATIENT": ["medical_receipt", "discharge_summary", "itemized_bill"],
    "DENTAL": ["dental_receipt"],
    "MATERNITY": ["medical_receipt", "discharge_summary"],
}

OPTIONAL_DOCUMENTS: dict[str, list[str]] = {
    "OUTPATIENT": ["prescription", "referral_letter"],
    "INPATIENT": ["prescription"],
    "DENTAL": ["treatment_plan"],
    "MATERNITY": ["prenatal_records"],
}


class PolicyStore:
    def __init__(
        self,
        data_dir: str = "data/policies",
        policies: dict[str, dict] | None = None,
    ):
        """Policy lookup store.

        ``policies`` (policy_id -> policy dict) injects an in-memory set, e.g.
        built from the database, so the agent assesses against live policy data
        instead of the file-backed demo policies. When omitted, policies are
        loaded from ``data_dir`` JSON files.
        """
        if policies is not None:
            self._policies = dict(policies)
            return
        self._policies = {}
        data_path = Path(data_dir)
        if data_path.exists():
            for f in data_path.glob("*.json"):
                policy = json.loads(f.read_text())
                self._policies[policy["policy_id"]] = policy

    def lookup(self, policy_id: str) -> dict | None:
        return self._policies.get(policy_id)

    @staticmethod
    def get_required_documents(claim_type: str) -> list[str]:
        return REQUIRED_DOCUMENTS.get(claim_type, ["medical_receipt"])

    @staticmethod
    def get_optional_documents(claim_type: str) -> list[str]:
        return OPTIONAL_DOCUMENTS.get(claim_type, [])
