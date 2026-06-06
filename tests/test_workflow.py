"""Tests for the config-driven Claims Workflow Orchestrator (Challenge 14)."""

from __future__ import annotations

import copy
from datetime import datetime, timezone

import pytest

from src.workflow.engine import (
    Claim,
    WorkflowEngine,
    InvalidTransitionError,
    PreconditionError,
    AuthorizationError,
    CycleLimitError,
)

FIXED_NOW = datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #
@pytest.fixture
def engine() -> WorkflowEngine:
    return WorkflowEngine(clock=lambda: FIXED_NOW)


def _to_documents_verified(engine: WorkflowEngine, claim: Claim) -> None:
    engine.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                      {"all_required_documents_present": True},
                      actor_id="clerk-1", now=FIXED_NOW)


def _to_under_assessment(engine: WorkflowEngine, claim: Claim) -> None:
    engine.transition(claim, "UNDER_ASSESSMENT", "team_lead",
                      {"assessor_assigned": True},
                      actor_id="lead-1", now=FIXED_NOW)


def _one_info_loop(engine: WorkflowEngine, claim: Claim) -> None:
    engine.transition(claim, "PENDING_INFO", "assessor",
                      {"missing_info_description_provided": True},
                      actor_id="assessor-1", now=FIXED_NOW)
    engine.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                      {"new_info_received": True},
                      actor_id="clerk-1", now=FIXED_NOW)
    _to_under_assessment(engine, claim)


# --------------------------------------------------------------------------- #
# 1. Valid transitions
# --------------------------------------------------------------------------- #
def test_valid_first_transition(engine):
    claim = engine.new_claim("C1")
    _to_documents_verified(engine, claim)
    assert claim.state == "DOCUMENTS_VERIFIED"


def test_valid_chain_to_under_assessment(engine):
    claim = engine.new_claim("C2")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    assert claim.state == "UNDER_ASSESSMENT"


def test_available_transitions_lists_targets(engine):
    targets = {t["to"] for t in engine.available_transitions("UNDER_ASSESSMENT")}
    assert targets == {"APPROVED", "REJECTED", "PENDING_INFO"}


def test_available_transitions_includes_role_and_preconditions(engine):
    trans = engine.available_transitions("SUBMITTED")
    assert trans == [
        {
            "to": "DOCUMENTS_VERIFIED",
            "role": "document_clerk",
            "preconditions": ["all_required_documents_present"],
        }
    ]


# --------------------------------------------------------------------------- #
# 2. Invalid transitions — specific errors
# --------------------------------------------------------------------------- #
def test_invalid_transition_specific_error(engine):
    claim = engine.new_claim("C3")
    with pytest.raises(InvalidTransitionError) as exc:
        engine.transition(claim, "APPROVED", "assessor",
                          {"assessment_complete": True, "amount_within_limit": True},
                          actor_id="a", now=FIXED_NOW)
    msg = str(exc.value)
    assert "cannot go from SUBMITTED to APPROVED" in msg
    assert "Valid targets: DOCUMENTS_VERIFIED" in msg


def test_invalid_transition_from_terminal_state(engine):
    claim = engine.new_claim("C4", state="CLOSED")
    with pytest.raises(InvalidTransitionError) as exc:
        engine.transition(claim, "APPROVED", "assessor", {}, now=FIXED_NOW)
    assert "terminal" in str(exc.value)


# --------------------------------------------------------------------------- #
# 3. Precondition failures
# --------------------------------------------------------------------------- #
def test_precondition_failure_names_key(engine):
    claim = engine.new_claim("C5")
    with pytest.raises(PreconditionError) as exc:
        engine.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                          {"all_required_documents_present": False}, now=FIXED_NOW)
    assert "all_required_documents_present" in str(exc.value)


def test_precondition_failure_when_missing_from_context(engine):
    claim = engine.new_claim("C6")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    with pytest.raises(PreconditionError) as exc:
        # amount_within_limit missing -> unmet.
        engine.transition(claim, "APPROVED", "assessor",
                          {"assessment_complete": True}, now=FIXED_NOW)
    assert "amount_within_limit" in str(exc.value)


# --------------------------------------------------------------------------- #
# 4. Role authorization
# --------------------------------------------------------------------------- #
def test_unauthorized_role_specific_error(engine):
    claim = engine.new_claim("C7")
    with pytest.raises(AuthorizationError) as exc:
        engine.transition(claim, "DOCUMENTS_VERIFIED", "assessor",
                          {"all_required_documents_present": True}, now=FIXED_NOW)
    msg = str(exc.value)
    assert "requires role 'document_clerk'" in msg
    assert "actor has role 'assessor'" in msg


def test_authorized_role_succeeds(engine):
    claim = engine.new_claim("C8")
    _to_documents_verified(engine, claim)
    assert claim.state == "DOCUMENTS_VERIFIED"


# --------------------------------------------------------------------------- #
# 5. Audit trail (immutable, append-only)
# --------------------------------------------------------------------------- #
def test_audit_trail_records_entries(engine):
    claim = engine.new_claim("C9")
    _to_documents_verified(engine, claim)
    trail = engine.audit_trail("C9")
    assert len(trail) == 1
    entry = trail[0]
    assert entry["from_state"] == "SUBMITTED"
    assert entry["to_state"] == "DOCUMENTS_VERIFIED"
    assert entry["triggered_by"] == {"id": "clerk-1", "role": "document_clerk"}
    assert entry["timestamp"] == FIXED_NOW.isoformat()
    assert any("notify_assessor_team" in s for s in entry["side_effects"])


def test_audit_trail_is_immutable_copy(engine):
    claim = engine.new_claim("C10")
    _to_documents_verified(engine, claim)
    trail = engine.audit_trail("C10")
    trail.append({"hacked": True})
    trail[0]["from_state"] = "TAMPERED"
    # Re-fetch: original is untouched.
    fresh = engine.audit_trail("C10")
    assert len(fresh) == 1
    assert fresh[0]["from_state"] == "SUBMITTED"


def test_failed_transition_not_audited(engine):
    claim = engine.new_claim("C11")
    with pytest.raises(AuthorizationError):
        engine.transition(claim, "DOCUMENTS_VERIFIED", "assessor",
                          {"all_required_documents_present": True}, now=FIXED_NOW)
    assert engine.audit_trail("C11") == []


# --------------------------------------------------------------------------- #
# 6. Cycle detection — allow 3, block the 4th
# --------------------------------------------------------------------------- #
def test_three_info_loops_allowed(engine):
    claim = engine.new_claim("C12")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    for _ in range(3):
        _one_info_loop(engine, claim)
    assert claim.state == "UNDER_ASSESSMENT"
    assert claim.info_request_count == 3


def test_fourth_info_loop_blocked(engine):
    claim = engine.new_claim("C13")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    for _ in range(3):
        _one_info_loop(engine, claim)
    # 4th loop: PENDING_INFO and back to DOCUMENTS_VERIFIED are fine,
    # but re-entering UNDER_ASSESSMENT must be blocked.
    engine.transition(claim, "PENDING_INFO", "assessor",
                      {"missing_info_description_provided": True}, now=FIXED_NOW)
    engine.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                      {"new_info_received": True}, now=FIXED_NOW)
    with pytest.raises(CycleLimitError) as exc:
        _to_under_assessment(engine, claim)
    assert str(exc.value) == (
        "Maximum information requests exceeded — escalate to team lead"
    )


def test_cycle_count_does_not_increment_on_normal_path(engine):
    """Entering UNDER_ASSESSMENT the first time (not via the loop) is free."""
    claim = engine.new_claim("C14")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    assert claim.info_request_count == 0


# --------------------------------------------------------------------------- #
# 7. The five named scenarios
# --------------------------------------------------------------------------- #
def test_scenario_1_happy_path(engine):
    claim = engine.new_claim("S1")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    engine.transition(claim, "APPROVED", "assessor",
                      {"assessment_complete": True, "amount_within_limit": True},
                      now=FIXED_NOW)
    engine.transition(claim, "PAYMENT_INITIATED", "finance",
                      {"payment_request_created": True}, now=FIXED_NOW)
    engine.transition(claim, "CLOSED", "finance",
                      {"payment_confirmed": True}, now=FIXED_NOW)
    assert claim.state == "CLOSED"
    assert len(engine.audit_trail("S1")) == 5


def test_scenario_2_rejection(engine):
    claim = engine.new_claim("S2")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    engine.transition(claim, "REJECTED", "assessor",
                      {"assessment_complete": True, "rejection_reason_provided": True},
                      now=FIXED_NOW)
    engine.transition(claim, "CLOSED", "system",
                      {"appeal_period_expired_or_acknowledged": True}, now=FIXED_NOW)
    assert claim.state == "CLOSED"
    states = [e["to_state"] for e in engine.audit_trail("S2")]
    assert states == ["DOCUMENTS_VERIFIED", "UNDER_ASSESSMENT", "REJECTED", "CLOSED"]


def test_scenario_3_info_loop(engine):
    claim = engine.new_claim("S3")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    _one_info_loop(engine, claim)
    engine.transition(claim, "APPROVED", "assessor",
                      {"assessment_complete": True, "amount_within_limit": True},
                      now=FIXED_NOW)
    engine.transition(claim, "PAYMENT_INITIATED", "finance",
                      {"payment_request_created": True}, now=FIXED_NOW)
    engine.transition(claim, "CLOSED", "finance",
                      {"payment_confirmed": True}, now=FIXED_NOW)
    assert claim.state == "CLOSED"
    assert claim.info_request_count == 1


def test_scenario_4_invalid_transition(engine):
    claim = engine.new_claim("S4")
    with pytest.raises(InvalidTransitionError):
        engine.transition(claim, "APPROVED", "assessor",
                          {"assessment_complete": True, "amount_within_limit": True},
                          now=FIXED_NOW)
    assert claim.state == "SUBMITTED"


def test_scenario_5_unauthorized_role(engine):
    claim = engine.new_claim("S5")
    _to_documents_verified(engine, claim)
    with pytest.raises(AuthorizationError):
        # team_lead's transition attempted by an assessor.
        engine.transition(claim, "UNDER_ASSESSMENT", "assessor",
                          {"assessor_assigned": True}, now=FIXED_NOW)
    assert claim.state == "DOCUMENTS_VERIFIED"


# --------------------------------------------------------------------------- #
# 8. Config-only extensibility
# --------------------------------------------------------------------------- #
def test_adding_new_state_and_transition_is_config_only():
    """A brand new state + transition works with zero engine code changes."""
    base = WorkflowEngine(clock=lambda: FIXED_NOW)
    config = copy.deepcopy(base._config)
    config["states"].append("ON_HOLD")
    config["transitions"].append(
        {
            "from": "SUBMITTED",
            "to": "ON_HOLD",
            "preconditions": ["fraud_flag_raised"],
            "side_effects": ["notify_fraud_team"],
            "role": "compliance",
        }
    )
    eng = WorkflowEngine(config=config, clock=lambda: FIXED_NOW)
    claim = eng.new_claim("NEW")
    eng.transition(claim, "ON_HOLD", "compliance",
                   {"fraud_flag_raised": True}, actor_id="c-1", now=FIXED_NOW)
    assert claim.state == "ON_HOLD"
    trail = eng.audit_trail("NEW")
    assert trail[0]["to_state"] == "ON_HOLD"
    assert any("notify_fraud_team" in s for s in trail[0]["side_effects"])


def test_new_config_transition_still_enforces_precondition():
    base = WorkflowEngine(clock=lambda: FIXED_NOW)
    config = copy.deepcopy(base._config)
    config["states"].append("ON_HOLD")
    config["transitions"].append(
        {
            "from": "SUBMITTED",
            "to": "ON_HOLD",
            "preconditions": ["fraud_flag_raised"],
            "side_effects": [],
            "role": "compliance",
        }
    )
    eng = WorkflowEngine(config=config, clock=lambda: FIXED_NOW)
    claim = eng.new_claim("NEW2")
    with pytest.raises(PreconditionError):
        eng.transition(claim, "ON_HOLD", "compliance", {}, now=FIXED_NOW)


# --------------------------------------------------------------------------- #
# 9. Check ordering — authorization BEFORE preconditions (no info leak)
# --------------------------------------------------------------------------- #
def test_unauthorized_with_unmet_precondition_raises_authorization_first(engine):
    """An unauthorized actor whose preconditions are ALSO unmet must get an
    AuthorizationError (not PreconditionError) — no precondition info leak."""
    claim = engine.new_claim("ORD1")
    with pytest.raises(AuthorizationError):
        # Wrong role AND the precondition is missing from context.
        engine.transition(claim, "DOCUMENTS_VERIFIED", "assessor", {},
                          actor_id="x", now=FIXED_NOW)
    # State unchanged and nothing audited.
    assert claim.state == "SUBMITTED"
    assert engine.audit_trail("ORD1") == []


def test_authorized_with_unmet_precondition_still_raises_precondition(engine):
    """With the correct role but an unmet precondition, the precondition error
    surfaces (auth passing does not swallow precondition checks)."""
    claim = engine.new_claim("ORD2")
    with pytest.raises(PreconditionError):
        engine.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk", {},
                          now=FIXED_NOW)


# --------------------------------------------------------------------------- #
# 10. Audit / state immutability — engine history cannot be rewritten
# --------------------------------------------------------------------------- #
def test_claim_state_is_read_only_handle(engine):
    """The Claim handle exposes state read-only; it cannot be set to bypass
    the state machine."""
    claim = engine.new_claim("IMM1")
    with pytest.raises(AttributeError):
        claim.state = "APPROVED"  # type: ignore[misc]
    assert claim.state == "SUBMITTED"


def test_returned_claim_cannot_mutate_engine_history(engine):
    """Mutating anything reachable from the returned claim/audit must not
    change the engine's canonical append-only history."""
    claim = engine.new_claim("IMM2")
    _to_documents_verified(engine, claim)
    returned = engine.transition(claim, "UNDER_ASSESSMENT", "team_lead",
                                 {"assessor_assigned": True}, now=FIXED_NOW)
    # Try to tamper via the returned audit copy.
    trail = engine.audit_trail(returned.id)
    trail.clear()
    trail.append({"forged": True})
    # Try to tamper via direct attribute assignment (should be impossible).
    with pytest.raises(AttributeError):
        returned.state = "REJECTED"  # type: ignore[misc]
    # Engine history is intact.
    fresh = engine.audit_trail("IMM2")
    assert len(fresh) == 2
    assert [e["to_state"] for e in fresh] == [
        "DOCUMENTS_VERIFIED", "UNDER_ASSESSMENT"
    ]
    assert claim.state == "UNDER_ASSESSMENT"


# --------------------------------------------------------------------------- #
# 11. Cycle exhaustion -> escalation path (claim is not wedged)
# --------------------------------------------------------------------------- #
def test_cycle_exhaustion_escalation_unwedges_claim(engine):
    """When the cycle limit is hit, the claim sits in DOCUMENTS_VERIFIED with a
    blocked re-entry edge, but the config-driven escalation edge lets it move
    to ESCALATED and then CLOSED — it is not a dead-end."""
    claim = engine.new_claim("ESC1")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    for _ in range(3):
        _one_info_loop(engine, claim)
    # 4th loop: PENDING_INFO and back to DOCUMENTS_VERIFIED are fine.
    engine.transition(claim, "PENDING_INFO", "assessor",
                      {"missing_info_description_provided": True}, now=FIXED_NOW)
    engine.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                      {"new_info_received": True}, now=FIXED_NOW)
    # Re-entering UNDER_ASSESSMENT is blocked with the exact message.
    with pytest.raises(CycleLimitError) as exc:
        _to_under_assessment(engine, claim)
    assert str(exc.value) == (
        "Maximum information requests exceeded — escalate to team lead"
    )
    # The claim is NOT wedged: escalate it out via the team_lead edge.
    audit_len_before = len(engine.audit_trail("ESC1"))
    engine.transition(claim, "ESCALATED", "team_lead", {},
                      actor_id="lead-1", now=FIXED_NOW)
    assert claim.state == "ESCALATED"
    # The blocked re-entry fired no side effects / no audit entry; the
    # escalation added exactly one entry with its side effect.
    trail = engine.audit_trail("ESC1")
    assert len(trail) == audit_len_before + 1
    assert trail[-1]["to_state"] == "ESCALATED"
    assert any("escalate_to_team_lead" in s for s in trail[-1]["side_effects"])
    # And it can be closed out.
    engine.transition(claim, "CLOSED", "team_lead",
                      {"escalation_resolved": True}, now=FIXED_NOW)
    assert claim.state == "CLOSED"


def test_blocked_cycle_reentry_writes_no_audit_and_no_side_effects(engine):
    """The blocked 4th UNDER_ASSESSMENT re-entry must leave history untouched."""
    claim = engine.new_claim("ESC2")
    _to_documents_verified(engine, claim)
    _to_under_assessment(engine, claim)
    for _ in range(3):
        _one_info_loop(engine, claim)
    engine.transition(claim, "PENDING_INFO", "assessor",
                      {"missing_info_description_provided": True}, now=FIXED_NOW)
    engine.transition(claim, "DOCUMENTS_VERIFIED", "document_clerk",
                      {"new_info_received": True}, now=FIXED_NOW)
    before = engine.audit_trail("ESC2")
    with pytest.raises(CycleLimitError):
        _to_under_assessment(engine, claim)
    after = engine.audit_trail("ESC2")
    assert after == before  # no new audit entry from a blocked transition
    assert claim.state == "DOCUMENTS_VERIFIED"


# --------------------------------------------------------------------------- #
# 12. Precondition evaluator — missing key vs present falsy value
# --------------------------------------------------------------------------- #
def test_precondition_present_truthy_non_boolean_passes():
    """A present, truthy non-boolean precondition value satisfies the check."""
    base = WorkflowEngine(clock=lambda: FIXED_NOW)
    config = copy.deepcopy(base._config)
    config["states"].append("REVIEW")
    config["transitions"].append(
        {
            "from": "SUBMITTED",
            "to": "REVIEW",
            "preconditions": ["reviewer_name"],
            "side_effects": [],
            "role": "clerk",
        }
    )
    eng = WorkflowEngine(config=config, clock=lambda: FIXED_NOW)
    claim = eng.new_claim("PC1")
    eng.transition(claim, "REVIEW", "clerk", {"reviewer_name": "Alice"},
                   now=FIXED_NOW)
    assert claim.state == "REVIEW"


def test_precondition_missing_key_fails_distinct_from_falsy():
    """A missing key fails; an explicitly-present falsy value also fails, but
    both are precondition failures (not silent passes)."""
    base = WorkflowEngine(clock=lambda: FIXED_NOW)
    config = copy.deepcopy(base._config)
    config["states"].append("REVIEW")
    config["transitions"].append(
        {
            "from": "SUBMITTED",
            "to": "REVIEW",
            "preconditions": ["ready"],
            "side_effects": [],
            "role": "clerk",
        }
    )
    eng = WorkflowEngine(config=config, clock=lambda: FIXED_NOW)
    # Missing key -> fail.
    c1 = eng.new_claim("PC2a")
    with pytest.raises(PreconditionError):
        eng.transition(c1, "REVIEW", "clerk", {}, now=FIXED_NOW)
    # Present but falsy -> fail.
    c2 = eng.new_claim("PC2b")
    with pytest.raises(PreconditionError):
        eng.transition(c2, "REVIEW", "clerk", {"ready": False}, now=FIXED_NOW)
