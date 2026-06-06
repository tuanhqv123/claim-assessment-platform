import pytest
from src.nodes.lookup_policy import lookup_policy_node
from src.nodes.verify_documents import verify_documents_node
from src.nodes.check_medical import check_medical_node
from src.nodes.set_recommendation import set_approve, set_reject, set_request_more_info


class TestLookupPolicyNode:
    def test_active_policy_returns_active(self):
        state = {"claim": {"policy_id": "POL-001", "member_id": "MBR-001", "claim_date": "2024-06-01", "claim_type": "OUTPATIENT"}}
        result = lookup_policy_node(state)
        assert result["policy_active"] is True
        assert result["policy"] is not None

    def test_nonexistent_policy_returns_inactive(self):
        state = {"claim": {"policy_id": "POL-999", "member_id": "MBR-001", "claim_date": "2024-06-01", "claim_type": "OUTPATIENT"}}
        result = lookup_policy_node(state)
        assert result["policy_active"] is False
        assert "not found" in result["policy_rejection_reason"]

    def test_member_not_in_policy(self):
        state = {"claim": {"policy_id": "POL-001", "member_id": "MBR-999", "claim_date": "2024-06-01", "claim_type": "OUTPATIENT"}}
        result = lookup_policy_node(state)
        assert result["policy_active"] is False
        assert "not covered" in result["policy_rejection_reason"]

    def test_claim_date_outside_policy(self):
        state = {"claim": {"policy_id": "POL-001", "member_id": "MBR-001", "claim_date": "2025-06-01", "claim_type": "OUTPATIENT"}}
        result = lookup_policy_node(state)
        assert result["policy_active"] is False
        assert "outside policy period" in result["policy_rejection_reason"]

    def test_tool_call_logged(self):
        state = {"claim": {"policy_id": "POL-001", "member_id": "MBR-001", "claim_date": "2024-06-01", "claim_type": "OUTPATIENT"}}
        result = lookup_policy_node(state)
        assert len(result["tool_call_log"]) == 1
        assert result["tool_call_log"][0]["tool_name"] == "lookupPolicy"


class TestVerifyDocumentsNode:
    def test_all_docs_present_outpatient(self):
        state = {
            "claim": {"submitted_document_ids": ["DOC-001", "DOC-002"], "claim_type": "OUTPATIENT"},
            "required_documents": ["medical_receipt"],
        }
        result = verify_documents_node(state)
        assert result["missing_documents"] == []

    def test_missing_discharge_summary_inpatient(self):
        state = {
            "claim": {"submitted_document_ids": ["DOC-020", "DOC-021"], "claim_type": "INPATIENT"},
            "required_documents": ["medical_receipt", "discharge_summary", "itemized_bill"],
        }
        result = verify_documents_node(state)
        assert "discharge_summary" in result["missing_documents"]

    def test_each_doc_logged(self):
        state = {
            "claim": {"submitted_document_ids": ["DOC-001", "DOC-002"], "claim_type": "OUTPATIENT"},
            "required_documents": ["medical_receipt"],
        }
        result = verify_documents_node(state)
        assert len(result["tool_call_log"]) == 2
        assert all(e["tool_name"] == "verifyDocument" for e in result["tool_call_log"])


class TestSetRecommendation:
    def test_set_approve(self):
        state = {"benefit_calculation": {"covered_amount": 2000, "reason": "Copay 20%"}}
        result = set_approve(state)
        assert result["recommendation"] == "APPROVE"
        assert "2,000" in result["recommendation_reason"]

    def test_set_reject_with_policy_reason(self):
        state = {"policy_rejection_reason": "Policy LAPSED", "medical_necessity": None, "benefit_calculation": None}
        result = set_reject(state)
        assert result["recommendation"] == "REJECT"
        assert "LAPSED" in result["recommendation_reason"]

    def test_set_reject_with_exclusion(self):
        state = {"policy_rejection_reason": None, "medical_necessity": None, "benefit_calculation": {"decision": "DENIED", "reason": "Excluded under T&C 8.2"}}
        result = set_reject(state)
        assert "T&C 8.2" in result["recommendation_reason"]

    def test_set_request_more_info(self):
        state = {"missing_documents": ["discharge_summary"], "claim": {"claim_type": "INPATIENT"}}
        result = set_request_more_info(state)
        assert result["recommendation"] == "REQUEST_MORE_INFO"
        assert "discharge_summary" in result["recommendation_reason"]
