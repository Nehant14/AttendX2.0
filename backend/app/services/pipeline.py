"""
Attendance pipeline: decode image → detect → match → annotate → return result.
Testable without a live database (accepts in-memory data).
"""
from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.config import settings
from app.services.annotate import annotate_image, build_detection_dicts
from app.services.matcher import match_faces, student_best_scores
from app.services.storage import save_named_image

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    bbox: list[float]
    det_score: float
    face_px: int
    embedding: Optional[np.ndarray]
    label: str = "unknown"
    student_index: Optional[int] = None   # column into unique_student_ids
    similarity: Optional[float] = None
    margin: Optional[float] = None


@dataclass
class PipelineResult:
    original_path: Optional[Path]
    annotated_path: Optional[Path]
    detector_version: str
    embedder_version: str
    faces_detected: int
    faces_unrecognizable: int
    faces_unknown: int
    detections: list[dict]        # one dict per detected face (for DB)
    student_results: list[dict]   # one dict per roster student
    banner: Optional[str]
    status: str                   # done | needs_review | failed
    processing_ms: int
    error: Optional[str] = None


def decode_image(image_bytes: bytes) -> np.ndarray:
    """
    Decode image bytes → BGR array, EXIF-rotated.
    Raises ValueError for bad / unsupported formats.
    """
    try:
        pil = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise ValueError(f"Cannot decode image: {exc}") from exc

    fmt = (pil.format or "").lower()
    # "mpo" is what many phone cameras write for ordinary JPEGs.
    if fmt not in ("jpeg", "jpg", "mpo", "png", "webp"):
        raise ValueError(f"Unsupported image format '{pil.format}'. Use JPEG, PNG or WebP.")

    pil = ImageOps.exif_transpose(pil).convert("RGB")
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def maybe_downscale(img: np.ndarray, max_side: int = 6000) -> np.ndarray:
    h, w = img.shape[:2]
    if max(h, w) <= max_side:
        return img
    scale = max_side / max(h, w)
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def run_pipeline(
    image_bytes: bytes,
    detector,
    roster_embeddings: np.ndarray,        # (M, 512)
    student_of_embedding: np.ndarray,     # (M,) student IDs
    unique_student_ids: list[int],        # [K] students that have embeddings
    student_id_to_info: dict[int, dict],  # ALL enrolled active students: id -> {full_name, roll_no}
    session_dir_path: Optional[Path] = None,
) -> PipelineResult:
    """
    Full attendance pipeline.

    Returns a PipelineResult with all data needed to write DB records.
    Saves original.jpg and annotated.jpg into session_dir_path when provided.
    """
    t0 = time.monotonic()
    det_ver = getattr(detector, "version", "unknown")
    emb_ver = getattr(detector, "embedder_version", "arcface-buffalo_l")

    # 1. Decode
    try:
        img_bgr = decode_image(image_bytes)
    except ValueError as exc:
        return PipelineResult(
            original_path=None, annotated_path=None,
            detector_version=det_ver, embedder_version=emb_ver,
            faces_detected=0, faces_unrecognizable=0, faces_unknown=0,
            detections=[], student_results=[],
            banner=None, status="failed",
            processing_ms=int((time.monotonic() - t0) * 1000),
            error=str(exc),
        )

    img_bgr = maybe_downscale(img_bgr)

    # Save original
    original_path: Optional[Path] = None
    if session_dir_path:
        pil_orig = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        original_path = save_named_image(session_dir_path, pil_orig, "original.jpg")

    # 2. Detect
    raw = detector.detect(img_bgr)

    # 3. Filter by confidence, label unrecognizable
    detected: list[DetectedFace] = []
    for f in raw:
        if f.det_score < settings.DET_CONF_MIN:
            continue
        too_small = f.face_px < settings.MIN_FACE_PX or f.embedding is None
        detected.append(DetectedFace(
            bbox=f.bbox, det_score=f.det_score, face_px=f.face_px,
            embedding=f.embedding,
            label="unrecognizable" if too_small else "unknown",
        ))

    # 4. Match
    recognizable = [df for df in detected if df.label != "unrecognizable"]
    N_valid = len(recognizable)
    K = len(unique_student_ids)

    if N_valid > 0 and K > 0 and len(roster_embeddings) > 0:
        face_embs = np.stack([df.embedding for df in recognizable], axis=0)
        valid_mask = np.ones(N_valid, dtype=bool)

        # Re-map student IDs -> column indices for the matcher
        sid_to_col = {sid: col for col, sid in enumerate(unique_student_ids)}
        emb_cols = np.array(
            [sid_to_col.get(int(sid), 0) for sid in student_of_embedding], dtype=np.int64
        )

        match_results = match_faces(
            face_embeddings=face_embs,
            face_valid_mask=valid_mask,
            roster_embeddings=roster_embeddings,
            student_of_embedding=emb_cols,
            student_indices=list(range(K)),
        )
        for i, mr in enumerate(match_results):
            df = recognizable[i]
            df.label = mr.label
            if mr.label in ("recognized", "review"):
                df.student_index = mr.student_index
                df.similarity = mr.similarity
                df.margin = mr.margin

    # Best-looking face for every student, even those who end up absent, so the teacher can
    # still see how close the match was (and re-decide with other thresholds later).
    best_scores: list = [None] * K
    if N_valid > 0 and K > 0 and len(roster_embeddings) > 0:
        best_scores = student_best_scores(
            face_embeddings=face_embs, roster_embeddings=roster_embeddings,
            student_of_embedding=emb_cols, K=K,
        )

    # 5. Build student results
    recognized_col: dict[int, int] = {}   # col -> index in recognizable
    review_col: dict[int, int] = {}

    for i, df in enumerate(recognizable):
        if df.label == "recognized" and df.student_index is not None:
            recognized_col[df.student_index] = i
        elif df.label == "review" and df.student_index is not None:
            review_col[df.student_index] = i

    # Every enrolled student gets a row. Students with no stored embedding cannot be
    # recognized, so they are absent (the teacher can mark them present manually).
    sid_to_col_all = {sid: col for col, sid in enumerate(unique_student_ids)}
    ordered_sids = sorted(
        student_id_to_info, key=lambda x: (student_id_to_info[x].get("roll_no", ""), x)
    )
    student_results = []
    for sid in ordered_sids:
        info = student_id_to_info.get(sid, {})
        col = sid_to_col_all.get(sid)
        base = {
            "student_id": sid, "roll_no": info.get("roll_no", ""),
            "full_name": info.get("full_name", ""), "marked_by": "auto",
        }
        if col is not None and col in recognized_col:
            df = recognizable[recognized_col[col]]
            student_results.append({**base, "status": "present",
                                    "similarity": df.similarity, "margin": df.margin,
                                    "bbox": df.bbox})
        elif col is not None and col in review_col:
            df = recognizable[review_col[col]]
            student_results.append({**base, "status": "needs_review",
                                    "similarity": df.similarity, "margin": df.margin,
                                    "bbox": df.bbox})
        else:
            best = best_scores[col] if col is not None else None
            if best is not None:
                face_row, b_sim, b_margin = best
                student_results.append({**base, "status": "absent",
                                        "similarity": b_sim, "margin": b_margin,
                                        "bbox": recognizable[face_row].bbox})
            else:
                student_results.append({**base, "status": "absent",
                                        "similarity": None, "margin": None, "bbox": None})

    # 6. Sanity / banner
    n_unrecog = sum(1 for df in detected if df.label == "unrecognizable")
    n_unknown = sum(1 for df in detected if df.label == "unknown")
    n_total = len(detected)
    banner: Optional[str] = None
    has_review = any(r["status"] == "needs_review" for r in student_results)

    if n_unknown > 3 or (n_total > 0 and n_unknown / n_total > 0.20):
        banner = "Many faces were not matched; please review."
        has_review = True

    status = "needs_review" if has_review else "done"

    # 7. Annotate
    col_to_name = {col: student_id_to_info.get(sid, {}).get("full_name", f"Student {sid}")
                   for col, sid in enumerate(unique_student_ids)}

    det_dicts = [
        {"bbox": df.bbox, "label": df.label, "student_index": df.student_index,
         "similarity": df.similarity, "det_score": df.det_score}
        for df in detected
    ]
    ann_dicts = build_detection_dicts(det_dicts, col_to_name)
    annotated_pil = annotate_image(img_bgr, ann_dicts)

    annotated_path: Optional[Path] = None
    if session_dir_path:
        annotated_path = save_named_image(session_dir_path, annotated_pil, "annotated.jpg")

    # Build final detections for DB
    final_detections = []
    for df in detected:
        sid = unique_student_ids[df.student_index] if df.student_index is not None else None
        final_detections.append({
            "bbox": df.bbox, "det_score": df.det_score, "face_px": df.face_px,
            "label": df.label, "student_id": sid, "similarity": df.similarity,
        })

    return PipelineResult(
        original_path=original_path,
        annotated_path=annotated_path,
        detector_version=det_ver,
        embedder_version=emb_ver,
        faces_detected=n_total,
        faces_unrecognizable=n_unrecog,
        faces_unknown=n_unknown,
        detections=final_detections,
        student_results=student_results,
        banner=banner,
        status=status,
        processing_ms=int((time.monotonic() - t0) * 1000),
    )
