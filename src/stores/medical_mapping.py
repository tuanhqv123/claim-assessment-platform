"""ICD-10 diagnosis → valid-procedure reference.

The data lives in the database (``medical_codes`` table), not in a file. The
mapping is loaded lazily on first use and cached. Tests inject a synthetic
mapping so they need no database. Nothing is hardcoded in source.
"""
from __future__ import annotations

from src import db


class MedicalMapping:
    def __init__(self, mapping: dict[str, dict] | None = None):
        # ``mapping`` (diagnosis_code -> {description, valid_procedures,
        # procedure_descriptions}) injects an in-memory set (used by tests).
        # When omitted, it is loaded lazily from the DB on first ``check``.
        self._mapping: dict[str, dict] | None = mapping

    @staticmethod
    def _load_from_db() -> dict[str, dict]:
        try:
            rows = db.select("medical_codes")
        except Exception:  # noqa: BLE001 — table may not exist yet; degrade safely
            return {}
        return {
            r["diagnosis_code"]: {
                "description": r.get("description") or "",
                "valid_procedures": r.get("valid_procedures") or [],
                "procedure_descriptions": r.get("procedure_descriptions") or {},
            }
            for r in rows
        }

    def _codes(self) -> dict[str, dict]:
        if self._mapping is None:
            self._mapping = self._load_from_db()
        return self._mapping

    def check(self, diagnosis_code: str, procedure_codes: list[str]) -> dict:
        entry = self._codes().get(diagnosis_code)
        if entry is None:
            return {
                "diagnosis_code": diagnosis_code,
                "diagnosis_description": "Unknown diagnosis code",
                "procedure_codes": procedure_codes,
                "is_medically_necessary": False,
                "reasoning": f"Diagnosis code {diagnosis_code} not found in mapping",
                "warnings": [f"Unknown ICD-10 code: {diagnosis_code}"],
            }

        valid = set(entry["valid_procedures"])
        submitted = set(procedure_codes)
        matched = submitted & valid
        unmatched = submitted - valid

        is_necessary = len(matched) > 0 and len(unmatched) == 0
        warnings = [
            f"Procedure {code} is not clinically associated with {diagnosis_code}"
            for code in unmatched
        ]

        if matched:
            matched_desc = ", ".join(
                entry["procedure_descriptions"].get(c, c) for c in matched
            )
            reasoning = f"Procedures [{matched_desc}] are valid for {entry['description']}"
        else:
            reasoning = f"No submitted procedures match valid procedures for {entry['description']}"

        return {
            "diagnosis_code": diagnosis_code,
            "diagnosis_description": entry["description"],
            "procedure_codes": procedure_codes,
            "is_medically_necessary": is_necessary,
            "reasoning": reasoning,
            "warnings": warnings,
        }
