"""Integration tests running the 3 real cases through src.assessment.run_assessment
against the LIVE LLM. Skipped when OPENAI_API_KEY is not set.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.assessment import run_assessment

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


def _load(claim_filename: str) -> dict:
    return json.loads(Path(f"data/claims/{claim_filename}").read_text())


def _tool_names(result: dict) -> list[str]:
    return [e.get("tool_name") for e in result.get("tool_call_log", [])]


class TestCase1Approve:
    def test_approve_and_all_tools_called(self):
        result = run_assessment(_load("case_1_approve.json"))

        assert result["recommendation"] == "APPROVE", result.get("recommendation_reason")

        names = _tool_names(result)
        for tool in ("lookupPolicy", "verifyDocument", "checkMedicalNecessity", "calculateBenefit"):
            assert tool in names, f"{tool} missing from log: {names}"

        # Clean case: guard should not have overridden anything.
        assert result["guard_flags"]["overridden"] is False
        assert result["guard_flags"]["missing_documents"] == []


class TestCase2Reject:
    def test_reject_cites_tnc_8_2(self):
        result = run_assessment(_load("case_2_reject.json"))

        assert result["recommendation"] == "REJECT", result.get("recommendation_reason")

        # Citation can appear in the reason, the report, or a guard override.
        haystack = json.dumps(result, default=str)
        assert "T&C 8.2" in haystack


class TestCase3RequestMoreInfo:
    def test_request_more_info_for_missing_discharge_summary(self):
        result = run_assessment(_load("case_3_request_info.json"))

        assert result["recommendation"] == "REQUEST_MORE_INFO", result.get("recommendation_reason")

        # discharge_summary is the missing required doc — must be surfaced.
        haystack = json.dumps(result, default=str)
        assert "discharge_summary" in haystack

        # Either the LLM stopped before medical/benefit, OR the guard overrode to
        # REQUEST_MORE_INFO. Verify the missing doc was detected by the guard.
        assert "discharge_summary" in result["guard_flags"]["missing_documents"]
