"""Policy-document retrieval (RAG): chunk -> embed -> cosine search."""
from src.rag.store import PolicyRAG, get_rag

__all__ = ["PolicyRAG", "get_rag"]
