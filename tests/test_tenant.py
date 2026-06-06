"""Tests for the multi-tenant configuration runtime (Challenge 15)."""

import copy
from datetime import date

import pytest

from src.tenant.config_schema import validate_config
from src.tenant.diff import ABSENT, diff_configs
from src.tenant.fixtures import GOVHEALTH, HEALTHFIRST, SAFEGUARD, TENANTS
from src.tenant.runtime import add_business_days, process_claim
from src.tenant.versioning import next_version, rollback


# --- Headline requirement: same claim -> 3 tenants -> 3 different outcomes ---

def test_same_claim_three_tenants_three_different_outcomes():
    claim = {
        "claim_type": "OUTPATIENT",
        "amount": 8000,
        "custom_fields": {"employee_id": "E-1", "department": "Health", "budget_code": "BC-9"},
    }
    sub = date(2026, 6, 3)  # Wednesday

    sg = process_claim(SAFEGUARD, claim, sub)
    hf = process_claim(HEALTHFIRST, claim, sub)
    gh = process_claim(GOVHEALTH, claim, sub)

    # Routing differs: 8000 < SafeGuard auto(20000) -> auto;
    # HealthFirst auto=5000 -> assessor; GovHealth auto=0 -> committee.
    assert sg["approval_routing"] == {"tier_role": "auto", "auto_approved": True}
    assert hf["approval_routing"] == {"tier_role": "assessor", "auto_approved": False}
    assert gh["approval_routing"] == {"tier_role": "committee", "auto_approved": False}

    # Notification channels differ.
    assert sg["notifications"]["approved"] == ["email"]
    assert hf["notifications"]["approved"] == ["email", "sms"]
    assert gh["notifications"]["approved"] == ["email", "webhook"]

    # SLA deadlines differ (out=5 / default=7 / default=15 business days).
    assert sg["sla_deadline"] == add_business_days(sub, 5)
    assert hf["sla_deadline"] == add_business_days(sub, 7)
    assert gh["sla_deadline"] == add_business_days(sub, 15)
    assert len({sg["sla_deadline"], hf["sla_deadline"], gh["sla_deadline"]}) == 3

    # All three outcomes are genuinely different.
    assert sg != hf and hf != gh and sg != gh


# --- Config validation ---

def test_all_seeded_configs_are_valid():
    for name, config in TENANTS.items():
        ok, errors = validate_config(config)
        assert ok, f"{name} should validate: {errors}"


def test_validation_rejects_negative_threshold():
    bad = copy.deepcopy(SAFEGUARD)
    bad["auto_approval_threshold"] = -1
    ok, errors = validate_config(bad)
    assert not ok
    assert any("auto_approval_threshold" in e for e in errors)


def test_validation_rejects_no_claim_types():
    bad = copy.deepcopy(SAFEGUARD)
    bad["claim_types"] = []
    ok, errors = validate_config(bad)
    assert not ok
    assert any("claim type" in e for e in errors)


def test_validation_rejects_non_positive_sla():
    bad = copy.deepcopy(SAFEGUARD)
    bad["sla"]["OUTPATIENT"] = 0
    ok, errors = validate_config(bad)
    assert not ok
    assert any("sla" in e.lower() for e in errors)


def test_validation_rejects_non_contiguous_tiers():
    bad = copy.deepcopy(SAFEGUARD)
    # Introduce a gap between tiers.
    bad["approval_tiers"] = [
        {"min": 0, "max": 100, "role": "auto"},
        {"min": 200, "max": None, "role": "boss"},
    ]
    ok, errors = validate_config(bad)
    assert not ok
    assert any("contiguous" in e for e in errors)


def test_validation_rejects_auto_threshold_misaligned_to_auto_tier():
    bad = copy.deepcopy(SAFEGUARD)
    # auto tier max stays 20000 but threshold moves -> phantom band.
    bad["auto_approval_threshold"] = 100
    ok, errors = validate_config(bad)
    assert not ok
    assert any("auto_approval_threshold" in e for e in errors)


def test_validation_rejects_missing_sla_default_without_full_coverage():
    bad = copy.deepcopy(SAFEGUARD)
    # Drop the default; OUTPATIENT/INPATIENT have entries but DENTAL does not.
    bad["sla"] = {"OUTPATIENT": 5, "INPATIENT": 10}
    ok, errors = validate_config(bad)
    assert not ok
    assert any("sla" in e.lower() and "default" in e.lower() for e in errors)


def test_validation_accepts_missing_default_when_every_claim_type_covered():
    ok_cfg = copy.deepcopy(SAFEGUARD)
    ok_cfg["sla"] = {"OUTPATIENT": 5, "INPATIENT": 10, "DENTAL": 6}
    ok, errors = validate_config(ok_cfg)
    assert ok, errors


def test_validation_rejects_claim_type_without_documents():
    bad = copy.deepcopy(SAFEGUARD)
    del bad["documents"]["DENTAL"]  # DENTAL still enabled, no documents entry
    ok, errors = validate_config(bad)
    assert not ok
    assert any("documents" in e.lower() for e in errors)


# --- Approval routing / auto-approval ---

def test_auto_approval_at_and_below_threshold():
    claim = {"claim_type": "OUTPATIENT", "amount": 20000, "custom_fields": {"employee_id": "E"}}
    out = process_claim(SAFEGUARD, claim, date(2026, 6, 3))
    assert out["approval_routing"] == {"tier_role": "auto", "auto_approved": True}


def test_routing_just_above_threshold_goes_to_assessor():
    claim = {"claim_type": "OUTPATIENT", "amount": 20001, "custom_fields": {"employee_id": "E"}}
    out = process_claim(SAFEGUARD, claim, date(2026, 6, 3))
    assert out["approval_routing"] == {"tier_role": "assessor", "auto_approved": False}


def test_routing_tier_boundaries():
    base = {"claim_type": "OUTPATIENT", "custom_fields": {"employee_id": "E"}}
    sub = date(2026, 6, 3)
    # 100000 is the assessor->team_lead boundary (half-open: 100000 -> team_lead).
    out = process_claim(SAFEGUARD, {**base, "amount": 100000}, sub)
    assert out["approval_routing"]["tier_role"] == "team_lead"
    # Top unbounded tier.
    out = process_claim(SAFEGUARD, {**base, "amount": 999999}, sub)
    assert out["approval_routing"]["tier_role"] == "director"


def test_negative_amount_raises():
    claim = {"claim_type": "OUTPATIENT", "amount": -1,
             "custom_fields": {"employee_id": "E"}}
    with pytest.raises(ValueError, match="amount"):
        process_claim(SAFEGUARD, claim, date(2026, 6, 3))


def test_unmatched_amount_raises_instead_of_top_tier():
    # A config whose tiers do not cover the full non-negative range: an amount
    # above the auto threshold but below the lowest non-auto tier is unroutable
    # and must raise rather than silently falling back to the top tier.
    config = copy.deepcopy(SAFEGUARD)
    config["auto_approval_threshold"] = 100
    config["approval_tiers"] = [
        {"min": 0, "max": 100, "role": "auto"},
        {"min": 500, "max": 1000, "role": "assessor"},
        {"min": 1000, "max": None, "role": "director"},
    ]
    # This config is itself invalid (non-contiguous), but routing is a pure
    # function over the dict, so we exercise it directly.
    from src.tenant.runtime import _resolve_approval_routing

    with pytest.raises(ValueError, match="not routable"):
        _resolve_approval_routing(config, 300)


def test_routing_never_returns_auto_role_without_auto_approval():
    # auto_approval_threshold below the auto tier's max creates a phantom band
    # (100, 20000): an amount there previously routed to role "auto",
    # auto_approved=False. It must NEVER return tier_role "auto" without
    # auto-approval; here the only matching tier is "auto", so it is unroutable.
    config = copy.deepcopy(SAFEGUARD)
    config["auto_approval_threshold"] = 100  # misaligned vs auto tier max 20000
    from src.tenant.runtime import _resolve_approval_routing

    # An amount in the phantom band (100, 20000) is unroutable, NOT auto-routed.
    with pytest.raises(ValueError, match="not routable"):
        _resolve_approval_routing(config, 5000)

    # An amount in a genuine non-auto tier still routes there (auto tier skipped,
    # never returned with auto_approved=False).
    routing = _resolve_approval_routing(config, 50000)
    assert routing == {"tier_role": "assessor", "auto_approved": False}


def test_govhealth_zero_threshold_never_auto_approves():
    claim = {"claim_type": "OUTPATIENT", "amount": 1,
             "custom_fields": {"department": "X", "budget_code": "Y"}}
    out = process_claim(GOVHEALTH, claim, date(2026, 6, 3))
    assert out["approval_routing"] == {"tier_role": "committee", "auto_approved": False}


# --- Required documents ---

def test_required_documents_per_claim_type():
    sub = date(2026, 6, 3)
    op = process_claim(SAFEGUARD, {"claim_type": "OUTPATIENT", "amount": 1,
                                   "custom_fields": {"employee_id": "E"}}, sub)
    assert op["required_documents"] == ["medical_receipt"]
    ip = process_claim(SAFEGUARD, {"claim_type": "INPATIENT", "amount": 1,
                                   "custom_fields": {"employee_id": "E"}}, sub)
    assert ip["required_documents"] == ["medical_receipt", "discharge_summary", "itemized_bill"]


def test_claim_type_not_enabled_raises():
    # GovHealth does not offer DENTAL.
    claim = {"claim_type": "DENTAL", "amount": 1,
             "custom_fields": {"department": "X", "budget_code": "Y"}}
    with pytest.raises(ValueError):
        process_claim(GOVHEALTH, claim, date(2026, 6, 3))


# --- SLA business-day calculation ---

def test_add_business_days_skips_weekend():
    # Friday 2026-06-05 + 1 business day -> Monday 2026-06-08.
    assert add_business_days(date(2026, 6, 5), 1) == date(2026, 6, 8)
    # Wednesday + 5 business days -> next Wednesday.
    assert add_business_days(date(2026, 6, 3), 5) == date(2026, 6, 10)
    assert add_business_days(date(2026, 6, 3), 0) == date(2026, 6, 3)


def test_sla_deadline_uses_claim_type_then_default():
    sub = date(2026, 6, 3)
    out = process_claim(SAFEGUARD, {"claim_type": "INPATIENT", "amount": 1,
                                    "custom_fields": {"employee_id": "E"}}, sub)
    assert out["sla_deadline"] == add_business_days(sub, 10)  # INPATIENT=10
    # DENTAL has no specific SLA -> default 7.
    out = process_claim(SAFEGUARD, {"claim_type": "DENTAL", "amount": 1,
                                    "custom_fields": {"employee_id": "E"}}, sub)
    assert out["sla_deadline"] == add_business_days(sub, 7)


# --- Custom field validation ---

def test_custom_field_missing_required_produces_error():
    claim = {"claim_type": "OUTPATIENT", "amount": 1, "custom_fields": {}}
    out = process_claim(SAFEGUARD, claim, date(2026, 6, 3))
    assert out["custom_fields"]["valid"] is False
    assert any("employee_id" in e for e in out["custom_fields"]["errors"])
    assert out["custom_fields"]["required"] == ["employee_id"]


def test_custom_field_present_is_valid():
    claim = {"claim_type": "OUTPATIENT", "amount": 1, "custom_fields": {"employee_id": "E-1"}}
    out = process_claim(SAFEGUARD, claim, date(2026, 6, 3))
    assert out["custom_fields"]["valid"] is True
    assert out["custom_fields"]["errors"] == []


def test_govhealth_requires_two_custom_fields():
    claim = {"claim_type": "OUTPATIENT", "amount": 1, "custom_fields": {"department": "X"}}
    out = process_claim(GOVHEALTH, claim, date(2026, 6, 3))
    assert out["custom_fields"]["valid"] is False
    assert any("budget_code" in e for e in out["custom_fields"]["errors"])


def test_healthfirst_has_no_custom_fields():
    claim = {"claim_type": "OUTPATIENT", "amount": 1, "custom_fields": {}}
    out = process_claim(HEALTHFIRST, claim, date(2026, 6, 3))
    assert out["custom_fields"]["valid"] is True
    assert out["custom_fields"]["required"] == []


# --- Diff ---

def test_diff_detects_differences():
    diffs = diff_configs(SAFEGUARD, GOVHEALTH)
    paths = {d["path"] for d in diffs}
    assert "auto_approval_threshold" in paths
    assert any(p.startswith("claim_types") for p in paths)
    # The threshold diff should carry both values.
    thr = next(d for d in diffs if d["path"] == "auto_approval_threshold")
    assert thr["a_value"] == 20000 and thr["b_value"] == 0


def test_diff_identical_configs_is_empty():
    assert diff_configs(SAFEGUARD, copy.deepcopy(SAFEGUARD)) == []


def test_diff_detects_added_and_removed_keys():
    # An added key uses the ABSENT sentinel on the missing side, NOT None.
    a = {"x": 1}
    b = {"x": 1, "y": 2}
    diffs = diff_configs(a, b)
    assert diffs == [{"path": "y", "a_value": ABSENT, "b_value": 2}]

    # And a removed key shows ABSENT on the b side.
    diffs_rev = diff_configs(b, a)
    assert diffs_rev == [{"path": "y", "a_value": 2, "b_value": ABSENT}]


def test_diff_distinguishes_absent_key_from_real_none():
    # A key that genuinely holds None must NOT be confused with an added/removed
    # key: a real None->None on a present-on-both key produces NO diff, while an
    # absent key is reported with the ABSENT sentinel.
    a = {"logo_url": None, "only_a": None}
    b = {"logo_url": None, "only_b": None}
    diffs = diff_configs(a, b)
    paths = {d["path"]: d for d in diffs}
    assert "logo_url" not in paths  # identical real None -> no diff
    assert paths["only_a"] == {"path": "only_a", "a_value": None, "b_value": ABSENT}
    assert paths["only_b"] == {"path": "only_b", "a_value": ABSENT, "b_value": None}


# --- Versioning / rollback ---

def test_next_version():
    assert next_version([]) == 1
    assert next_version([{"version": 1, "config": {}}, {"version": 2, "config": {}}]) == 3


def test_rollback_creates_new_version_without_mutating_history():
    history = [
        {"version": 1, "config": {"auto_approval_threshold": 20000}},
        {"version": 2, "config": {"auto_approval_threshold": 5000}},
    ]
    snapshot = copy.deepcopy(history)

    new_version = rollback(history, target_version=1)

    assert new_version["version"] == 3
    assert new_version["config"] == {"auto_approval_threshold": 20000}
    assert new_version["rolled_back_from"] == 1
    # History untouched.
    assert history == snapshot
    # New version is a deep copy, not an alias.
    new_version["config"]["auto_approval_threshold"] = 999
    assert history[0]["config"]["auto_approval_threshold"] == 20000


def test_rollback_unknown_version_raises():
    with pytest.raises(ValueError):
        rollback([{"version": 1, "config": {}}], target_version=99)
