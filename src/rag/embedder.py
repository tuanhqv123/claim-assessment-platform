"""Local sentence embedder (fastembed / ONNX) — no API, no torch.

The LLM endpoint we use has no embeddings model, so retrieval runs on a small
local ONNX model. The model is loaded lazily on first use (first call downloads
~80 MB once, then it is cached by huggingface_hub).
"""
from __future__ import annotations

import os
from functools import lru_cache

import numpy as np

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384-dim, instruction-tuned for retrieval
DIM = 384


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding

    # EMBED_PROVIDERS lets the deploy pick the ONNX Runtime execution providers,
    # e.g. "CUDAExecutionProvider,CPUExecutionProvider" on a CUDA box (uses the
    # GPU when present, falls back to CPU otherwise). Unset -> plain CPU.
    providers_env = os.getenv("EMBED_PROVIDERS", "").strip()
    if providers_env:
        providers = [p.strip() for p in providers_env.split(",") if p.strip()]
        return TextEmbedding(MODEL_NAME, providers=providers)
    return TextEmbedding(MODEL_NAME)


def embed(texts: list[str]) -> np.ndarray:
    """Embed a batch of texts; returns an L2-normalized (n, DIM) float32 array."""
    if not texts:
        return np.zeros((0, DIM), dtype=np.float32)
    vecs = np.asarray(list(_model().embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def embed_one(text: str) -> np.ndarray:
    """Embed a single string; returns a 1-D normalized vector."""
    return embed([text])[0]
