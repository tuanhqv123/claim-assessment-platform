from __future__ import annotations

from typing import Literal


def route_after_policy(state: dict) -> Literal["verify_documents", "set_reject"]:
    if not state.get("policy_active"):
        return "set_reject"
    return "verify_documents"


def route_after_documents(state: dict) -> Literal["check_medical", "set_request_more_info"]:
    missing = state.get("missing_documents", [])
    if missing:
        return "set_request_more_info"
    return "check_medical"


def route_after_medical(state: dict) -> Literal["calculate_benefit", "set_reject"]:
    med = state.get("medical_necessity", {})
    if not med.get("is_medically_necessary"):
        return "set_reject"
    return "calculate_benefit"


def route_after_benefit(state: dict) -> Literal["set_approve", "set_reject"]:
    calc = state.get("benefit_calculation", {})
    if calc.get("covered_amount", 0) <= 0:
        return "set_reject"
    return "set_approve"
