from __future__ import annotations

from datetime import datetime

from src.stores.policy_store import PolicyStore


def lookup_policy_node(state: dict) -> dict:
    claim = state["claim"]
    store = PolicyStore()
    policy = store.lookup(claim["policy_id"])

    log_entry = {
        "tool_name": "lookupPolicy",
        "inputs": {"policy_id": claim["policy_id"]},
        "outputs": {},
    }

    if policy is None:
        log_entry["outputs"] = {"error": "Policy not found"}
        return {
            "policy": None,
            "policy_active": False,
            "policy_rejection_reason": f"Policy {claim['policy_id']} not found",
            "tool_call_log": [log_entry],
        }

    if policy["status"] != "ACTIVE":
        log_entry["outputs"] = {"status": policy["status"]}
        return {
            "policy": policy,
            "policy_active": False,
            "policy_rejection_reason": f"Policy status is {policy['status']}, not ACTIVE",
            "tool_call_log": [log_entry],
        }

    if claim["member_id"] not in policy["member_ids"]:
        log_entry["outputs"] = {"error": "Member not in policy"}
        return {
            "policy": policy,
            "policy_active": False,
            "policy_rejection_reason": f"Member {claim['member_id']} is not covered under policy {claim['policy_id']}",
            "tool_call_log": [log_entry],
        }

    claim_date = datetime.strptime(claim["claim_date"], "%Y-%m-%d").date()
    eff = datetime.strptime(policy["effective_date"], "%Y-%m-%d").date()
    exp = datetime.strptime(policy["expiry_date"], "%Y-%m-%d").date()
    if claim_date < eff or claim_date > exp:
        log_entry["outputs"] = {"error": "Claim date outside policy period"}
        return {
            "policy": policy,
            "policy_active": False,
            "policy_rejection_reason": f"Claim date {claim['claim_date']} is outside policy period ({policy['effective_date']} to {policy['expiry_date']})",
            "tool_call_log": [log_entry],
        }

    required_docs = PolicyStore.get_required_documents(claim["claim_type"])

    log_entry["outputs"] = {"status": "ACTIVE", "benefits_count": len(policy["benefits"])}
    return {
        "policy": policy,
        "policy_active": True,
        "policy_rejection_reason": None,
        "required_documents": required_docs,
        "tool_call_log": [log_entry],
    }
