"""Demo driver for the Claims Workflow Orchestrator.

Runs five named scenarios, printing each one's final state and full audit
trail. Uses a fixed clock so output is deterministic.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as `python src/workflow/demo.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.workflow.engine import (  # noqa: E402
    WorkflowEngine,
    WorkflowError,
)

FIXED_NOW = datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)


def _engine() -> WorkflowEngine:
    return WorkflowEngine(clock=lambda: FIXED_NOW)


def _print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _print_audit(engine: WorkflowEngine, claim) -> None:
    print(f"Final state: {claim.state}")
    print(f"Info-request loops: {claim.info_request_count}")
    print("Audit trail:")
    trail = engine.audit_trail(claim.id)
    if not trail:
        print("  (empty)")
    for i, entry in enumerate(trail, 1):
        by = entry["triggered_by"]
        print(
            f"  {i}. {entry['from_state']} -> {entry['to_state']} "
            f"by {by['id']} ({by['role']}) at {entry['timestamp']}"
        )
        if entry.get("reason"):
            print(f"       reason: {entry['reason']}")
        if entry.get("notes"):
            print(f"       notes: {entry['notes']}")
        for se in entry["side_effects"]:
            print(f"       {se}")


def scenario_1_happy_path() -> None:
    _print_header("Scenario 1 — Happy path (SUBMITTED -> ... -> CLOSED)")
    eng = _engine()
    claim = eng.new_claim("CLM-001")
    eng.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                   {"all_required_documents_present": True},
                   actor_id="clerk-1", reason="All docs present", now=FIXED_NOW)
    eng.transition(claim, "UNDER_ASSESSMENT", "team_lead",
                   {"assessor_assigned": True},
                   actor_id="lead-1", now=FIXED_NOW)
    eng.transition(claim, "APPROVED", "assessor",
                   {"assessment_complete": True, "amount_within_limit": True},
                   actor_id="assessor-1", reason="Within limit", now=FIXED_NOW)
    eng.transition(claim, "PAYMENT_INITIATED", "finance",
                   {"payment_request_created": True},
                   actor_id="fin-1", now=FIXED_NOW)
    eng.transition(claim, "CLOSED", "finance",
                   {"payment_confirmed": True},
                   actor_id="fin-1", now=FIXED_NOW)
    _print_audit(eng, claim)


def scenario_2_rejection() -> None:
    _print_header("Scenario 2 — Rejection (SUBMITTED -> ... -> REJECTED -> CLOSED)")
    eng = _engine()
    claim = eng.new_claim("CLM-002")
    eng.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                   {"all_required_documents_present": True},
                   actor_id="clerk-1", now=FIXED_NOW)
    eng.transition(claim, "UNDER_ASSESSMENT", "team_lead",
                   {"assessor_assigned": True},
                   actor_id="lead-1", now=FIXED_NOW)
    eng.transition(claim, "REJECTED", "assessor",
                   {"assessment_complete": True, "rejection_reason_provided": True},
                   actor_id="assessor-1", reason="Pre-existing condition",
                   now=FIXED_NOW)
    eng.transition(claim, "CLOSED", "system",
                   {"appeal_period_expired_or_acknowledged": True},
                   actor_id="system", now=FIXED_NOW)
    _print_audit(eng, claim)


def scenario_3_info_loop() -> None:
    _print_header("Scenario 3 — Info loop")
    eng = _engine()
    claim = eng.new_claim("CLM-003")
    eng.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                   {"all_required_documents_present": True},
                   actor_id="clerk-1", now=FIXED_NOW)
    eng.transition(claim, "UNDER_ASSESSMENT", "team_lead",
                   {"assessor_assigned": True},
                   actor_id="lead-1", now=FIXED_NOW)
    eng.transition(claim, "PENDING_INFO", "assessor",
                   {"missing_info_description_provided": True},
                   actor_id="assessor-1", reason="Need itemized invoice",
                   now=FIXED_NOW)
    eng.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                   {"new_info_received": True},
                   actor_id="clerk-1", now=FIXED_NOW)
    eng.transition(claim, "UNDER_ASSESSMENT", "team_lead",
                   {"assessor_assigned": True},
                   actor_id="lead-1", now=FIXED_NOW)
    eng.transition(claim, "APPROVED", "assessor",
                   {"assessment_complete": True, "amount_within_limit": True},
                   actor_id="assessor-1", now=FIXED_NOW)
    eng.transition(claim, "PAYMENT_INITIATED", "finance",
                   {"payment_request_created": True},
                   actor_id="fin-1", now=FIXED_NOW)
    eng.transition(claim, "CLOSED", "finance",
                   {"payment_confirmed": True},
                   actor_id="fin-1", now=FIXED_NOW)
    _print_audit(eng, claim)


def scenario_4_invalid_transition() -> None:
    _print_header("Scenario 4 — Invalid transition (SUBMITTED -> APPROVED)")
    eng = _engine()
    claim = eng.new_claim("CLM-004")
    try:
        eng.transition(claim, "APPROVED", "assessor",
                       {"assessment_complete": True, "amount_within_limit": True},
                       actor_id="assessor-1", now=FIXED_NOW)
    except WorkflowError as exc:
        print(f"Rejected as expected: {exc}")
    _print_audit(eng, claim)


def scenario_5_unauthorized_role() -> None:
    _print_header("Scenario 5 — Unauthorized role")
    eng = _engine()
    claim = eng.new_claim("CLM-005")
    # Wrong role: an assessor tries to do the document_clerk's job.
    try:
        eng.transition(claim, "DOCUMENTS_VERIFIED", "assessor",
                       {"all_required_documents_present": True},
                       actor_id="assessor-1", now=FIXED_NOW)
    except WorkflowError as exc:
        print(f"Rejected as expected: {exc}")
    _print_audit(eng, claim)


def main() -> None:
    scenario_1_happy_path()
    scenario_2_rejection()
    scenario_3_info_loop()
    scenario_4_invalid_transition()
    scenario_5_unauthorized_role()


if __name__ == "__main__":
    main()
