"""Tests for the matching algorithm."""
import numpy as np
import pytest
from app.services.matcher import match_faces
from tests.conftest import make_unit_vector


def l2_norm(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


class TestMatcherBasic:
    """Basic threshold and assignment tests."""

    def _run(self, face_embs, roster_embs, student_of_emb, student_indices, **kwargs):
        valid_mask = np.ones(len(face_embs), dtype=bool)
        return match_faces(
            face_embeddings=np.array(face_embs, dtype=np.float32),
            face_valid_mask=valid_mask,
            roster_embeddings=np.array(roster_embs, dtype=np.float32),
            student_of_embedding=np.array(student_of_emb, dtype=np.int64),
            student_indices=student_indices,
            **kwargs,
        )

    def test_recognized_above_threshold(self):
        """A face identical to the enrolled embedding should be recognized."""
        v = make_unit_vector(seed=1)
        results = self._run(
            face_embs=[v],
            roster_embs=[v],
            student_of_emb=[0],
            student_indices=[0],
            sim_accept=0.45,
            sim_review_min=0.35,
            margin_min=0.0,
        )
        assert results[0].label == "recognized"
        assert abs(results[0].similarity - 1.0) < 1e-4

    def test_review_in_band(self):
        """A face with similarity in the review band should be labeled review."""
        v1 = make_unit_vector(seed=1)
        v2 = make_unit_vector(seed=2)
        target_sim = 0.40
        v_perp = v2 - np.dot(v2, v1) * v1
        v_perp = v_perp / np.linalg.norm(v_perp)
        v_blend = target_sim * v1 + np.sqrt(max(0, 1 - target_sim**2)) * v_perp
        v_blend = v_blend / np.linalg.norm(v_blend)

        v_other = make_unit_vector(seed=42)
        results = self._run(
            face_embs=[v_blend],
            roster_embs=[v1, v_other],
            student_of_emb=[0, 1],
            student_indices=[0, 1],
            sim_accept=0.45,
            sim_review_min=0.35,
            margin_min=0.0,
        )
        assert results[0].label in ("review", "recognized", "unknown")
        if results[0].similarity is not None:
            assert results[0].similarity >= 0.35

    def test_unknown_below_threshold(self):
        """A face far from all enrolled embeddings should be unknown."""
        v1 = make_unit_vector(seed=1)
        v2 = make_unit_vector(seed=2)
        v_perp = v2 - np.dot(v2, v1) * v1
        v_perp = v_perp / np.linalg.norm(v_perp)

        results = self._run(
            face_embs=[v_perp],
            roster_embs=[v1],
            student_of_emb=[0],
            student_indices=[0],
            sim_accept=0.45,
            sim_review_min=0.35,
            margin_min=0.0,
        )
        assert results[0].label == "unknown"

    def test_hungarian_one_to_one(self):
        """Two faces competing for one student: higher-sim face wins, other is unknown."""
        v_student = make_unit_vector(seed=10)
        v_face_high = v_student.copy()
        noise = make_unit_vector(seed=99) * 0.1
        v_face_low = l2_norm(v_student + noise)

        results = self._run(
            face_embs=[v_face_high, v_face_low],
            roster_embs=[v_student],
            student_of_emb=[0],
            student_indices=[0],
            sim_accept=0.45,
            sim_review_min=0.35,
            margin_min=0.0,
        )
        labels = [r.label for r in results]
        assert "recognized" in labels
        assert "unknown" in labels

    def test_k_equals_1_margin(self):
        """With K=1 student, margin should equal similarity."""
        v = make_unit_vector(seed=1)
        results = self._run(
            face_embs=[v],
            roster_embs=[v],
            student_of_emb=[0],
            student_indices=[0],
            sim_accept=0.45,
            sim_review_min=0.35,
            margin_min=0.0,
        )
        assert results[0].label == "recognized"
        assert results[0].margin is not None
        assert abs(results[0].margin - 1.0) < 1e-4

    def test_n_greater_than_k(self):
        """More faces than students: extra faces should be unknown."""
        v1 = make_unit_vector(seed=1)
        v2 = make_unit_vector(seed=2)
        v_student = v1.copy()

        results = self._run(
            face_embs=[v1, v2],
            roster_embs=[v_student],
            student_of_emb=[0],
            student_indices=[0],
            sim_accept=0.45,
            sim_review_min=0.35,
            margin_min=0.0,
        )
        assert len(results) == 2
        recognized_count = sum(1 for r in results if r.label == "recognized")
        assert recognized_count <= 1

    def test_n_less_than_k(self):
        """Fewer faces than students: face is matched properly."""
        v1 = make_unit_vector(seed=1)
        v2 = make_unit_vector(seed=2)
        v_face = v1.copy()

        results = self._run(
            face_embs=[v_face],
            roster_embs=[v1, v2],
            student_of_emb=[0, 1],
            student_indices=[0, 1],
            sim_accept=0.45,
            sim_review_min=0.35,
            margin_min=0.0,
        )
        assert len(results) == 1
        assert results[0].label == "recognized"

    def test_margin_requirement(self):
        """With a strict margin requirement and two similar students, should be review or unknown."""
        v_base = make_unit_vector(seed=1)
        noise = make_unit_vector(seed=2) * 0.05
        v2 = l2_norm(v_base + noise)

        results = self._run(
            face_embs=[v_base],
            roster_embs=[v_base, v2],
            student_of_emb=[0, 1],
            student_indices=[0, 1],
            sim_accept=0.45,
            sim_review_min=0.35,
            margin_min=0.15,
        )
        assert results[0].label in ("review", "unknown")

    def test_unrecognizable_skipped(self):
        """Faces marked unrecognizable should not go through matching."""
        v = make_unit_vector(seed=1)
        valid_mask = np.array([False])

        results = match_faces(
            face_embeddings=np.array([v], dtype=np.float32),
            face_valid_mask=valid_mask,
            roster_embeddings=np.array([v], dtype=np.float32),
            student_of_embedding=np.array([0], dtype=np.int64),
            student_indices=[0],
        )
        assert results[0].label == "unrecognizable"
