"""Public entry point for Challenge-08 document extraction.

extract_document(image_path) runs:
    Stage A (dots.ocr raw OCR)  ->  Stage B (LLM structuring)  ->  validation
and returns the structured schema dict with validation_errors merged in.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.ocr.dots_client import layout_to_text, ocr_layout
from src.ocr.structurer import structure
from src.ocr.validation import validate


def extract_document_stream(image_path: str | Path):
    """Run the pipeline stage-by-stage, yielding progress events as each stage
    completes (so a UI can show what the OCR model / LLM is doing live), then a
    final ``{"event": "done", "result": <full schema>}``.
    """
    # Stage A: dots.ocr native layout (bbox + category + text per element).
    yield {"event": "step", "step": "ocr", "label": "Reading document", "status": "running"}
    layout = ocr_layout(image_path)
    categories = sorted({e.get("category") for e in layout if e.get("category")})
    yield {
        "event": "step", "step": "ocr", "status": "done",
        "data": {"regions": len(layout), "categories": categories},
    }

    # Stage B: structure the reading-order text into business fields (LLM).
    yield {"event": "step", "step": "structure", "label": "Extracting details", "status": "running"}
    raw_text = layout_to_text(layout)
    structured = structure(raw_text)
    yield {
        "event": "step", "step": "structure", "status": "done",
        "data": {
            "document_type": structured.get("document_type"),
            "fields": len(structured.get("fields", {}) or {}),
            "confidence": structured.get("confidence"),
        },
    }

    # Stage C: deterministic validation (dates, amounts, totals).
    yield {"event": "step", "step": "validate", "label": "Validating dates, amounts & totals", "status": "running"}
    rule_errors = validate(structured)
    existing = structured.get("validation_errors") or []
    merged: list[str] = []
    for e in list(existing) + rule_errors:
        if e and e not in merged:
            merged.append(e)
    structured["validation_errors"] = merged
    with Image.open(image_path) as img:
        width, height = img.size
    structured["layout"] = layout
    structured["image_size"] = [width, height]
    yield {"event": "step", "step": "validate", "status": "done", "data": {"issues": len(merged)}}

    yield {"event": "done", "result": structured}


def extract_document(image_path: str | Path) -> dict:
    """Non-streaming entry point: drains the stream and returns the final result."""
    result: dict = {}
    for ev in extract_document_stream(image_path):
        if ev.get("event") == "done":
            result = ev["result"]
    return result


if __name__ == "__main__":
    import json
    import sys

    print(json.dumps(extract_document(sys.argv[1]), indent=2, ensure_ascii=False))
