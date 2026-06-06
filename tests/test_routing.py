import pytest
from src.routing.conditions import (
    route_after_policy,
    route_after_documents,
    route_after_medical,
    route_after_benefit,
)


def test_route_after_policy_inactive():
    state = {"policy_active": False}
    assert route_after_policy(state) == "set_reject"


def test_route_after_policy_active():
    state = {"policy_active": True}
    assert route_after_policy(state) == "verify_documents"


def test_route_after_documents_missing():
    state = {"missing_documents": ["discharge_summary"]}
    assert route_after_documents(state) == "set_request_more_info"


def test_route_after_documents_all_present():
    state = {"missing_documents": []}
    assert route_after_documents(state) == "check_medical"


def test_route_after_medical_not_necessary():
    state = {"medical_necessity": {"is_medically_necessary": False}}
    assert route_after_medical(state) == "set_reject"


def test_route_after_medical_necessary():
    state = {"medical_necessity": {"is_medically_necessary": True}}
    assert route_after_medical(state) == "calculate_benefit"


def test_route_after_benefit_denied():
    state = {"benefit_calculation": {"covered_amount": 0, "decision": "DENIED"}}
    assert route_after_benefit(state) == "set_reject"


def test_route_after_benefit_covered():
    state = {"benefit_calculation": {"covered_amount": 2000, "decision": "COVERED"}}
    assert route_after_benefit(state) == "set_approve"
