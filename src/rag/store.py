"""Policy-document vector store backed by Supabase pgvector.

Embeddings (fastembed bge-small, 384-dim) are stored in the ``policy_chunks``
table and searched with pgvector cosine distance via the ``match_policy_chunks``
RPC. Embedding still happens locally (the LLM endpoint has no embeddings model),
but the vectors themselves live in Supabase — so there is no local cache to keep
in sync and any backend instance shares the same index.

Re-indexing is idempotent: a policy is only re-embedded when its document text
changes (tracked by a content hash stored on every chunk row).
"""
from __future__ import annotations

import hashlib

import numpy as np

from src import db
from src.rag.chunker import chunk_document
from src.rag.embedder import embed, embed_one


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vec_literal(vec) -> str:
    """Format a vector as the pgvector text literal '[0.1,0.2,...]'."""
    arr = np.asarray(vec, dtype=np.float32)
    return "[" + ",".join(f"{x:.7f}" for x in arr.tolist()) + "]"


class PolicyRAG:
    """Per-policy semantic index over policy-document text, in Supabase pgvector."""

    # ------------------------------------------------------------------ #
    # Indexing.
    # ------------------------------------------------------------------ #
    def index_policy(
        self,
        policy_id: str,
        document_text: str,
        tenant_id: str | None = None,
    ) -> int:
        """(Re)index a policy's document text. Returns the chunk count.

        Reuses the stored vectors when the document text is unchanged.
        """
        document_text = (document_text or "").strip()
        if not policy_id:
            return 0
        if not document_text:
            db.delete("policy_chunks", {"policy_id": f"eq.{policy_id}"})
            return 0

        doc_hash = _hash(document_text)
        existing = db.select(
            "policy_chunks",
            columns="id,content_hash",
            filters={"policy_id": f"eq.{policy_id}"},
        )
        if existing and existing[0].get("content_hash") == doc_hash:
            return len(existing)

        chunks = chunk_document(document_text)
        # Replace any previous index for this policy.
        db.delete("policy_chunks", {"policy_id": f"eq.{policy_id}"})
        if not chunks:
            return 0
        matrix = embed([c.text for c in chunks])
        rows = [
            {
                "tenant_id": tenant_id,
                "policy_id": policy_id,
                "content_hash": doc_hash,
                "section": c.section or None,
                "chunk_text": c.text,
                "embedding": _vec_literal(vec),
            }
            for c, vec in zip(chunks, matrix)
        ]
        db.insert("policy_chunks", rows)
        return len(chunks)

    def has(self, policy_id: str) -> bool:
        rows = db.select(
            "policy_chunks",
            columns="id",
            filters={"policy_id": f"eq.{policy_id}"},
            limit=1,
        )
        return bool(rows)

    # ------------------------------------------------------------------ #
    # Retrieval.
    # ------------------------------------------------------------------ #
    def retrieve(self, policy_id: str, query: str, k: int = 4) -> list[dict]:
        """Return the top-k clauses for ``query`` within ``policy_id``.

        Each result: {section, text, score}. Empty list if the policy has no
        indexed document.
        """
        if not policy_id or not query:
            return []
        q = embed_one(query)
        results = db.rpc(
            "match_policy_chunks",
            {
                "query_embedding": _vec_literal(q),
                "p_policy_id": policy_id,
                "match_count": max(1, k),
            },
        )
        out: list[dict] = []
        for r in results or []:
            out.append(
                {
                    "section": r.get("section"),
                    "text": r.get("chunk_text"),
                    "score": round(float(r.get("score") or 0.0), 4),
                }
            )
        return out


# Process-wide singleton (stateless apart from the embedder cache).
_RAG: PolicyRAG | None = None


def get_rag() -> PolicyRAG:
    global _RAG
    if _RAG is None:
        _RAG = PolicyRAG()
    return _RAG
