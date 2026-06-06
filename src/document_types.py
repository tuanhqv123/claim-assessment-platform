"""Bridge between OCR-classified document types and policy required-doc names.

The OCR pipeline (Challenge 08) classifies an uploaded document as one of:
    receipt | discharge_summary | lab_report | prescription
The policy / tenant required-document names (Challenge 11/15) use a richer set:
    medical_receipt, dental_receipt, optical_receipt, itemized_bill,
    discharge_summary, prescription, referral_letter, treatment_plan, ...

``doc_satisfies`` lets document verification work on REAL uploaded files: e.g. an
OCR-classified 'receipt' satisfies a required 'medical_receipt'/'itemized_bill'.
"""

from __future__ import annotations

# An OCR-classified type "satisfies" these required-doc-name slots.
OCR_TYPE_SATISFIES: dict[str, set[str]] = {
    "receipt": {"medical_receipt", "dental_receipt", "optical_receipt", "itemized_bill"},
    "discharge_summary": {"discharge_summary"},
    "lab_report": {"lab_report", "diagnostic_report"},
    "prescription": {"prescription"},
}


def doc_satisfies(doc_type: str | None, required_type: str | None) -> bool:
    """True if a document of ``doc_type`` fills a ``required_type`` slot.

    Matches on normalized equality (so legacy 'medical_receipt' == 'medical_receipt')
    or via the OCR->required mapping (so OCR 'receipt' satisfies 'medical_receipt').
    """
    if not doc_type or not required_type:
        return False
    dt = str(doc_type).strip().lower()
    rt = str(required_type).strip().lower()
    if dt == rt:
        return True
    return rt in OCR_TYPE_SATISFIES.get(dt, set())


def match_required_documents(
    required: list[str],
    optional: list[str],
    uploaded_types: list[str],
) -> dict:
    """Match uploaded (OCR-classified) document types against a claim type's slots.

    Returns ``{satisfied, missing, mismatches}``:
      - satisfied:  required slot names filled by some uploaded type
      - missing:    required slot names not filled by any upload
      - mismatches: uploaded types that fill neither a required nor optional slot
    """
    req = [r for r in (required or []) if r]
    opt = [o for o in (optional or []) if o]
    uploaded = [u for u in (uploaded_types or []) if u]

    satisfied = [r for r in req if any(doc_satisfies(u, r) for u in uploaded)]
    missing = [r for r in req if r not in satisfied]
    allowed = req + opt
    mismatches = sorted(
        {u for u in uploaded if not any(doc_satisfies(u, a) for a in allowed)}
    )
    return {"satisfied": satisfied, "missing": missing, "mismatches": mismatches}
