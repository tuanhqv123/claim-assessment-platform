"""Upsert the data/policies/*.json files into the `policies` table.

All policies belong to the SafeGuard tenant. ``policy_number`` is the file's
``policy_id`` and ``data`` is the full policy JSON. Idempotent via upsert on
(tenant_id, policy_number).

Run: .venv/bin/python -m scripts.sync_policies
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as a standalone script (python scripts/sync_policies.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from src import db  # noqa: E402

SAFEGUARD_TENANT_ID = "a0000000-0000-0000-0000-000000000001"
POLICIES_DIR = Path(__file__).resolve().parents[1] / "data" / "policies"


def sync() -> None:
    files = sorted(POLICIES_DIR.glob("*.json"))
    if not files:
        print(f"No policy files found in {POLICIES_DIR}")
        return

    rows = []
    for path in files:
        policy = json.loads(path.read_text())
        policy_number = policy["policy_id"]
        rows.append(
            {
                "tenant_id": SAFEGUARD_TENANT_ID,
                "policy_number": policy_number,
                "data": policy,
            }
        )
        print(f"  prepared {path.name} -> policy_number={policy_number}")

    result = db.upsert("policies", rows, on_conflict="tenant_id,policy_number")
    print(f"Upserted {len(result)} policies under SafeGuard tenant.")
    for r in result:
        print(f"    {r['policy_number']}  (id={r['id']})")


if __name__ == "__main__":
    sync()
