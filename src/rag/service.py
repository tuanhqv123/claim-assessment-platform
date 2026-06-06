"""High-level glue between policy records and the RAG index.

A policy's retrievable text is the admin-uploaded document when one exists,
otherwise a document rendered from the policy's structured terms. Callers index
and query through here so that resolution rule lives in one place.
"""
from __future__ import annotations

from src.rag.policy_document import render_policy_document
from src.rag.store import get_rag


def _uploaded_text(policy_data: dict) -> str:
    uploaded = (policy_data or {}).get("terms_document")
    return uploaded if isinstance(uploaded, str) and uploaded.strip() else ""


def document_text_for(policy_data: dict) -> str:
    """Text to DISPLAY for a policy: the uploaded document if present, else a
    document rendered from the structured terms."""
    return _uploaded_text(policy_data) or render_policy_document(policy_data or {})


def index_text_for(policy_data: dict) -> str:
    """Text to INDEX for retrieval: always the structured-rendered document
    (guarantees the numbers/limits/exclusions are searchable) PLUS any uploaded
    document text (adds the fine print). This way uploading a short addendum
    never drops the core terms from the RAG corpus."""
    rendered = render_policy_document(policy_data or {})
    uploaded = _uploaded_text(policy_data)
    return f"{rendered}\n\n{uploaded}" if uploaded else rendered


def ensure_indexed(
    policy_id: str, policy_data: dict, tenant_id: str | None = None
) -> int:
    """Index (or refresh) a single policy's document. Returns chunk count."""
    if not policy_id:
        return 0
    return get_rag().index_policy(
        policy_id, index_text_for(policy_data), tenant_id=tenant_id
    )


def index_all(policies: list[dict]) -> int:
    """Index a batch of policy rows (each must carry ``data`` + a policy id).

    Returns the number of policies indexed.
    """
    count = 0
    for row in policies:
        data = row.get("data") or {}
        pid = data.get("policy_id") or row.get("policy_number")
        if pid:
            ensure_indexed(pid, data, tenant_id=row.get("tenant_id"))
            count += 1
    return count


def retrieve(policy_id: str, query: str, k: int = 4) -> list[dict]:
    return get_rag().retrieve(policy_id, query, k=k)
