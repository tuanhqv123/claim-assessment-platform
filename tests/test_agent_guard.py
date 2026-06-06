"""Unit tests for the deterministic guard layer (src.guard.apply_guards).

These tests use SYNTHETIC agent results / tool_call_logs only. They perform no
network I/O and must be fast and deterministic.
"""

from __future__ import annotations

from src.guard import apply_guards


# --- helpers ----------------------------------------------------------------

def _verify_entry(doc_id: str, doc_type: str, status: str = "COMPLETE") -> dict:
    return {
        "tool_name": "verifyDocument",
        "inputs": {"documentId": doc_id},
        "outputs": {
            "document_id": doc_id,
            "document_type": doc_type,
            "status": status,
            "issues": [],
        },
    }


def _benefit_entry(covered_amount, decision="COVERED", reason="Fully covered") -> dict:
    return {
        "tool_name": "calculateBenefit",
        "inputs": {},
        "outputs": {
            "covered_amount": covered_amount,
            "decision": decision,
            "reason": reason,
        },
    }


def _policy_entry() -> dict:
    """Synthetic lookupPolicy output, mirroring the live DB policy shape. The
    guard resolves benefit limits from this (the policy the agent looked up) —
    never from a file-backed store."""
    return {
        "tool_name": "lookupPolicy",
        "inputs": {"policyId": "POL-001"},
        "outputs": {
            "policy_id": "POL-001",
            "benefits": [
                {
                    "type": "OUTPATIENT",
                    "annual_limit": 100000,
                    "sub_benefits": [
                        {"name": "Doctor Visit", "limit_per_visit": 3000, "visits_per_year": 30},
                        {"name": "Prescribed Medicine", "limit_per_visit": 3000},
                        {"name": "Diagnostic Tests", "limit_per_year": 20000},
                    ],
                }
            ],
        },
    }


# --- Rule 1: missing required document --> REQUEST_MORE_INFO -----------------

def test_missing_required_document_overrides_to_request_more_info():
    # INPATIENT requires medical_receipt, discharge_summary, itemized_bill.
    # discharge_summary is missing here.
    claim = {
        "claim_id": "CLM-X",
        "policy_id": "POL-003",
        "claim_type": "INPATIENT",
        "sub_benefit": "Surgery",
    }
    result = {
        "claim_id": "CLM-X",
        "recommendation": "APPROVE",
        "recommendation_reason": "Looks fine to me",
        "tool_call_log": [
            _verify_entry("DOC-1", "medical_receipt"),
            _verify_entry("DOC-2", "itemized_bill"),
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "REQUEST_MORE_INFO"
    flags = out["guard_flags"]
    assert flags["overridden"] is True
    assert flags["override"] == {"from": "APPROVE", "to": "REQUEST_MORE_INFO"}
    assert "discharge_summary" in flags["missing_documents"]
    assert "discharge_summary" in out["recommendation_reason"]


def test_ocr_receipt_satisfies_medical_receipt():
    # OUTPATIENT requires medical_receipt. An OCR-classified 'receipt' satisfies
    # it via src.document_types.doc_satisfies, so a clean APPROVE passes through.
    claim = {"claim_id": "CLM-R", "policy_id": "POL-001", "claim_type": "OUTPATIENT", "sub_benefit": "Doctor Visit"}
    result = {
        "claim_id": "CLM-R",
        "recommendation": "APPROVE",
        "recommendation_reason": "ok",
        "tool_call_log": [
            _verify_entry("receipt_1.png", "receipt"),
            _benefit_entry(2000, decision="COVERED"),
        ],
    }
    out = apply_guards(claim, result)
    assert out["guard_flags"]["missing_documents"] == []
    assert out["recommendation"] == "APPROVE"
    assert out["guard_flags"]["overridden"] is False


def test_ocr_receipt_alone_misses_discharge_summary_for_inpatient():
    # INPATIENT requires medical_receipt + discharge_summary + itemized_bill.
    # A single OCR 'receipt' covers medical_receipt + itemized_bill, so only
    # discharge_summary remains missing -> REQUEST_MORE_INFO.
    claim = {"claim_id": "CLM-I", "policy_id": "POL-003", "claim_type": "INPATIENT", "sub_benefit": "Surgery"}
    result = {
        "claim_id": "CLM-I",
        "recommendation": "APPROVE",
        "recommendation_reason": "ok",
        "tool_call_log": [_verify_entry("receipt_2.png", "receipt")],
    }
    out = apply_guards(claim, result)
    assert out["recommendation"] == "REQUEST_MORE_INFO"
    assert out["guard_flags"]["missing_documents"] == ["discharge_summary"]


def test_missing_required_document_never_rejects():
    # A REJECT for a claim with a missing required doc must be flipped to
    # REQUEST_MORE_INFO, never left as REJECT.
    claim = {"claim_id": "C", "policy_id": "POL-001", "claim_type": "OUTPATIENT"}
    result = {
        "recommendation": "REJECT",
        "recommendation_reason": "no receipt",
        "tool_call_log": [
            _verify_entry("DOC-9", "prescription"),  # optional, not the required receipt
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "REQUEST_MORE_INFO"
    assert out["guard_flags"]["missing_documents"] == ["medical_receipt"]


# --- Rule 2: never approve over the benefit limit ---------------------------

def test_over_limit_approve_is_blocked():
    # OUTPATIENT / Doctor Visit limit_per_visit is 3000 in POL-001.
    claim = {
        "claim_id": "C",
        "policy_id": "POL-001",
        "claim_type": "OUTPATIENT",
        "sub_benefit": "Doctor Visit",
    }
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "approve full amount",
        "tool_call_log": [
            _policy_entry(),
            _verify_entry("DOC-1", "medical_receipt"),
            _benefit_entry(covered_amount=9999, decision="COVERED"),
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "REJECT"
    assert out["guard_flags"]["over_limit"]["blocked"] is True
    assert out["guard_flags"]["over_limit"]["policy_limit"] == 3000
    assert "exceeds" in out["recommendation_reason"].lower()


def test_denied_benefit_blocks_approve():
    claim = {
        "claim_id": "C",
        "policy_id": "POL-001",
        "claim_type": "OUTPATIENT",
        "sub_benefit": "Doctor Visit",
    }
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "approve",
        "tool_call_log": [
            _verify_entry("DOC-1", "medical_receipt"),
            _benefit_entry(covered_amount=0, decision="DENIED", reason="Excluded under T&C 8.2"),
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "REJECT"
    assert out["guard_flags"]["over_limit"]["blocked"] is True


def test_missing_benefit_calc_blocks_approve():
    claim = {
        "claim_id": "C",
        "policy_id": "POL-001",
        "claim_type": "OUTPATIENT",
        "sub_benefit": "Doctor Visit",
    }
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "approve",
        "tool_call_log": [
            _verify_entry("DOC-1", "medical_receipt"),
            # no calculateBenefit call
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "REJECT"
    assert out["guard_flags"]["over_limit"]["blocked"] is True


def test_over_limit_approve_blocked_when_sub_benefit_missing():
    # POL-001 OUTPATIENT sub-benefit caps are 3000 / 3000 / 20000; smallest = 3000.
    # With sub_benefit absent, the guard must fall back to the SMALLEST cap (3000)
    # and still block an over-cap APPROVE rather than jumping to annual_limit
    # (100000), which would have let 9999 through.
    claim = {
        "claim_id": "C",
        "policy_id": "POL-001",
        "claim_type": "OUTPATIENT",
        # no sub_benefit key
    }
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "approve full amount",
        "tool_call_log": [
            _policy_entry(),
            _verify_entry("DOC-1", "medical_receipt"),
            _benefit_entry(covered_amount=9999, decision="COVERED"),
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "REJECT"
    assert out["guard_flags"]["over_limit"]["blocked"] is True
    assert out["guard_flags"]["over_limit"]["policy_limit"] == 3000
    assert "exceeds" in out["recommendation_reason"].lower()


def test_over_limit_approve_blocked_when_sub_benefit_casing_differs():
    # Same as above but sub_benefit casing/whitespace differs from the policy
    # name "Doctor Visit". It must still resolve via normalized matching to the
    # 3000 per-visit cap and block the 9999 APPROVE.
    claim = {
        "claim_id": "C",
        "policy_id": "POL-001",
        "claim_type": "OUTPATIENT",
        "sub_benefit": "  doctor VISIT  ",
    }
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "approve full amount",
        "tool_call_log": [
            _policy_entry(),
            _verify_entry("DOC-1", "medical_receipt"),
            _benefit_entry(covered_amount=9999, decision="COVERED"),
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "REJECT"
    assert out["guard_flags"]["over_limit"]["blocked"] is True
    assert out["guard_flags"]["over_limit"]["policy_limit"] == 3000
    assert "exceeds" in out["recommendation_reason"].lower()


def test_incomplete_required_doc_treated_as_missing():
    # A required doc returned with status INCOMPLETE does NOT satisfy the
    # requirement; the claim must be downgraded to REQUEST_MORE_INFO.
    claim = {
        "claim_id": "C",
        "policy_id": "POL-001",
        "claim_type": "OUTPATIENT",
        "sub_benefit": "Doctor Visit",
    }
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "approve",
        "tool_call_log": [
            _verify_entry("DOC-1", "medical_receipt", status="INCOMPLETE"),
            _benefit_entry(covered_amount=2000, decision="COVERED"),
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "REQUEST_MORE_INFO"
    assert out["guard_flags"]["missing_documents"] == ["medical_receipt"]
    assert out["guard_flags"]["present_document_types"] == []


def test_verified_status_does_not_satisfy_required_type():
    # Only COMPLETE satisfies a required doc; VERIFIED must NOT count.
    claim = {
        "claim_id": "C",
        "policy_id": "POL-001",
        "claim_type": "OUTPATIENT",
        "sub_benefit": "Doctor Visit",
    }
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "approve",
        "tool_call_log": [
            _verify_entry("DOC-1", "medical_receipt", status="VERIFIED"),
            _benefit_entry(covered_amount=2000, decision="COVERED"),
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "REQUEST_MORE_INFO"
    assert out["guard_flags"]["missing_documents"] == ["medical_receipt"]
    assert "medical_receipt" not in out["guard_flags"]["present_document_types"]


def test_unknown_claim_type_does_not_flip_valid_approve():
    # An unrecognized claim_type must NOT fabricate a phantom required document
    # (PolicyStore defaults unknown types to ['medical_receipt']). An otherwise
    # valid APPROVE must pass through unchanged.
    claim = {
        "claim_id": "C",
        "policy_id": "POL-001",
        "claim_type": "WELLNESS",  # not a known claim type
    }
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "valid approve",
        "tool_call_log": [
            # No documents at all; without the fix a phantom medical_receipt
            # would be flagged missing and flip this to REQUEST_MORE_INFO.
            _benefit_entry(covered_amount=2000, decision="COVERED"),
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "APPROVE"
    flags = out["guard_flags"]
    assert flags["overridden"] is False
    assert flags["required_documents"] == []
    assert flags["missing_documents"] == []


# --- Rule 3: document type mismatch -----------------------------------------

def test_type_mismatch_is_flagged():
    # 'consultation_notes' is neither required nor optional for OUTPATIENT.
    claim = {
        "claim_id": "C",
        "policy_id": "POL-001",
        "claim_type": "OUTPATIENT",
        "sub_benefit": "Doctor Visit",
    }
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "ok",
        "tool_call_log": [
            _verify_entry("DOC-1", "medical_receipt"),
            _verify_entry("DOC-2", "consultation_notes"),
            _benefit_entry(covered_amount=2000, decision="COVERED"),
        ],
    }

    out = apply_guards(claim, result)

    mismatches = out["guard_flags"]["type_mismatches"]
    assert len(mismatches) == 1
    assert mismatches[0]["document_type"] == "consultation_notes"
    assert mismatches[0]["document_id"] == "DOC-2"
    # A type mismatch alone does not change a valid APPROVE.
    assert out["recommendation"] == "APPROVE"


# --- Clean APPROVE passes through unchanged ----------------------------------

def test_clean_approve_passes_through_unchanged():
    claim = {
        "claim_id": "CLM-001",
        "policy_id": "POL-001",
        "claim_type": "OUTPATIENT",
        "sub_benefit": "Doctor Visit",
    }
    result = {
        "claim_id": "CLM-001",
        "recommendation": "APPROVE",
        "recommendation_reason": "All documents present, medically necessary, within limit.",
        "tool_call_log": [
            _verify_entry("DOC-1", "medical_receipt"),
            _verify_entry("DOC-2", "prescription"),  # optional, allowed
            _benefit_entry(covered_amount=2000, decision="COVERED"),
        ],
    }

    out = apply_guards(claim, result)

    assert out["recommendation"] == "APPROVE"
    flags = out["guard_flags"]
    assert flags["overridden"] is False
    assert flags["missing_documents"] == []
    assert flags["type_mismatches"] == []
    assert flags["over_limit"]["blocked"] is False
    # Original reason is preserved untouched.
    assert out["recommendation_reason"] == result["recommendation_reason"]


def test_input_result_not_mutated():
    claim = {"claim_id": "C", "policy_id": "POL-001", "claim_type": "OUTPATIENT", "sub_benefit": "Doctor Visit"}
    result = {
        "recommendation": "APPROVE",
        "recommendation_reason": "x",
        "tool_call_log": [_verify_entry("DOC-1", "prescription")],  # missing required receipt
    }

    apply_guards(claim, result)

    # The original is untouched.
    assert result["recommendation"] == "APPROVE"
    assert "guard_flags" not in result
