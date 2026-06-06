"""Run the extraction pipeline over every sample doc and write results to
``output/ocr/<name>.json``.

    .venv/bin/python -m src.ocr.run_all
"""
from __future__ import annotations

import json
from pathlib import Path

from src.ocr.pipeline import extract_document

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "data" / "sample_docs"
OUTPUT_DIR = ROOT / "output" / "ocr"


def run_all() -> dict[str, dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    for png in sorted(SAMPLE_DIR.glob("*.png")):
        name = png.stem
        result = extract_document(png)
        out_path = OUTPUT_DIR / f"{name}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        results[name] = result
        print(
            f"{name}: {result['document_type']} "
            f"(conf {result['confidence']:.2f}, "
            f"{len(result['validation_errors'])} validation error(s))"
        )
    return results


if __name__ == "__main__":
    run_all()
