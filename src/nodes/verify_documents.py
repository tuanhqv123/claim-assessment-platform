from __future__ import annotations

from src.stores.document_store import DocumentStore
from src.stores.policy_store import PolicyStore


def verify_documents_node(state: dict) -> dict:
    claim = state["claim"]
    required = state.get("required_documents", PolicyStore.get_required_documents(claim["claim_type"]))
    store = DocumentStore()

    reviews = []
    log_entries = []

    for doc_id in claim["submitted_document_ids"]:
        result = store.verify(doc_id)
        reviews.append(result)
        log_entries.append({
            "tool_name": "verifyDocument",
            "inputs": {"document_id": doc_id},
            "outputs": result,
        })

    submitted_types = {
        r["document_type"] for r in reviews if r["status"] == "COMPLETE"
    }
    missing = [doc_type for doc_type in required if doc_type not in submitted_types]

    return {
        "document_reviews": reviews,
        "missing_documents": missing,
        "tool_call_log": log_entries,
    }
