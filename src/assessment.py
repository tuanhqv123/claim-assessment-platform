"""Safe entry point for claim assessment.

Runs the LLM tool-calling agent (src.agent.assess_claim) and then applies the
deterministic guard layer (src.guard.apply_guards) on top of its result. Callers
should prefer ``run_assessment`` over calling ``assess_claim`` directly, because
only this path enforces the Challenge 11 safety rules.
"""

from __future__ import annotations

from src.agent import assess_claim
from src.guard import apply_guards
from src.stores.document_store import DocumentStore
from src.stores.policy_store import PolicyStore


def _enforce_member_eligibility(
    claim: dict, result: dict, policy_store: PolicyStore | None
) -> dict:
    """Deterministic backstop: a member who is not enrolled in the policy is not
    covered, so the claim must be REJECTED — regardless of what the LLM decided
    or what the document guards concluded. (No point asking for more documents
    from someone the policy doesn't cover.)

    Verifiable only when we can resolve the policy AND it carries a non-empty
    member roster; otherwise we leave the result untouched (can't prove
    ineligibility, so don't guess).
    """
    policy_id = (claim or {}).get("policy_id") or ""
    member_id = (claim or {}).get("member_id") or ""
    if not policy_store or not policy_id or not member_id:
        return result

    policy = policy_store.lookup(policy_id)
    if not policy:
        return result
    member_ids = policy.get("member_ids") or []
    if not member_ids:
        return result  # roster unknown -> can't verify enrollment

    eligible = member_id in member_ids
    flags = result.setdefault("guard_flags", {})
    flags["member_eligibility"] = {
        "member_id": member_id,
        "policy_id": policy_id,
        "eligible": eligible,
    }
    if eligible or result.get("recommendation") == "REJECT":
        return result

    reason = (
        f"Member {member_id} is not enrolled in policy {policy_id} "
        f"— not covered."
    )
    flags["overridden"] = True
    flags["override"] = {"from": result.get("recommendation"), "to": "REJECT"}
    flags.setdefault("override_reasons", []).append(reason)
    result["recommendation"] = "REJECT"
    if not result.get("recommendation_reason"):
        result["recommendation_reason"] = reason
    return result


def run_assessment(
    claim: dict,
    doc_store: DocumentStore | None = None,
    policy_store: PolicyStore | None = None,
) -> dict:
    """Assess a claim and apply deterministic guards.

    Args:
        claim: the claim dict.
        doc_store: optional document store so verifyDocument resolves real
            uploaded documents (e.g. built from DB rows) instead of the demo
            file-backed store.
        policy_store: optional policy store so lookupPolicy / retrievePolicyClauses
            resolve the live DB policy (and its uploaded document) instead of the
            file-backed demo policies.

    Returns:
        The agent result, adjusted by the guard layer, with a ``guard_flags``
        key documenting every check performed.
    """
    result = assess_claim(claim, doc_store=doc_store, policy_store=policy_store)
    result = apply_guards(claim, result)
    return _enforce_member_eligibility(claim, result, policy_store)
