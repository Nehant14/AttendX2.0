"""
Enrollment service: quality checks, photo storage, embedding persistence,
duplicate-identity warning, and the in-memory roster cache.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.config import settings
from app.services.embedder import cosine_similarity

logger = logging.getLogger(__name__)


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class PhotoResult:
    """Outcome of processing one enrollment photo."""
    filename: str
    accepted: bool
    reason: Optional[str] = None
    embedding: Optional[np.ndarray] = None
    det_score: Optional[float] = None
    face_px: Optional[int] = None
    blur_var: Optional[float] = None
    saved_path: Optional[Path] = None


# ─── Roster cache ─────────────────────────────────────────────────────────────

@dataclass
class RosterCache:
    """
    In-memory cache of all stored embeddings.
    Rebuilt whenever embeddings are added or removed.
    """
    student_ids: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    embedding_ids: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    matrix: np.ndarray = field(default_factory=lambda: np.zeros((0, 512), dtype=np.float32))

    def rebuild(self, embeddings: list[dict]) -> None:
        """
        Rebuild from a list of dicts:
          {student_id: int, embedding_id: int, embedding: np.ndarray (512,)}
        """
        if not embeddings:
            self.student_ids = np.array([], dtype=np.int64)
            self.embedding_ids = np.array([], dtype=np.int64)
            self.matrix = np.zeros((0, 512), dtype=np.float32)
            return
        self.student_ids = np.array([e["student_id"] for e in embeddings], dtype=np.int64)
        self.embedding_ids = np.array([e["embedding_id"] for e in embeddings], dtype=np.int64)
        self.matrix = np.stack([e["embedding"] for e in embeddings], axis=0).astype(np.float32)

    def get_course_subset(
        self, course_student_ids: list[int]
    ) -> tuple[np.ndarray, np.ndarray, list[int]]:
        """
        Extract embeddings for a specific set of student IDs.

        Returns:
            embs           (M, 512) — embedding matrix
            student_of_emb (M,)    — student_id for each row
            unique_sids    [K]     — unique student IDs present
        """
        if len(self.student_ids) == 0:
            return np.zeros((0, 512), dtype=np.float32), np.array([], dtype=np.int64), []

        cs = set(course_student_ids)
        mask = np.array([int(sid) in cs for sid in self.student_ids], dtype=bool)
        if not mask.any():
            return np.zeros((0, 512), dtype=np.float32), np.array([], dtype=np.int64), []

        embs = self.matrix[mask]
        sids = self.student_ids[mask]
        # Preserve insertion order, deduplicate
        seen: set[int] = set()
        unique: list[int] = []
        for s in sids.tolist():
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return embs, sids, unique


# Global singleton
roster_cache = RosterCache()


# ─── Quality checks ───────────────────────────────────────────────────────────

def compute_blur_variance(img_bgr: np.ndarray, bbox: list[float]) -> float:
    """
    Laplacian variance on the face crop (112×112 grayscale).
    Higher = sharper.
    """
    x1, y1, x2, y2 = (int(v) for v in bbox)
    h, w = img_bgr.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    crop = img_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return 0.0
    crop = cv2.resize(crop, (112, 112))
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


# Enrollment photos are close-ups (selfie-style). SCRFD-34GF has a fixed 640×640 input,
# so we use 640 as the primary size and fall back to 320 for very close-up crops where
# the face fills the entire frame and might be missed at the native resolution.
ENROLL_DET_SIZES = (640, 320)


def detect_faces_multiscale(insight_app, img_bgr: np.ndarray, sizes=ENROLL_DET_SIZES):
    """Run InsightFace at several detector input sizes; return the first non-empty result.

    The caller must hold the global inference lock (the detector's input size is mutated
    temporarily and restored).
    """
    det_model = getattr(insight_app, "det_model", None)
    old_size = getattr(det_model, "input_size", None)
    try:
        for size in sizes:
            if det_model is not None:
                det_model.input_size = (size, size)
            faces = insight_app.get(img_bgr)
            if faces:
                return faces
        return []
    finally:
        if det_model is not None and old_size is not None:
            det_model.input_size = old_size


def check_enrollment_photo(
    img_bytes: bytes,
    filename: str,
    insight_app,          # insightface.app.FaceAnalysis
) -> PhotoResult:
    """
    Run all quality checks on one enrollment photo.

    Checks (in order):
      1. Image decodable.
      2. At least one face detected.
      3. No dominant second face (area > 30% of largest).
      4. Detection score >= ENROLL_MIN_DET_SCORE.
      5. Face width >= ENROLL_MIN_FACE_PX.
      6. Laplacian variance >= ENROLL_MIN_BLUR_VAR.
      7. Embedding computable.

    Returns PhotoResult with accepted=True or accepted=False + reason.
    """
    # Decode
    try:
        pil = Image.open(io.BytesIO(img_bytes))
        pil = ImageOps.exif_transpose(pil).convert("RGB")
        img_bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    except Exception as exc:
        return PhotoResult(filename=filename, accepted=False,
                           reason=f"Cannot decode image: {exc}")

    # Detect
    try:
        faces = detect_faces_multiscale(insight_app, img_bgr)
    except Exception as exc:
        return PhotoResult(filename=filename, accepted=False,
                           reason=f"Face detection failed: {exc}")

    if not faces:
        return PhotoResult(filename=filename, accepted=False,
                           reason="No face detected in the photo.")

    def area(f) -> float:
        x1, y1, x2, y2 = f.bbox
        return max(0.0, float((x2 - x1) * (y2 - y1)))

    faces_sorted = sorted(faces, key=area, reverse=True)
    dominant = faces_sorted[0]

    # Second-face check
    if len(faces_sorted) > 1:
        dom_a = area(dominant)
        sec_a = area(faces_sorted[1])
        if dom_a > 0 and sec_a / dom_a > 0.30:
            return PhotoResult(filename=filename, accepted=False,
                               reason="Multiple faces detected. Use a photo with only your face.")

    x1, y1, x2, y2 = dominant.bbox
    face_px = int(x2 - x1)
    det_score = float(dominant.det_score)

    if det_score < settings.ENROLL_MIN_DET_SCORE:
        return PhotoResult(filename=filename, accepted=False,
                           reason=(f"Face detection confidence too low "
                                   f"({det_score:.2f} < {settings.ENROLL_MIN_DET_SCORE}). "
                                   "Ensure the face is clearly visible."))

    if face_px < settings.ENROLL_MIN_FACE_PX:
        return PhotoResult(filename=filename, accepted=False,
                           reason=(f"Face too small ({face_px}px < {settings.ENROLL_MIN_FACE_PX}px). "
                                   "Move closer to the camera."))

    blur_var = compute_blur_variance(img_bgr, [x1, y1, x2, y2])
    if blur_var < settings.ENROLL_MIN_BLUR_VAR:
        return PhotoResult(filename=filename, accepted=False,
                           reason=(f"Photo is too blurry (sharpness {blur_var:.1f} "
                                   f"< {settings.ENROLL_MIN_BLUR_VAR}). "
                                   "Ensure the photo is in focus."))

    emb = getattr(dominant, "normed_embedding", None)
    if emb is None:
        return PhotoResult(filename=filename, accepted=False,
                           reason="Could not compute face embedding. Try a clearer, frontal photo.")

    return PhotoResult(
        filename=filename, accepted=True,
        embedding=emb.astype(np.float32),
        det_score=det_score, face_px=face_px, blur_var=blur_var,
    )


def check_duplicate_identity(
    new_embedding: np.ndarray,
    new_student_id: int,
    all_embeddings: list[dict],   # [{student_id, embedding, student_name}]
) -> Optional[str]:
    """
    Return a warning string if the embedding is suspiciously similar
    to another student's embeddings (similarity >= ENROLL_DUPLICATE_SIM).
    """
    threshold = settings.ENROLL_DUPLICATE_SIM
    max_sim, max_name = -1.0, None

    for item in all_embeddings:
        if item["student_id"] == new_student_id:
            continue
        sim = cosine_similarity(new_embedding, item["embedding"])
        if sim > max_sim:
            max_sim = sim
            max_name = item.get("student_name", f"student ID {item['student_id']}")

    if max_sim >= threshold:
        return (f"This face is similar to {max_name} (similarity={max_sim:.2f}). "
                "Verify these are different people.")
    return None
