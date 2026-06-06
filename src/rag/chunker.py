"""Split a policy document into clause-level chunks for retrieval.

Real uploaded policy documents arrive as one long text blob (from OCR or a PDF
text layer). We split into paragraph-sized chunks and carry the nearest
preceding heading along, so a retrieved clause can be cited as
"Section 4.2 — Exclusions: ...".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# A heading is a short line that is not a full sentence: an ALL-CAPS title, a
# numbered clause ("4.2 Exclusions"), or a markdown header ("## Exclusions").
_HEADING_RE = re.compile(
    r"^\s*(#{1,6}\s+.+"  # markdown header
    r"|\d+(\.\d+)*\.?\s+[A-Z].{0,60}"  # numbered clause heading
    r"|[A-Z0-9][A-Z0-9 &/()\-]{2,60})\s*$"  # ALL-CAPS title
)
_MAX_WORDS = 130


@dataclass
class Chunk:
    section: str  # nearest heading, e.g. "4. EXCLUSIONS"
    text: str

    def to_dict(self) -> dict:
        return {"section": self.section, "text": self.text}

    def citation_text(self) -> str:
        return f"{self.section}: {self.text}" if self.section else self.text


def _looks_like_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line.split()) > 10:
        return False
    if line.endswith((".", ":", ";", ",")) and not line.startswith("#"):
        # A trailing period usually means a sentence, not a heading — but allow
        # a numbered "4.2 Exclusions:" style which ends with a colon.
        if not line.endswith(":"):
            return False
    return bool(_HEADING_RE.match(line))


def _clean_heading(line: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", line).strip().rstrip(":").strip()


def _split_words(text: str, limit: int) -> list[str]:
    """Break an over-long paragraph on sentence boundaries into <=limit-word parts."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    parts: list[str] = []
    cur: list[str] = []
    for sent in sentences:
        cur.append(sent)
        if len(" ".join(cur).split()) >= limit:
            parts.append(" ".join(cur).strip())
            cur = []
    if cur:
        parts.append(" ".join(cur).strip())
    return [p for p in parts if p]


def chunk_document(text: str) -> list[Chunk]:
    """Chunk a raw policy document into clause-sized pieces with section context."""
    # Normalize newlines; split into paragraphs on blank lines.
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip())
    chunks: list[Chunk] = []
    section = ""
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        # A lone heading line updates the current section context.
        if len(lines) == 1 and _looks_like_heading(lines[0]):
            section = _clean_heading(lines[0])
            continue
        # If the block leads with a heading line followed by body, capture it.
        if _looks_like_heading(lines[0]) and len(lines) > 1:
            section = _clean_heading(lines[0])
            lines = lines[1:]
        body = " ".join(ln.strip() for ln in lines).strip()
        if not body:
            continue
        for part in _split_words(body, _MAX_WORDS):
            chunks.append(Chunk(section=section, text=part))
    return chunks
