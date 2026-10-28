"""
Matching service: cosine similarity matrix + per-student max pooling
+ Hungarian one-to-one assignment + threshold decisions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.config import settings
from app.services.embedder import cosine_matrix

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Matching outcome for a single face."""
    face_index: int
    label: str                       # recognized | review | unknown | unrecognizable
    student_index: Optional[int]     # column index into student_indices list
    similarity: Optional[float]
    margin: Optional[float]


def match_faces(
    face_embeddings: np.ndarray,         # (N, 512) L2-normalised
    face_valid_mask: np.ndarray,         # (N,) bool — False = unrecognizable
    roster_embeddings: np.ndarray,       # (M, 512) L2-normalised
    student_of_embedding: np.ndarray,    # (M,) int — column index for each embedding
    student_indices: list[int],          # [K] unique student column indices
    sim_accept: float | None = None,
    sim_review_min: float | None = None,
    margin_min: float | None = None,
) -> list[MatchResult]:
    """
    Match faces to students using cosine similarity and Hungarian assignment.

    For each of the N faces returns a MatchResult.
    Faces with face_valid_mask=False are returned immediately as "unrecognizable".

    Algorithm (per spec §8.4):
      1. S_all (N_valid, M) = face_embeddings @ roster_embeddings.T
      2. S (N_valid, K) = per-student max over their embedding rows.
      3. Hungarian on -S for one-to-one assignment.
      4. Threshold: sim >= SIM_ACCEPT and margin >= MARGIN_MIN -> recognized
                    sim >= SIM_REVIEW_MIN                       -> review
                    else                                        -> unknown
      5. Unassigned valid faces -> unknown.
    """
    sim_accept = sim_accept if sim_accept is not None else settings.SIM_ACCEPT
    sim_review_min = sim_review_min if sim_review_min is not None else settings.SIM_REVIEW_MIN
    margin_min = margin_min if margin_min is not None else settings.MARGIN_MIN

    N = len(face_valid_mask)
    results: list[Optional[MatchResult]] = [None] * N

    # Mark unrecognizable faces immediately
    for i in range(N):
        if not face_valid_mask[i]:
            results[i] = MatchResult(face_index=i, label="unrecognizable",
                                     student_index=None, similarity=None, margin=None)

    valid_idx = [i for i in range(N) if face_valid_mask[i]]
    N_valid = len(valid_idx)

    if N_valid == 0 or len(roster_embeddings) == 0 or len(student_indices) == 0:
        for i in valid_idx:
            results[i] = MatchResult(face_index=i, label="unknown",
                                     student_index=None, similarity=None, margin=None)
        return results  # type: ignore[return-value]

    K = len(student_indices)
    # Map student index value -> column in S
    sid_to_col: dict[int, int] = {sid: col for col, sid in enumerate(student_indices)}

    # Step 1: S_all (N_valid, M)
    valid_embs = face_embeddings[valid_idx]
    S_all = cosine_matrix(valid_embs, roster_embeddings)  # (N_valid, M)

    # Step 2: S (N_valid, K) — per-student max
    S = np.full((N_valid, K), -2.0, dtype=np.float32)
    for m, sid in enumerate(student_of_embedding):
        col = sid_to_col.get(int(sid))
        if col is not None:
            S[:, col] = np.maximum(S[:, col], S_all[:, m])

    # Step 3: Hungarian assignment
    row_ind, col_ind = linear_sum_assignment(-S)

    for r, c in zip(row_ind, col_ind):
        face_i = valid_idx[r]
        sim = float(S[r, c])

        # Margin: sim lead over best OTHER student
        if K > 1:
            others = np.delete(S[r], c)
            mg = sim - float(np.max(others))
        else:
            mg = sim  # only one student

        if sim >= sim_accept and mg >= margin_min:
            label = "recognized"
        elif sim >= sim_review_min:
            label = "review"
        else:
            label = "unknown"

        results[face_i] = MatchResult(
            face_index=face_i,
            label=label,
            student_index=c if label != "unknown" else None,
            similarity=sim if label != "unknown" else None,
            margin=mg if label != "unknown" else None,
        )

    # Remaining valid faces not assigned -> unknown
    for i in valid_idx:
        if results[i] is None:
            results[i] = MatchResult(face_index=i, label="unknown",
                                     student_index=None, similarity=None, margin=None)

    return results  # type: ignore[return-value]


def student_best_scores(
    face_embeddings: np.ndarray,         # (N, 512) L2-normalised, recognizable faces only
    roster_embeddings: np.ndarray,       # (M, 512) L2-normalised
    student_of_embedding: np.ndarray,    # (M,) column index (0..K-1) for each embedding
    K: int,
) -> list[Optional[tuple[int, float, float]]]:
    """
    For every student column, the face that looks most like them, independent of the
    one-to-one assignment and of any threshold.

    Returns a list of length K. Each entry is (face_row, similarity, margin) or None when
    there are no faces / no embeddings. ``margin`` is the student's similarity minus the best
    OTHER student's similarity on that same face, so it is negative when someone else
    resembles that face more. This is what lets absent students still show their numbers.
    """
    if len(face_embeddings) == 0 or len(roster_embeddings) == 0 or K == 0:
        return [None] * K

    S_all = cosine_matrix(face_embeddings, roster_embeddings)          # (N, M)
    S = np.full((len(face_embeddings), K), -2.0, dtype=np.float32)
    for m, col in enumerate(student_of_embedding):
        c = int(col)
        if 0 <= c < K:
            S[:, c] = np.maximum(S[:, c], S_all[:, m])

    out: list[Optional[tuple[int, float, float]]] = []
    for c in range(K):
        col = S[:, c]
        if col.max() <= -2.0:            # student has no embeddings in this roster slice
            out.append(None)
            continue
        r = int(np.argmax(col))
        sim = float(col[r])
        if K > 1:
            margin = sim - float(np.max(np.delete(S[r], c)))
        else:
            margin = sim
        out.append((r, sim, margin))
    return out


def decide_status(sim: float, margin: float, sim_accept: float,
                  sim_review_min: float, margin_min: float) -> str:
    """Same rule as match_faces, expressed as a student status."""
    if sim >= sim_accept and margin >= margin_min:
        return "present"
    if sim >= sim_review_min:
        return "needs_review"
    return "absent"
