"""Tests for OCR document-type matching against required/optional doc slots."""

from __future__ import annotations

from src.document_types import doc_satisfies, match_required_documents


def test_receipt_satisfies_outpatient():
    m = match_required_documents(["medical_receipt"], ["prescription"], ["receipt"])
    assert m["satisfied"] == ["medical_receipt"]
    assert m["missing"] == []
    assert m["mismatches"] == []


def test_inpatient_receipt_only_missing_discharge():
    # receipt covers medical_receipt + itemized_bill; discharge_summary still missing.
    m = match_required_documents(
        ["medical_receipt", "discharge_summary", "itemized_bill"],
        ["prescription"],
        ["receipt"],
    )
    assert "medical_receipt" in m["satisfied"]
    assert "itemized_bill" in m["satisfied"]
    assert m["missing"] == ["discharge_summary"]


def test_inpatient_complete():
    m = match_required_documents(
        ["medical_receipt", "discharge_summary", "itemized_bill"],
        [],
        ["receipt", "discharge_summary"],
    )
    assert m["missing"] == []


def test_wrong_type_is_mismatch():
    # OUTPATIENT: required medical_receipt; optional prescription/referral.
    # A lab_report fills neither -> missing receipt + lab_report flagged mismatch.
    m = match_required_documents(
        ["medical_receipt"], ["prescription", "referral_letter"], ["lab_report"]
    )
    assert m["missing"] == ["medical_receipt"]
    assert m["mismatches"] == ["lab_report"]


def test_optional_doc_is_not_a_mismatch():
    m = match_required_documents(["medical_receipt"], ["prescription"], ["receipt", "prescription"])
    assert m["missing"] == []
    assert m["mismatches"] == []


def test_doc_satisfies_basics():
    assert doc_satisfies("receipt", "medical_receipt")
    assert doc_satisfies("discharge_summary", "discharge_summary")
    assert not doc_satisfies("lab_report", "medical_receipt")
