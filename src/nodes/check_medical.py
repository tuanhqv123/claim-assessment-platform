from __future__ import annotations

from src.stores.medical_mapping import MedicalMapping


def check_medical_node(state: dict) -> dict:
    claim = state["claim"]
    mapping = MedicalMapping()
    result = mapping.check(claim["diagnosis_code"], claim["procedure_codes"])

    log_entry = {
        "tool_name": "checkMedicalNecessity",
        "inputs": {
            "diagnosis": claim["diagnosis_code"],
            "procedures": claim["procedure_codes"],
        },
        "outputs": result,
    }

    return {
        "medical_necessity": result,
        "tool_call_log": [log_entry],
    }
