"""Core multi-tenant claim-processing runtime.

Pure functions: given a tenant config dict + a claim dict, derive the
tenant-specific outcome (required docs, approval routing, notifications,
SLA deadline, custom-field validation).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

NOTIFICATION_EVENTS = ["claim_submitted", "approved", "rejected", "payment_sent"]


def add_business_days(start: date, business_days: int) -> date:
    """Return `start` advanced by `business_days` business days (skip Sat/Sun).

    `business_days == 0` returns `start` unchanged.
    """
    if business_days < 0:
        raise ValueError("business_days must be >= 0")
    current = start
    remaining = business_days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri == 0..4
            remaining -= 1
    return current


def _resolve_required_documents(config: dict, claim_type: str) -> list[str]:
    docs = config.get("documents", {}).get(claim_type, {})
    return list(docs.get("required", []))


def _resolve_approval_routing(config: dict, amount: float) -> dict:
    if amount < 0:
        raise ValueError(f"claim amount must be >= 0, got {amount}")

    threshold = config.get("auto_approval_threshold", 0)
    # Only auto-approve a non-negative amount at or below the threshold.
    if amount <= threshold:
        return {"tier_role": "auto", "auto_approved": True}

    for tier in config.get("approval_tiers", []):
        tier_min = tier["min"]
        tier_max = tier["max"]
        # Half-open interval [min, max); unbounded top tier when max is None.
        if amount >= tier_min and (tier_max is None or amount < tier_max):
            # Never route a non-auto-approved claim to the "auto" role (a
            # phantom band can appear when auto_approval_threshold < the auto
            # tier's max). Continue to the next non-"auto" tier instead.
            if tier["role"] == "auto":
                continue
            return {"tier_role": tier["role"], "auto_approved": False}

    # No tier matched a non-negative amount: this is unroutable, not a fallback
    # to the top tier.
    raise ValueError(
        f"amount {amount} is not routable to any approval tier"
    )


def _resolve_notifications(config: dict) -> dict[str, list[str]]:
    notifications = config.get("notifications", {})
    result: dict[str, list[str]] = {}
    for event in NOTIFICATION_EVENTS:
        rule = notifications.get(event, {})
        result[event] = list(rule.get("channels", []))
    return result


def _resolve_sla_deadline(config: dict, claim_type: str, submission_date: date) -> date:
    sla = config.get("sla", {})
    days = sla.get(claim_type, sla.get("default", 7))
    return add_business_days(submission_date, days)


def _validate_custom_fields(config: dict, provided: dict) -> dict:
    required_keys: list[str] = []
    errors: list[str] = []
    for field in config.get("custom_fields", []):
        if field.get("required"):
            required_keys.append(field["key"])
            value = provided.get(field["key"])
            if value is None or value == "":
                errors.append(f"missing required custom field '{field['key']}'")
    return {
        "required": required_keys,
        "provided": dict(provided),
        "valid": len(errors) == 0,
        "errors": errors,
    }


def process_claim(config: dict, claim: dict, submission_date: date) -> dict:
    """Process a claim against a tenant config.

    Returns a dict with keys:
      required_documents, approval_routing, notifications,
      sla_deadline, custom_fields.

    Raises ValueError if the claim_type is not enabled for the tenant.
    """
    claim_type = claim.get("claim_type")
    if claim_type not in config.get("claim_types", []):
        raise ValueError(
            f"claim_type '{claim_type}' is not enabled for this tenant "
            f"(enabled: {config.get('claim_types', [])})"
        )

    amount = claim.get("amount", 0)
    provided_custom_fields = claim.get("custom_fields", {})

    return {
        "required_documents": _resolve_required_documents(config, claim_type),
        "approval_routing": _resolve_approval_routing(config, amount),
        "notifications": _resolve_notifications(config),
        "sla_deadline": _resolve_sla_deadline(config, claim_type, submission_date),
        "custom_fields": _validate_custom_fields(config, provided_custom_fields),
    }
