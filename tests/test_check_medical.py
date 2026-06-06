import pytest
from src.stores.medical_mapping import MedicalMapping


# Synthetic mapping injected into the store — tests do no DB/network I/O.
_FIXTURE = {
    "J06.9": {
        "description": "Acute upper respiratory infection, unspecified",
        "valid_procedures": ["99213", "99214", "87880", "71046"],
        "procedure_descriptions": {"99213": "Office/outpatient visit"},
    },
}


@pytest.fixture
def mapping():
    return MedicalMapping(mapping=_FIXTURE)


def test_valid_diagnosis_procedure_pair(mapping):
    result = mapping.check("J06.9", ["99213"])
    assert result["is_medically_necessary"] is True
    assert len(result["warnings"]) == 0


def test_invalid_procedure_for_diagnosis(mapping):
    result = mapping.check("J06.9", ["44950"])
    assert result["is_medically_necessary"] is False
    assert len(result["warnings"]) > 0


def test_unknown_diagnosis_code(mapping):
    result = mapping.check("Z99.99", ["99213"])
    assert result["is_medically_necessary"] is False


def test_mixed_valid_and_invalid(mapping):
    result = mapping.check("J06.9", ["99213", "44950"])
    assert result["is_medically_necessary"] is False
    assert len(result["warnings"]) == 1
