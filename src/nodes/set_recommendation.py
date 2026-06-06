from __future__ import annotations


def set_approve(state: dict) -> dict:
    calc = state.get("benefit_calculation", {})
    return {
        "recommendation": "APPROVE",
        "recommendation_reason": (
            f"Claim approved. Covered amount: {calc.get('covered_amount', 0):,.0f} THB. "
            f"{calc.get('reason', '')}"
        ),
    }


def set_reject(state: dict) -> dict:
    reasons = []

    if state.get("policy_rejection_reason"):
        reasons.append(state["policy_rejection_reason"])

    med = state.get("medical_necessity")
    if med and not med.get("is_medically_necessary"):
        reasons.append(f"Not medically necessary: {med.get('reasoning', '')}")

    calc = state.get("benefit_calculation")
    if calc and calc.get("decision") == "DENIED":
        reasons.append(calc.get("reason", ""))

    return {
        "recommendation": "REJECT",
        "recommendation_reason": ". ".join(reasons) if reasons else "Claim rejected",
    }


def set_request_more_info(state: dict) -> dict:
    missing = state.get("missing_documents", [])
    claim_type = state.get("claim", {}).get("claim_type", "")
    return {
        "recommendation": "REQUEST_MORE_INFO",
        "recommendation_reason": (
            f"Missing required documents for {claim_type} claim: {', '.join(missing)}. "
            f"Please submit the missing documents to proceed with assessment."
        ),
    }
