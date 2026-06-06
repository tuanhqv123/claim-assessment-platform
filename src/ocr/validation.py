"""Validation rules over the structured Challenge-08 output.

Checks:
- Date fields parse as valid dates (DD/MM/YYYY and a few common variants).
- Amount fields are positive numbers.
- For receipts, the sum of line-item totals matches grand_total within 5%.

Returns a list of human-readable error strings; the pipeline merges these into
``validation_errors``.
"""
from __future__ import annotations

import re
from datetime import datetime

_DATE_FIELDS = {
    "date",
    "admission_date",
    "discharge_date",
    "collection_date",
}

_DATE_FORMATS = (
    # Numeric formats.
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%d/%m/%y",
    "%Y/%m/%d",
    "%m-%d-%Y",
    # Spelled-out month formats.
    "%d %B %Y",     # 15 March 2024
    "%B %d, %Y",    # March 15, 2024
    "%B %d %Y",     # March 15 2024
    "%d %b %Y",     # 15 Mar 2024
    "%b %d, %Y",    # Mar 15, 2024
    "%b %d %Y",     # Mar 15 2024
    "%d-%b-%Y",     # 15-Mar-2024
    "%d-%B-%Y",     # 15-March-2024
)


def _field_value(structured: dict, name: str):
    f = structured.get("fields", {}).get(name)
    if isinstance(f, dict):
        return f.get("value")
    return f


def _parse_date(value) -> bool:
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not s:
        return False
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(s, fmt)
            return True
        except ValueError:
            continue
    return False


def _to_number(value):
    """Coerce a messy numeric string to float, else None.

    Handles: plain ints/floats; currency symbols and spaces ('THB 7,128.00');
    thousands commas ('7,128.00' -> 7128.0); parenthesized accounting negatives
    ('(500.00)' -> -500.0). Returns None when the string is genuinely
    unparseable, and does NOT mangle ambiguous values like '1.234.567'.
    """
    if isinstance(value, bool):
        # bool is an int subclass; treat as non-numeric to avoid True -> 1.0.
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    # Parenthesized accounting negative, e.g. "(500.00)".
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()

    # Leading sign.
    if s.startswith("-"):
        negative = not negative
        s = s[1:].strip()
    elif s.startswith("+"):
        s = s[1:].strip()

    # Strip everything that isn't a digit, comma, or dot (currency symbols,
    # spaces, currency codes like "THB", etc.).
    s = re.sub(r"[^\d.,]", "", s)
    if not s or not any(ch.isdigit() for ch in s):
        return None

    # Thousands commas only: drop them ('7,128.00' -> '7128.00').
    s = s.replace(",", "")

    # Reject ambiguous multi-dot strings like '1.234.567' rather than mangle.
    if s.count(".") > 1:
        return None

    try:
        num = float(s)
    except ValueError:
        return None
    return -num if negative else num


def validate(structured: dict) -> list[str]:
    errors: list[str] = []
    fields = structured.get("fields", {}) or {}
    dtype = structured.get("document_type")

    # --- date validity ---
    for name in _DATE_FIELDS:
        if name in fields:
            val = _field_value(structured, name)
            if val is None:
                continue
            if not _parse_date(val):
                errors.append(f"Invalid date in field '{name}': {val!r}")

    # --- positive amounts ---
    for name in ("grand_total",):
        if name in fields:
            val = _field_value(structured, name)
            if val is None:
                continue
            num = _to_number(val)
            if num is None:
                errors.append(f"Non-numeric amount in field '{name}': {val!r}")
            elif num <= 0:
                errors.append(f"Amount in field '{name}' must be positive: {num}")

    # --- receipt: line items sum vs grand_total ---
    if dtype == "receipt":
        errors.extend(_validate_receipt_totals(structured))

    return errors


def _validate_receipt_totals(structured: dict) -> list[str]:
    errors: list[str] = []
    items = _field_value(structured, "items")
    grand_total = _to_number(_field_value(structured, "grand_total"))
    if not isinstance(items, list) or not items or grand_total is None:
        return errors

    item_sum = 0.0
    counted = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        total = _to_number(it.get("total"))
        if total is None:
            # Fall back to quantity * unit_price if available.
            qty = _to_number(it.get("quantity"))
            up = _to_number(it.get("unit_price"))
            if qty is not None and up is not None:
                total = qty * up
        if total is not None:
            if total < 0:
                errors.append(
                    f"Negative line-item total for "
                    f"{it.get('description', '<item>')!r}: {total}"
                )
            item_sum += total
            counted += 1

    if counted == 0 or grand_total == 0:
        return errors

    diff_pct = abs(item_sum - grand_total) / grand_total * 100.0
    if diff_pct > 5.0:
        errors.append(
            "Receipt total mismatch: line items sum to "
            f"{item_sum:,.2f} but grand_total is {grand_total:,.2f} "
            f"({diff_pct:.1f}% difference, exceeds 5% tolerance)."
        )
    return errors
