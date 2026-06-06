"""Deterministic guard layer for the Claim Assessment Agent (Challenge 11).

This module sits AFTER the LLM agent (src.agent.assess_claim) and enforces a
small set of hard, code-level safety rules that the LLM is not trusted to get
right on its own. It is pure and deterministic: given the same claim + agent
result it always produces the same adjusted result. It performs NO network I/O.

Guard rules enforced here:

  1. Missing required document  => REQUEST_MORE_INFO (never REJECT).
     Required docs are derived from the policy/claim_type via PolicyStore. A
     required type counts as satisfied only if a verifyDocument call in the
     tool_call_log returned that document_type with status COMPLETE.

  2. Never approve over the benefit limit. If the recommendation is APPROVE but
     the calculateBenefit tool output says DENIED, or covered_amount <= 0, or
     the covered/approved amount exceeds the applicable policy benefit limit,
     the APPROVE is blocked (downgraded to REJECT) with a specific reason.

  3. Document type mismatch. Any verified document whose type is neither a
     required nor an optional type for the claim_type is recorded as a
     TYPE_MISMATCH flag (it is never silently ignored).

The function never raises on malformed input; it degrades gracefully and records
what it could check in ``guard_flags``.
"""

from __future__ import annotations

import copy
from typing import Any

from src.document_types import doc_satisfies
from src.stores.policy_store import PolicyStore


# A required doc is satisfied ONLY if its verifyDocument status is COMPLETE.
_COMPLETE_STATUSES = {"COMPLETE"}

# Claim types the policy/required-docs map actually recognizes. Anything outside
# this set is "unknown" and must NOT have a fabricated required document applied.
_KNOWN_CLAIM_TYPES = {"OUTPATIENT", "INPATIENT", "DENTAL", "MATERNITY"}


def _resolve_policy(claim, tool_call_log, policy_store):
    """Resolve the policy for guard checks from live data only — never a
    file-backed store. Prefer the injected DB-backed ``policy_store``; otherwise
    fall back to the ``lookupPolicy`` output the agent already produced (which
    is itself the DB policy)."""
    pid = (claim or {}).get("policy_id", "")
    if policy_store is not None and pid:
        resolved = policy_store.lookup(pid)
        if resolved:
            return resolved
    out = _latest_tool_output(tool_call_log, "lookupPolicy")
    if isinstance(out, dict) and "error" not in out:
        return out
    return None


def apply_guards(claim: dict, result: dict, policy_store=None) -> dict:
    """Apply deterministic guard rules to an agent ``result``.

    Args:
        claim: the original claim dict (needs ``claim_type``; ``policy_id`` /
            ``submitted_document_ids`` are used when available).
        result: the agent result, expected to contain ``recommendation`` and
            ``tool_call_log`` (entries shaped ``{tool_name, inputs, outputs}``).
        policy_store: optional DB-backed PolicyStore so limit/eligibility checks
            use the live policy. Falls back to the lookupPolicy output in the
            tool log when omitted.

    Returns:
        A deep-copied, possibly-adjusted result with an added ``guard_flags``
        dict documenting every check. The input ``result`` is never mutated.
    """
    result = copy.deepcopy(result) if result else {}

    claim_type = (claim or {}).get("claim_type", "")
    original_recommendation = result.get("recommendation", "UNKNOWN")
    tool_call_log = result.get("tool_call_log") or []

    policy = _resolve_policy(claim, tool_call_log, policy_store)

    # A claim_type is "known" only if it appears in the required-docs map or as a
    # benefit type on the resolved policy. PolicyStore.get_required_documents
    # fabricates ['medical_receipt'] for unknown types, so for unknown types we
    # must NOT apply the missing-document override (treat required docs as empty).
    claim_type_known = _is_known_claim_type(claim_type, policy)

    if claim_type_known:
        required_docs = set(PolicyStore.get_required_documents(claim_type))
    else:
        required_docs = set()
    optional_docs = set(PolicyStore.get_optional_documents(claim_type))
    allowed_docs = required_docs | optional_docs

    verified = _collect_verified_documents(tool_call_log)

    # --- Rule 1 + Rule 3: document checks -------------------------------------
    present_types = {
        v["document_type"]
        for v in verified
        if str(v.get("status", "")).upper() in _COMPLETE_STATUSES
    }
    # A required slot is satisfied if any present type maps to it (so an OCR
    # 'receipt' fills a required 'medical_receipt'); see src.document_types.
    missing_documents = sorted(
        r for r in required_docs
        if not any(doc_satisfies(pt, r) for pt in present_types)
    )

    type_mismatches = []
    for v in verified:
        # Only flag a REAL present document (verified COMPLETE) whose type is
        # disallowed. A not-found probe (status MISSING / type 'unknown') is not
        # a type mismatch — the agent may have probed an id that doesn't exist.
        if str(v.get("status", "")).upper() not in _COMPLETE_STATUSES:
            continue
        dtype = v.get("document_type")
        if dtype in (None, "", "unknown"):
            continue
        if not any(doc_satisfies(dtype, a) for a in allowed_docs):
            type_mismatches.append(
                {
                    "document_id": v.get("document_id"),
                    "document_type": dtype,
                    "reason": (
                        f"Document type '{dtype}' is neither a required nor an "
                        f"optional document type for claim type "
                        f"'{claim_type or 'UNKNOWN'}'"
                    ),
                }
            )

    # --- Rule 2: benefit limit check ------------------------------------------
    benefit_output = _latest_tool_output(tool_call_log, "calculateBenefit")
    over_limit = _evaluate_over_limit(claim, benefit_output, policy)

    guard_flags: dict[str, Any] = {
        "claim_type": claim_type,
        "required_documents": sorted(required_docs),
        "optional_documents": sorted(optional_docs),
        "present_document_types": sorted(present_types),
        "missing_documents": missing_documents,
        "type_mismatches": type_mismatches,
        "over_limit": over_limit,
        "original_recommendation": original_recommendation,
        "overridden": False,
        "override": None,
        "override_reasons": [],
    }

    new_recommendation = original_recommendation
    override_reasons: list[str] = []

    # Rule 1 takes precedence: a missing required document can never be a REJECT
    # or APPROVE; it must become REQUEST_MORE_INFO.
    if missing_documents:
        if new_recommendation != "REQUEST_MORE_INFO":
            override_reasons.append(
                "Missing required document(s): "
                + ", ".join(missing_documents)
                + " — must REQUEST_MORE_INFO, not "
                + f"{new_recommendation}."
            )
        new_recommendation = "REQUEST_MORE_INFO"

    # Rule 2: block an over-limit / denied APPROVE. Only relevant when, after the
    # missing-doc rule, we would still be approving.
    elif new_recommendation == "APPROVE" and over_limit["blocked"]:
        new_recommendation = "REJECT"
        override_reasons.append(over_limit["reason"])

    if new_recommendation != original_recommendation:
        guard_flags["overridden"] = True
        guard_flags["override"] = {
            "from": original_recommendation,
            "to": new_recommendation,
        }
        guard_flags["override_reasons"] = override_reasons

        result["recommendation"] = new_recommendation
        prefix = " ".join(override_reasons).strip()
        existing_reason = result.get("recommendation_reason") or ""
        result["recommendation_reason"] = (
            f"[GUARD OVERRIDE {original_recommendation}->{new_recommendation}] "
            f"{prefix}"
            + (f" | Original: {existing_reason}" if existing_reason else "")
        ).strip()

    result["guard_flags"] = guard_flags
    return result


def _collect_verified_documents(tool_call_log: list[dict]) -> list[dict]:
    """Extract every verifyDocument output from the tool_call_log.

    agent.py logs entries as ``{tool_name, inputs, outputs}`` where a
    verifyDocument ``outputs`` dict carries ``document_id``/``document_type``/
    ``status``. We tolerate missing keys.
    """
    verified = []
    for entry in tool_call_log:
        if not isinstance(entry, dict):
            continue
        if entry.get("tool_name") != "verifyDocument":
            continue
        outputs = entry.get("outputs")
        if not isinstance(outputs, dict):
            continue
        verified.append(outputs)
    return verified


def _latest_tool_output(tool_call_log: list[dict], tool_name: str) -> dict | None:
    """Return the outputs of the last call to ``tool_name``, or None."""
    found = None
    for entry in tool_call_log:
        if not isinstance(entry, dict):
            continue
        if entry.get("tool_name") == tool_name and isinstance(entry.get("outputs"), dict):
            found = entry["outputs"]
    return found


_SUB_BENEFIT_LIMIT_KEYS = (
    "limit_per_visit",
    "limit_per_day",
    "limit_per_event",
    "limit_per_year",
)


def _is_known_claim_type(claim_type: str, policy: dict | None) -> bool:
    """Return True if ``claim_type`` is a recognized type.

    Recognized means it is in the static required-docs map OR it is defined as a
    benefit ``type`` on the resolved policy. Unknown/empty types must not trigger
    a fabricated required document.
    """
    if not claim_type:
        return False
    if claim_type in _KNOWN_CLAIM_TYPES:
        return True
    if policy:
        for b in policy.get("benefits", []):
            if b.get("type") == claim_type:
                return True
    return False


def _sub_benefit_cap(sub_benefit_def: dict) -> float | None:
    """Return the most specific cap defined on a single sub-benefit, or None."""
    for key in _SUB_BENEFIT_LIMIT_KEYS:
        if sub_benefit_def.get(key) is not None:
            try:
                return float(sub_benefit_def[key])
            except (TypeError, ValueError):
                return None
    return None


def _policy_benefit_limit(policy: dict | None, claim_type: str, sub_benefit: str | None) -> float | None:
    """Resolve the applicable benefit limit for a claim.

    Resolution order:
      1. If ``sub_benefit`` is given and matches a policy sub-benefit (matched
         case-insensitively and whitespace-trimmed), use that sub-benefit's most
         specific per-visit/day/event/year cap.
      2. If ``sub_benefit`` is missing or cannot be resolved BUT the benefit
         defines sub-benefit caps, fall back conservatively to the SMALLEST
         applicable sub-benefit cap (never silently jump to the larger
         annual_limit, which would let an over-cap APPROVE through).
      3. Only when there are genuinely no sub-benefit caps, use ``annual_limit``.

    Returns None if no limit can be determined.
    """
    if not policy:
        return None
    benefit = None
    for b in policy.get("benefits", []):
        if b.get("type") == claim_type:
            benefit = b
            break
    if benefit is None:
        return None

    sub_benefits = benefit.get("sub_benefits") or []

    # 1. Exact (normalized) sub-benefit match.
    if sub_benefit is not None:
        target = str(sub_benefit).strip().casefold()
        if target:
            for sb in sub_benefits:
                name = sb.get("name")
                if name is not None and str(name).strip().casefold() == target:
                    cap = _sub_benefit_cap(sb)
                    if cap is not None:
                        return cap
                    # Matched the sub-benefit but it defines no specific cap;
                    # fall through to the conservative handling below.
                    break

    # 2. Sub-benefit missing/unresolvable: use the smallest applicable cap.
    sub_caps = [c for c in (_sub_benefit_cap(sb) for sb in sub_benefits) if c is not None]
    if sub_caps:
        return min(sub_caps)

    # 3. No sub-benefit caps at all: fall back to the annual limit.
    annual = benefit.get("annual_limit")
    return float(annual) if annual is not None else None


def _evaluate_over_limit(claim: dict, benefit_output: dict | None, policy: dict | None = None) -> dict:
    """Decide whether an APPROVE should be blocked on benefit-limit grounds.

    Returns a dict describing the check. ``blocked`` is True when an APPROVE must
    not stand. We block when:
      * the calculateBenefit decision is DENIED, or
      * covered_amount <= 0, or
      * covered_amount exceeds the applicable policy benefit limit.
    If there is no calculateBenefit output at all, we block (cannot prove the
    amount is within limit).
    """
    flag = {
        "blocked": False,
        "reason": "",
        "covered_amount": None,
        "decision": None,
        "policy_limit": None,
    }

    if benefit_output is None:
        flag["blocked"] = True
        flag["reason"] = (
            "Cannot APPROVE: no calculateBenefit result is present to confirm "
            "the covered amount is within the policy benefit limit."
        )
        return flag

    decision = str(benefit_output.get("decision", "")).upper()
    covered = benefit_output.get("covered_amount")
    flag["decision"] = decision
    flag["covered_amount"] = covered

    if decision == "DENIED":
        flag["blocked"] = True
        reason = benefit_output.get("reason") or "benefit denied"
        flag["reason"] = f"Cannot APPROVE: calculateBenefit returned DENIED — {reason}."
        return flag

    try:
        covered_val = float(covered)
    except (TypeError, ValueError):
        covered_val = None

    if covered_val is None or covered_val <= 0:
        flag["blocked"] = True
        flag["reason"] = (
            f"Cannot APPROVE: covered_amount is {covered} (must be > 0)."
        )
        return flag

    # Cross-check against the policy benefit limit when we can resolve it.
    # ``policy`` is resolved upstream from the DB store / lookupPolicy output.
    sub_benefit = (claim or {}).get("sub_benefit")
    limit = _policy_benefit_limit(policy, (claim or {}).get("claim_type", ""), sub_benefit)
    flag["policy_limit"] = limit

    if limit is not None and covered_val > limit:
        flag["blocked"] = True
        flag["reason"] = (
            f"Cannot APPROVE: covered_amount {covered_val:.0f} exceeds the policy "
            f"benefit limit {limit:.0f}."
        )
        return flag

    return flag
