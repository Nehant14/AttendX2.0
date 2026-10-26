"""Embedding utilities: L2 normalisation and cosine similarity helpers."""
from __future__ import annotations

import numpy as np


def l2_normalize(v: np.ndarray) -> np.ndarray:
    """L2-normalise a vector or batch of vectors (last axis)."""
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(norm == 0, 1.0, norm)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalised vectors."""
    return float(np.dot(a, b))


def cosine_matrix(F: np.ndarray, E: np.ndarray) -> np.ndarray:
    """
    Cosine similarity matrix.

    Args:
        F: (N, 512) L2-normalised face embeddings.
        E: (M, 512) L2-normalised enrollment embeddings.

    Returns:
        (N, M) similarity matrix.
    """
    return (F @ E.T).astype(np.float32)
