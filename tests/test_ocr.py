"""End-to-end tests for the Challenge-08 OCR extraction module.

These hit the LIVE dots.ocr and LLM endpoints. To avoid re-running the (slow)
two-stage pipeline per assertion, every sample is extracted once in a
session-scoped fixture, and the JSON results are written to output/ocr/.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ocr.dots_client import _extract_content
from src.ocr.pipeline import extract_document
from src.ocr.structurer import _parse_content
from src.ocr.validation import _parse_date, _to_number

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample_docs"
OUTPUT_DIR = ROOT / "output" / "ocr"

# sample stem -> expected document_type
EXPECTED_TYPE = {
    "receipt_1_bangkok": "receipt",
    "receipt_2_samitivej": "receipt",
    "receipt_3_mismatch": "receipt",
    "discharge_1_bangkok": "discharge_summary",
    "discharge_2_siriraj": "discharge_summary",
    "discharge_3_samitivej": "discharge_summary",
    "lab_1_bangkok": "lab_report",
    "lab_2_nhealth": "lab_report",
    "prescription_1_bangkok": "prescription",
    "prescription_2_siriraj": "prescription",
}

# Key fields that must be extracted non-null per type.
KEY_FIELDS = {
    "receipt": ["hospital_name", "patient_name", "date", "items", "grand_total"],
    "discharge_summary": [
        "hospital_name",
        "patient_name",
        "admission_date",
        "discharge_date",
        "diagnosis",
    ],
    "lab_report": ["lab_name", "patient_name", "date", "tests"],
    "prescription": ["doctor_name", "patient_name", "date", "medications"],
}


@pytest.fixture(scope="session")
def all_results() -> dict[str, dict]:
    """Extract every sample once and persist results to output/ocr/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    for stem in EXPECTED_TYPE:
        png = SAMPLE_DIR / f"{stem}.png"
        assert png.exists(), f"missing sample: {png}"
        result = extract_document(png)
        (OUTPUT_DIR / f"{stem}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False)
        )
        results[stem] = result
    return results


def _value(result: dict, field: str):
    f = result["fields"].get(field)
    return f.get("value") if isinstance(f, dict) else None


@pytest.mark.parametrize("stem", list(EXPECTED_TYPE))
def test_classification(all_results, stem):
    result = all_results[stem]
    assert result["document_type"] == EXPECTED_TYPE[stem], (
        f"{stem}: got {result['document_type']!r}, "
        f"expected {EXPECTED_TYPE[stem]!r}"
    )


def test_classification_accuracy(all_results):
    correct = sum(
        1
        for stem, r in all_results.items()
        if r["document_type"] == EXPECTED_TYPE[stem]
    )
    assert correct == len(EXPECTED_TYPE), (
        f"classification accuracy {correct}/{len(EXPECTED_TYPE)}"
    )


@pytest.mark.parametrize("stem", list(EXPECTED_TYPE))
def test_key_fields_non_null(all_results, stem):
    result = all_results[stem]
    dtype = result["document_type"]
    for field in KEY_FIELDS[dtype]:
        val = _value(result, field)
        assert val not in (None, "", [], {}), (
            f"{stem}: key field {field!r} is empty/null ({val!r})"
        )


@pytest.mark.parametrize("stem", list(EXPECTED_TYPE))
def test_field_confidences_present_and_valid(all_results, stem):
    result = all_results[stem]
    for name, f in result["fields"].items():
        assert isinstance(f, dict) and "value" in f and "confidence" in f, (
            f"{stem}: field {name!r} malformed: {f!r}"
        )
        assert 0.0 <= float(f["confidence"]) <= 1.0


def test_reasonable_values_receipt(all_results):
    r = all_results["receipt_1_bangkok"]
    items = _value(r, "items")
    assert isinstance(items, list) and len(items) >= 3
    grand_total = _value(r, "grand_total")
    # printed grand total is 7,128.00 THB
    gt = float(str(grand_total).replace(",", ""))
    assert 7000 <= gt <= 7300, f"grand_total off: {grand_total}"


def test_reasonable_values_lab(all_results):
    r = all_results["lab_1_bangkok"]
    tests = _value(r, "tests")
    assert isinstance(tests, list) and len(tests) >= 3
    names = " ".join(str(t.get("test_name", "")) for t in tests).lower()
    assert "hemoglobin" in names or "glucose" in names


def test_mismatch_produces_validation_error(all_results):
    r = all_results["receipt_3_mismatch"]
    errs = r["validation_errors"]
    assert any("mismatch" in e.lower() or "tolerance" in e.lower() for e in errs), (
        f"expected a total-mismatch validation error, got: {errs}"
    )


def test_clean_receipts_have_no_total_mismatch(all_results):
    for stem in ("receipt_1_bangkok", "receipt_2_samitivej"):
        errs = all_results[stem]["validation_errors"]
        assert not any("mismatch" in e.lower() for e in errs), (
            f"{stem} should not flag a mismatch: {errs}"
        )


def test_confidences_not_uniformly_one(all_results):
    """Across all extracted fields, confidence must vary (not all exactly 1.0)."""
    confidences: list[float] = []
    for r in all_results.values():
        confidences.append(float(r["confidence"]))
        for f in r["fields"].values():
            confidences.append(float(f["confidence"]))
    assert confidences, "no confidences collected"
    assert not all(c == 1.0 for c in confidences), (
        "confidence scores are uniformly 1.0"
    )
    # Sanity: there is genuine spread, not a single constant value.
    assert len(set(round(c, 2) for c in confidences)) > 1


def test_null_value_fields_have_low_confidence(all_results):
    """Anti-hallucination: any field whose value is None must have confidence
    capped at <= 0.3 (never trust a null emitted with high confidence)."""
    for stem, r in all_results.items():
        for name, f in r["fields"].items():
            if f.get("value") is None:
                assert float(f["confidence"]) <= 0.3, (
                    f"{stem}: null field {name!r} has confidence "
                    f"{f['confidence']} > 0.3"
                )


def test_extract_document_returns_layout_and_image_size(all_results):
    """extract_document must expose dots.ocr layout bboxes + the image size,
    without dropping any of the existing structured-output keys."""
    r = all_results["receipt_1_bangkok"]

    # Existing keys remain intact.
    for key in ("document_type", "confidence", "fields", "validation_errors"):
        assert key in r, f"missing existing key {key!r}"

    # image_size is [width, height] matching the actual PNG.
    image_size = r["image_size"]
    assert isinstance(image_size, list) and len(image_size) == 2
    width, height = image_size
    assert isinstance(width, int) and isinstance(height, int)
    assert width > 0 and height > 0

    from PIL import Image

    with Image.open(SAMPLE_DIR / "receipt_1_bangkok.png") as img:
        assert list(img.size) == image_size

    # layout is a non-empty list of {bbox, category[, text]} elements.
    layout = r["layout"]
    assert isinstance(layout, list) and layout, "layout is empty"
    categories = {
        "Caption", "Footnote", "Formula", "List-item", "Page-footer",
        "Page-header", "Picture", "Section-header", "Table", "Text", "Title",
    }
    for el in layout:
        assert isinstance(el, dict)
        bbox = el["bbox"]
        assert isinstance(bbox, list) and len(bbox) == 4
        assert all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in bbox)
        x1, y1, x2, y2 = bbox
        # Each coordinate lies within the image bounds.
        for x in (x1, x2):
            assert 0 <= x <= width, f"x {x} out of [0, {width}]"
        for y in (y1, y2):
            assert 0 <= y <= height, f"y {y} out of [0, {height}]"
        assert el["category"] in categories, f"bad category {el['category']!r}"
        if "text" in el:
            assert isinstance(el["text"], str)


# --- offline unit tests (no network) -------------------------------------


def test_to_number_parses_accounting_negative():
    assert _to_number("(500.00)") == -500.0


@pytest.mark.parametrize(
    "raw,expected",
    [
        (7128, 7128.0),
        (7128.0, 7128.0),
        ("7,128.00", 7128.0),
        ("THB 7,128.00", 7128.0),
        ("  $1,234.50 ", 1234.5),
        ("(500.00)", -500.0),
        ("-42", -42.0),
        ("+42", 42.0),
        ("1.234.567", None),  # ambiguous: do not mangle
        ("", None),
        ("N/A", None),
        ("abc", None),
        (None, None),
        (True, None),
    ],
)
def test_to_number_cases(raw, expected):
    assert _to_number(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "15 March 2024",
        "March 15, 2024",
        "15 Mar 2024",
        "Mar 15, 2024",
        "15/03/2024",
        "2024-03-15",
        "15-Mar-2024",
    ],
)
def test_parse_date_valid(raw):
    assert _parse_date(raw) is True


@pytest.mark.parametrize("raw", ["not a date", "", "32/13/2024", "Marchish 2024"])
def test_parse_date_invalid(raw):
    assert _parse_date(raw) is False


def test_structure_bad_input_degrades_gracefully():
    """_parse_content must never raise on None/empty/garbage/fenced input."""
    expected_err = ["LLM output not parseable as JSON"]

    for bad in (None, "", "   ", "not json at all", "{broken", "[1, 2, 3]"):
        out = _parse_content(bad)
        assert out["document_type"] in ("receipt",)
        assert out["confidence"] == 0.0
        assert out["fields"] == {}
        assert out["validation_errors"] == expected_err


def test_structure_strips_markdown_fences():
    fenced = '```json\n{"document_type": "receipt", "confidence": 0.9, ' \
             '"fields": {}, "validation_errors": []}\n```'
    out = _parse_content(fenced)
    assert out["document_type"] == "receipt"
    assert out["confidence"] == 0.9
    assert out["validation_errors"] == []


def test_structure_caps_null_field_confidence():
    payload = json.dumps(
        {
            "document_type": "receipt",
            "confidence": 0.8,
            "fields": {
                "patient_name": {"value": None, "confidence": 0.99},
                "grand_total": {"value": 7128.0, "confidence": 0.95},
            },
            "validation_errors": [],
        }
    )
    out = _parse_content(payload)
    assert out["fields"]["patient_name"]["confidence"] <= 0.3
    assert out["fields"]["grand_total"]["confidence"] == 0.95


def test_extract_content_guards_bad_responses():
    import pytest as _pytest

    for bad in (
        {"error": {"message": "boom"}},
        {"choices": []},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": {"content": "   "}}]},
        {},
    ):
        with _pytest.raises(RuntimeError, match="dots.ocr returned no content"):
            _extract_content(bad)

    ok = {"choices": [{"message": {"content": "  hello  "}}]}
    assert _extract_content(ok) == "hello"
