import json
import os
from pathlib import Path

import pytest

from src.graph import compile_agent

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


def _run_claim(claim_filename: str) -> dict:
    claim = json.loads(Path(f"data/claims/{claim_filename}").read_text())
    agent = compile_agent()
    state = {
        "claim": claim,
        "policy": None,
        "policy_active": False,
        "policy_rejection_reason": None,
        "document_reviews": [],
        "required_documents": [],
        "missing_documents": [],
        "medical_necessity": None,
        "benefit_calculation": None,
        "recommendation": None,
        "recommendation_reason": None,
        "report": None,
        "tool_call_log": [],
    }
    return agent.invoke(state)


class TestCase1Approve:
    def test_recommendation_is_approve(self):
        result = _run_claim("case_1_approve.json")
        assert result["recommendation"] == "APPROVE"

    def test_covered_amount_is_correct(self):
        result = _run_claim("case_1_approve.json")
        assert result["benefit_calculation"]["covered_amount"] == 2000

    def test_all_tools_called(self):
        result = _run_claim("case_1_approve.json")
        tool_names = [entry["tool_name"] for entry in result["tool_call_log"]]
        assert "lookupPolicy" in tool_names
        assert "verifyDocument" in tool_names
        assert "checkMedicalNecessity" in tool_names
        assert "calculateBenefit" in tool_names

    def test_report_is_generated(self):
        result = _run_claim("case_1_approve.json")
        assert result["report"] is not None
        assert "recommendation" in result["report"]


class TestCase2Reject:
    def test_recommendation_is_reject(self):
        result = _run_claim("case_2_reject.json")
        assert result["recommendation"] == "REJECT"

    def test_rejection_cites_exclusion(self):
        result = _run_claim("case_2_reject.json")
        assert "T&C 8.2" in result["recommendation_reason"]


class TestCase3RequestMoreInfo:
    def test_recommendation_is_request_more_info(self):
        result = _run_claim("case_3_request_info.json")
        assert result["recommendation"] == "REQUEST_MORE_INFO"

    def test_identifies_missing_discharge_summary(self):
        result = _run_claim("case_3_request_info.json")
        assert "discharge_summary" in result["recommendation_reason"]

    def test_stops_at_document_verification(self):
        result = _run_claim("case_3_request_info.json")
        tool_names = [entry["tool_name"] for entry in result["tool_call_log"]]
        assert "checkMedicalNecessity" not in tool_names
        assert "calculateBenefit" not in tool_names
