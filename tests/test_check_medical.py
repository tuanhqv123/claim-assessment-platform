import pytest
from src.stores.medical_mapping import MedicalMapping


@pytest.fixture
def mapping():
    return MedicalMapping()


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
