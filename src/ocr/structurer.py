"""Stage B: turn raw OCR text into the structured Challenge-08 schema via the LLM.

Output schema (exactly):
{ "document_type": "receipt|discharge_summary|lab_report|prescription",
  "confidence": 0.0-1.0,
  "fields": { "<field>": { "value": <any|null>, "confidence": 0.0-1.0 }, ... },
  "validation_errors": [ "..." ] }
"""
from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from src.config import require_env

load_dotenv()

_client = OpenAI(
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY") or "none",
)

# Field sets per document type (these are the fields the LLM must populate).
FIELD_SPECS = {
    "receipt": (
        "hospital_name, patient_name, date, "
        "items (a LIST of objects each with description, quantity, unit_price, total), "
        "total_cost (the total billed treatment cost), "
        "insurance_paid (amount the health-insurance fund / insurer pays or covers — "
        "e.g. Vietnamese 'Số tiền Quỹ BHYT thanh toán', or 'insurance paid'/'covered by insurer'), "
        "patient_paid (amount the patient pays out of pocket — e.g. Vietnamese "
        "'Người bệnh trả', or 'patient responsibility'/'co-pay'), "
        "grand_total, payment_method"
    ),
    "discharge_summary": (
        "hospital_name, patient_name, admission_date, discharge_date, "
        "diagnosis (an object with primary and secondary), "
        "procedures_performed, attending_physician, discharge_instructions"
    ),
    "lab_report": (
        "lab_name, patient_name, date, "
        "tests (a LIST of objects each with test_name, result, unit, reference_range, flag)"
    ),
    "prescription": (
        "doctor_name, patient_name, date, "
        "medications (a LIST of objects each with name, dosage, frequency, duration, quantity)"
    ),
}

SYSTEM_PROMPT = (
    "You are a medical-document information extraction engine for an insurance "
    "claims platform. You receive raw OCR text of a single document and return "
    "STRICT JSON only.\n\n"
    "Classify the document as exactly one of: receipt, discharge_summary, "
    "lab_report, prescription.\n\n"
    "Field sets to extract per type:\n"
    f"- receipt: {FIELD_SPECS['receipt']}\n"
    f"- discharge_summary: {FIELD_SPECS['discharge_summary']}\n"
    f"- lab_report: {FIELD_SPECS['lab_report']}\n"
    f"- prescription: {FIELD_SPECS['prescription']}\n\n"
    "Output object shape EXACTLY:\n"
    "{\n"
    '  "document_type": "<one of the four>",\n'
    '  "confidence": <float 0..1 for the classification>,\n'
    '  "fields": {\n'
    '     "<field_name>": { "value": <string|number|object|array|null>, '
    '"confidence": <float 0..1> },\n'
    "     ... one entry for EVERY field in the matching type's field set ...\n"
    "  },\n"
    '  "validation_errors": []\n'
    "}\n\n"
    "RULES:\n"
    "1. Include EVERY field of the chosen type, even if not present.\n"
    "2. If a field is NOT visible in the OCR text, set its value to null and a "
    "LOW confidence (<= 0.3). NEVER invent or hallucinate values.\n"
    "3. Give a realistic per-field confidence reflecting how clearly the value "
    "was read (clear printed value ~0.9-0.98; partly garbled ~0.5-0.8; "
    "absent/null <= 0.3). Do NOT make every confidence 1.0.\n"
    "4. For list fields (items/tests/medications), value is a JSON array of "
    "objects with the specified keys; use null for any missing sub-field.\n"
    "5. Numbers (amounts, quantities, results) should be JSON numbers when they "
    "are clearly numeric; strip currency symbols and thousands separators "
    "(e.g. '7,128.00' -> 7128.00). Keep dates as the literal printed string.\n"
    "6. Leave validation_errors as an empty array (validation runs separately).\n"
    "7. INSURANCE FOCUS: this is an insurance-claims platform, so the most "
    "important values are the INSURANCE AMOUNTS — the total billed cost, the "
    "amount the insurer / health-insurance fund pays (e.g. Vietnamese 'Quỹ BHYT "
    "thanh toán'), and the amount the patient pays. Documents may be in any "
    "language including Vietnamese — extract these amounts regardless of language.\n"
    "8. Return ONLY the JSON object, no markdown, no commentary."
)


def structure(raw_text: str) -> dict:
    """Call the LLM to convert raw OCR text into the Challenge-08 schema dict."""
    resp = _client.chat.completions.create(
        model=require_env("OPENAI_MODEL"),
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Raw OCR text of the document:\n\n" + raw_text,
            },
        ],
    )
    content = resp.choices[0].message.content
    return _parse_content(content)


def _parse_content(content: str | None) -> dict:
    """Parse the LLM's text output into the schema, degrading gracefully.

    Handles None/empty content and markdown-fenced JSON, and never raises on a
    parse failure: returns a valid empty-schema dict instead.
    """
    empty = {
        "document_type": "receipt",
        "confidence": 0.0,
        "fields": {},
        "validation_errors": ["LLM output not parseable as JSON"],
    }
    if not content or not content.strip():
        return empty

    text = content.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```).
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError):
        return empty
    if not isinstance(data, dict):
        return empty
    return _normalize(data)


def _normalize(data: dict) -> dict:
    """Defensively coerce the LLM output into the exact schema shape."""
    out: dict = {}
    dt = data.get("document_type")
    if dt not in FIELD_SPECS:
        # Best-effort fallback so downstream never breaks on a bad label.
        dt = dt if isinstance(dt, str) else "receipt"
    out["document_type"] = dt
    try:
        out["confidence"] = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        out["confidence"] = 0.0

    fields = data.get("fields") or {}
    norm_fields: dict = {}
    if isinstance(fields, dict):
        for k, v in fields.items():
            if isinstance(v, dict) and "value" in v:
                try:
                    conf = float(v.get("confidence", 0.0))
                except (TypeError, ValueError):
                    conf = 0.0
                value = v.get("value")
            else:
                # LLM put a bare value; wrap it.
                value = v
                conf = 0.5
            # Anti-hallucination: a null value must never carry high confidence.
            if value is None and conf > 0.3:
                conf = 0.3
            norm_fields[k] = {"value": value, "confidence": conf}
    out["fields"] = norm_fields

    ve = data.get("validation_errors")
    out["validation_errors"] = ve if isinstance(ve, list) else []
    return out


if __name__ == "__main__":
    import sys

    from src.ocr.dots_client import ocr_image

    raw = ocr_image(sys.argv[1])
    print(json.dumps(structure(raw), indent=2, ensure_ascii=False))
