"""Stage A: raw OCR via the dots.ocr vLLM endpoint (OpenAI-compatible vision).

dots.ocr is a vision model served behind an OpenAI-compatible /chat/completions
route. We base64-encode the PNG and send it as an image_url. No API key is
required (we send a placeholder).
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import httpx

from src.config import require_env

# OCR endpoint + model come from the environment (no hardcoded server IP/model).

# dots.ocr is a layout model: given this prompt it returns the document layout as
# a JSON list of {bbox, category, text} elements (bbox in image pixel
# coordinates, sorted in human reading order). This is its native, most reliable
# output format. Stage B then runs on the texts joined in reading order.
LAYOUT_PROMPT = (
    "Please output the layout information from the PDF image, including each "
    "layout element's bbox, its category, and the corresponding text content "
    "within the bbox.\n\n"
    "1. Bbox format: [x1, y1, x2, y2]\n\n"
    "2. Layout Categories: The possible categories are ['Caption', 'Footnote', "
    "'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', "
    "'Section-header', 'Table', 'Text', 'Title'].\n\n"
    "3. Text Extraction & Formatting Rules:\n"
    "    - Picture: For the 'Picture' category, the text field should be "
    "omitted.\n"
    "    - Formula: Format its text as LaTeX.\n"
    "    - Table: Format its text as HTML.\n"
    "    - All Others (Text, Title, etc.): Format their text as Markdown.\n\n"
    "4. Constraints:\n"
    "    - The output text must be the original text from the image, with no "
    "translation.\n"
    "    - All layout elements must be sorted according to human reading "
    "order.\n\n"
    "5. Final Output: The entire output must be a single JSON object."
)

# Categories whose text should NOT be folded into the Stage B input.
_NON_TEXT_CATEGORIES = {"Picture"}
# Layout categories that represent document headings.
_HEADING_CATEGORIES = {"Title", "Section-header"}


# Supported image extensions -> data-URL mime type.
_IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def _image_data_url(image_path: str | Path) -> str:
    """base64 data URL with the mime matching the file extension (default PNG)."""
    p = Path(image_path)
    mime = _IMAGE_MIME.get(p.suffix.lower(), "image/png")
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _post_chat(prompt: str, data_url: str, timeout: float) -> str:
    ocr_base_url = require_env("OCR_BASE_URL")
    payload = {
        "model": require_env("OCR_MODEL"),
        "messages": [
            {
                "role": "user",
                # Image MUST precede the text prompt: dots.ocr only enters its
                # layout-parsing mode with image-first ordering; text-first
                # degrades it to plain markdown OCR.
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.1,
        "repetition_penalty": 1.1,
        "max_tokens": 8192,
    }
    url = ocr_base_url.rstrip("/") + "/chat/completions"
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            url,
            json=payload,
            headers={"Authorization": "Bearer none", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    return _extract_content(data)


def _parse_layout(content: str) -> list[dict]:
    """Parse dots.ocr layout output into a list of {bbox, category, text}.

    Tolerates markdown ```json fences and a top-level {"...": [...]} wrapper
    around the list. Skips malformed elements rather than raising.
    """
    text = content.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```).
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise RuntimeError(
            f"dots.ocr layout not parseable as JSON: {content!r}"
        ) from exc

    # Tolerate a top-level {"...": [...]} wrapper around the list.
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        if len(lists) == 1:
            data = lists[0]
        else:
            raise RuntimeError(
                f"dots.ocr layout: expected a JSON list, got dict {data!r}"
            )
    if not isinstance(data, list):
        raise RuntimeError(
            f"dots.ocr layout: expected a JSON list, got {type(data).__name__}"
        )

    elements: list[dict] = []
    for el in data:
        if not isinstance(el, dict):
            continue
        bbox = el.get("bbox")
        category = el.get("category")
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or not all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in bbox)
            or not isinstance(category, str)
        ):
            continue
        out: dict = {"bbox": [int(c) for c in bbox], "category": category}
        txt = el.get("text")
        # text may legitimately be absent (e.g. Picture); keep it only if present.
        if isinstance(txt, str):
            out["text"] = txt
        elements.append(out)
    return elements


def ocr_layout(image_path: str | Path, timeout: float = 180.0, retries: int = 3) -> list[dict]:
    """Return the document layout from dots.ocr as a list of layout elements.

    Each element is {"bbox": [x1, y1, x2, y2], "category": str, "text": str},
    with "text" absent for non-text categories (e.g. Picture). bbox coordinates
    are in the image's pixel space; elements are in human reading order.
    """
    data_url = _image_data_url(image_path)
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            content = _post_chat(LAYOUT_PROMPT, data_url, timeout)
            return _parse_layout(content)
        except (RuntimeError, Exception) as exc:
            last_exc = exc
            if attempt == retries:
                break
    raise RuntimeError(f"dots.ocr failed after {retries} attempts: {last_exc}") from last_exc


def layout_to_text(elements: list[dict]) -> str:
    """Join layout element texts in reading order into a single OCR text blob."""
    parts: list[str] = []
    for el in elements:
        if el.get("category") in _NON_TEXT_CATEGORIES:
            continue
        txt = el.get("text")
        if isinstance(txt, str) and txt.strip():
            parts.append(txt.strip())
    return "\n".join(parts)


def layout_to_structured_text(elements: list[dict]) -> str:
    """Reconstruct layout-aware text that PRESERVES document structure.

    Unlike ``layout_to_text`` (which flattens everything into one blob), this
    keeps the dots.ocr categories: headings (Title / Section-header) are emitted
    as markdown ``## headings`` and tables keep their HTML, with every layout
    block separated by a blank line. This lets downstream chunking split on real
    section boundaries — so a retrieved clause carries its true heading/context
    instead of bleeding across sections.
    """
    blocks: list[str] = []
    for el in elements:
        cat = el.get("category")
        if cat in _NON_TEXT_CATEGORIES:
            continue
        txt = el.get("text")
        if not isinstance(txt, str) or not txt.strip():
            continue
        txt = txt.strip()
        if cat in _HEADING_CATEGORIES:
            # Strip any leading markdown hashes the model may already have added.
            blocks.append(f"## {txt.lstrip('# ').strip()}")
        else:
            blocks.append(txt)  # Text / List-item / Table(HTML) kept verbatim
    return "\n\n".join(blocks)


def ocr_image(image_path: str | Path, timeout: float = 180.0) -> str:
    """Return the raw OCR text for a single PNG image.

    Implemented on top of ocr_layout: the layout elements' texts are joined in
    reading order to produce the plain-text transcription Stage B consumes.
    """
    elements = ocr_layout(image_path, timeout=timeout)
    return layout_to_text(elements)


def _extract_content(data) -> str:
    """Pull the text content out of an OpenAI-style response, guarding against
    error bodies, empty choices, and null content returned with a 200."""
    if not isinstance(data, dict):
        raise RuntimeError(f"dots.ocr returned no content: unexpected body {data!r}")

    # A 200 can still carry an error payload.
    if data.get("error"):
        raise RuntimeError(f"dots.ocr returned no content: error {data['error']!r}")

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(f"dots.ocr returned no content: empty choices in {data!r}")

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"dots.ocr returned no content: null/empty content in {data!r}")

    return content.strip()


if __name__ == "__main__":
    import sys

    print(ocr_image(sys.argv[1]))
