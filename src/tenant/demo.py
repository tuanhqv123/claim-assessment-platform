"""Demo: the SAME claim produces DIFFERENT outcomes per tenant.

Run: .venv/bin/python src/tenant/demo.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.tenant.diff import diff_configs  # noqa: E402
from src.tenant.fixtures import GOVHEALTH, SAFEGUARD, TENANTS  # noqa: E402
from src.tenant.runtime import process_claim  # noqa: E402


def _fmt(outcome: dict) -> str:
    out = dict(outcome)
    out["sla_deadline"] = out["sla_deadline"].isoformat()
    return json.dumps(out, indent=2)


def main() -> None:
    claim = {
        "claim_type": "OUTPATIENT",
        "amount": 8000,
        "custom_fields": {"employee_id": "E-1"},
    }
    submission_date = date(2026, 6, 3)  # a Wednesday

    print("=" * 70)
    print("SAME CLAIM submitted to 3 tenants:")
    print(json.dumps(claim, indent=2))
    print(f"submission_date = {submission_date.isoformat()} ({submission_date.strftime('%A')})")
    print("=" * 70)

    for name, config in TENANTS.items():
        print(f"\n----- {name} -----")
        try:
            outcome = process_claim(config, claim, submission_date)
            print(_fmt(outcome))
        except ValueError as exc:
            print(f"ERROR: {exc}")

    print("\n" + "=" * 70)
    print("diff_configs(SafeGuard, GovHealth):")
    print("=" * 70)
    for d in diff_configs(SAFEGUARD, GOVHEALTH):
        print(f"  {d['path']}: {d['a_value']!r}  ->  {d['b_value']!r}")


if __name__ == "__main__":
    main()
