"""Layout-aware text extraction for whole documents (policies).

Runs the dots.ocr layout model and keeps the document structure (headings,
tables, paragraph boundaries) instead of flattening it — so the RAG corpus
preserves the original document's context. Multi-page PDFs are rasterized one
page at a time (via poppler's ``pdftoppm``) and OCR'd page by page.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from src.ocr.dots_client import layout_to_structured_text, ocr_layout

_PDF_DPI = 150


def _pdf_to_pngs(pdf_path: Path, out_dir: Path, dpi: int = _PDF_DPI) -> list[Path]:
    """Rasterize each PDF page to a PNG using poppler's pdftoppm."""
    if not shutil.which("pdftoppm"):
        raise RuntimeError(
            "pdftoppm (poppler) is required to OCR PDF policy documents."
        )
    prefix = out_dir / "page"
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        check=True,
        capture_output=True,
    )
    return sorted(out_dir.glob("page*.png"))


def extract_document_text(path: str | Path) -> str:
    """Return layout-aware, structure-preserving text for an image or PDF file."""
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        with tempfile.TemporaryDirectory() as tmp:
            pages = _pdf_to_pngs(p, Path(tmp))
            sections: list[str] = []
            for i, page in enumerate(pages, start=1):
                body = layout_to_structured_text(ocr_layout(page))
                sections.append(f"## Page {i}\n\n{body}" if body else f"## Page {i}")
            return "\n\n".join(sections)
    # Single image.
    return layout_to_structured_text(ocr_layout(p))
