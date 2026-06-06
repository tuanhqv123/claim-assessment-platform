import pytest
from src.stores.policy_store import PolicyStore


@pytest.fixture
def store():
    return PolicyStore(data_dir="data/policies")


def test_lookup_existing_policy(store):
    policy = store.lookup("POL-001")
    assert policy is not None
    assert policy["policy_id"] == "POL-001"
    assert policy["status"] == "ACTIVE"
    assert len(policy["benefits"]) >= 1


def test_lookup_nonexistent_policy(store):
    policy = store.lookup("POL-999")
    assert policy is None


def test_policy_has_required_fields(store):
    policy = store.lookup("POL-001")
    required = ["policy_id", "status", "effective_date", "expiry_date",
                "benefits", "copay", "exclusions", "waiting_periods"]
    for field in required:
        assert field in policy, f"Missing field: {field}"


def test_get_required_documents_outpatient(store):
    docs = store.get_required_documents("OUTPATIENT")
    assert "medical_receipt" in docs


def test_get_required_documents_inpatient(store):
    docs = store.get_required_documents("INPATIENT")
    assert "medical_receipt" in docs
    assert "discharge_summary" in docs
    assert "itemized_bill" in docs
