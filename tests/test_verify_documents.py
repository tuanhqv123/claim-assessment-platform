import pytest
from src.stores.document_store import DocumentStore


@pytest.fixture
def store():
    return DocumentStore()


def test_verify_existing_complete_doc(store):
    result = store.verify("DOC-001")
    assert result["status"] == "COMPLETE"
    assert result["document_type"] == "medical_receipt"


def test_verify_missing_doc(store):
    result = store.verify("DOC-999")
    assert result["status"] == "MISSING"
    assert len(result["issues"]) > 0
