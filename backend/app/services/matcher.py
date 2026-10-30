"""Match detected faces to students: cosine similarity + one-to-one (Hungarian) assignment."""
from typing import Optional

import numpy as np
from scipy.optimize import linear_sum_assignment


def match_faces(
    face_embs: np.ndarray,      # (N, 512) L2-normalised faces found in the class photo
    roster_embs: np.ndarray,    # (M, 512) L2-normalised enrolled photos
    owner_cols: np.ndarray,     # (M,) which student (0..K-1) each enrolled photo belongs to
    n_students: int,            # K
    threshold: float,
) -> list[tuple[Optional[int], Optional[float]]]:
    """For every face return (student_column, similarity), or (None, None) if nobody matches.

    1. Cosine similarity of every face with every enrolled photo.
    2. A student's score for a face = the best of their photos.
    3. Hungarian assignment, so one student can't be claimed by two faces.
    4. Keep a pair only if the similarity is >= threshold.
    """
    n = len(face_embs)
    results: list[tuple[Optional[int], Optional[float]]] = [(None, None)] * n
    if n == 0 or len(roster_embs) == 0 or n_students == 0:
        return results

    sim_all = face_embs @ roster_embs.T                      # (N, M)
    sim = np.full((n, n_students), -1.0, dtype=np.float32)   # (N, K)
    for col in np.unique(owner_cols):
        sim[:, col] = sim_all[:, owner_cols == col].max(axis=1)

    rows, cols = linear_sum_assignment(-sim)
    for r, c in zip(rows, cols):
        if sim[r, c] >= threshold:
            results[r] = (int(c), float(sim[r, c]))
    return results
