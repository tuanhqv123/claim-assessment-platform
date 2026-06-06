from __future__ import annotations

import json
from pathlib import Path


class MedicalMapping:
    def __init__(self, data_path: str = "data/mappings/icd10_procedures.json"):
        path = Path(data_path)
        self._mapping: dict[str, dict] = json.loads(path.read_text()) if path.exists() else {}

    def check(self, diagnosis_code: str, procedure_codes: list[str]) -> dict:
        entry = self._mapping.get(diagnosis_code)
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
