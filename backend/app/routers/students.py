"""Student CRUD and enrollment photo endpoints."""
from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.errors import AppError, duplicate, not_found
from app.models import CourseEnrollment, Student, StudentEmbedding
from app.schemas import (
    PhotoOut, PhotoUploadResponse, PhotoUploadResult,
    StudentCreate, StudentDetailOut, StudentOut, StudentUpdate,
)
from app.security import get_current_user
from app.services import enrollment as enroll_svc
from app.services.locks import inference_lock
from app.services.serializers import student_out
from app.services.storage import (
    absolute_from_data, data_url, delete_directory, delete_file,
    enrollment_dir, relative_to_data,
)

router = APIRouter(prefix="/api/students", tags=["students"])


def _embedding_from_db(emb: StudentEmbedding) -> np.ndarray:
    return np.frombuffer(emb.embedding, dtype=np.float32).copy()


def rebuild_cache(db: Session) -> None:
    """Rebuild the global roster cache from the database."""
    rows = db.scalars(select(StudentEmbedding)).all()
    enroll_svc.roster_cache.rebuild([
        {"student_id": r.student_id, "embedding_id": r.id, "embedding": _embedding_from_db(r)}
        for r in rows
    ])


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=StudentOut)
def create_student(
    body: StudentCreate,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    if db.scalar(select(Student).where(Student.roll_no == body.roll_no)):
        raise duplicate(f"roll_no '{body.roll_no}' already exists.")
    student = Student(**body.model_dump())
    db.add(student)
    db.flush()
    return student_out(student)


@router.get("", response_model=list[StudentOut])
def list_students(
    query: str = Query(""),
    course_id: Optional[int] = Query(None),
    active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    stmt = select(Student).order_by(Student.roll_no)
    if active is not None:
        stmt = stmt.where(Student.is_active == active)
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(Student.full_name.ilike(like) | Student.roll_no.ilike(like))
    if course_id is not None:
        stmt = stmt.where(
            Student.id.in_(
                select(CourseEnrollment.student_id).where(CourseEnrollment.course_id == course_id)
            )
        )
    return [student_out(s) for s in db.scalars(stmt).all()]


@router.get("/{student_id}", response_model=StudentDetailOut)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    s = db.get(Student, student_id)
    if s is None:
        raise not_found("Student")
    photos = [
        PhotoOut(
            id=e.id,
            url=data_url(f"enrollment/{s.id}/{Path(e.source_image_path).name}")
            if e.source_image_path else "",
            det_score=e.det_score,
            face_px=e.face_px,
        )
        for e in sorted(s.embeddings, key=lambda e: e.id)
    ]
    return StudentDetailOut(**student_out(s).model_dump(), photos=photos)


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    body: StudentUpdate,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    s = db.get(Student, student_id)
    if s is None:
        raise not_found("Student")
    # exclude_unset lets callers clear nullable fields (email, consent_date) with null,
    # while non-nullable fields ignore an explicit null.
    non_nullable = {"full_name", "is_active", "consent_recorded"}
    for field_name, val in body.model_dump(exclude_unset=True).items():
        if val is None and field_name in non_nullable:
            continue
        setattr(s, field_name, val)
    db.flush()
    return student_out(s)


def _check_photo(content: bytes, filename: str, insight_app) -> enroll_svc.PhotoResult:
    """Blocking inference, serialized by the global lock."""
    with inference_lock:
        return enroll_svc.check_enrollment_photo(content, filename, insight_app)


@router.post("/{student_id}/photos", response_model=PhotoUploadResponse)
async def upload_photos(
    student_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    from app.routers.health import _detector_ref

    s = db.get(Student, student_id)
    if s is None:
        raise not_found("Student")

    det = _detector_ref[0] if _detector_ref else None
    if det is None or not det.is_loaded:
        raise AppError(503, "Face detection models are not ready yet.", "SERVICE_UNAVAILABLE")
    insight_app = det.get_app() if hasattr(det, "get_app") else None
    if insight_app is None:
        raise AppError(503, "InsightFace is not available.", "SERVICE_UNAVAILABLE")

    max_allowed = max(0, settings.ENROLL_MAX_PHOTOS - len(s.embeddings))
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    results: list[PhotoUploadResult] = []
    warnings: list[str] = []

    # Other students' embeddings (with names) for the duplicate-identity warning.
    names = {st.id: st.full_name for st in db.scalars(select(Student)).all()}
    others = [
        {"student_id": e.student_id, "embedding": _embedding_from_db(e),
         "student_name": names.get(e.student_id)}
        for e in db.scalars(
            select(StudentEmbedding).where(StudentEmbedding.student_id != student_id)
        ).all()
    ]

    accepted = 0
    for upload in files:
        fname = upload.filename or "photo.jpg"
        content = await upload.read()

        if accepted >= max_allowed:
            results.append(PhotoUploadResult(
                filename=fname, accepted=False,
                reason=f"Maximum of {settings.ENROLL_MAX_PHOTOS} photos reached."))
            continue
        if len(content) > max_bytes:
            results.append(PhotoUploadResult(
                filename=fname, accepted=False,
                reason=f"File exceeds the {settings.MAX_UPLOAD_MB} MB upload limit."))
            continue

        res = await run_in_threadpool(_check_photo, content, fname, insight_app)
        if not res.accepted:
            results.append(PhotoUploadResult(filename=fname, accepted=False, reason=res.reason))
            continue

        warn = enroll_svc.check_duplicate_identity(res.embedding, student_id, others)
        if warn:
            warnings.append(warn)

        # Re-encode (EXIF-rotated, same orientation as the face that was embedded) under a
        # server-generated name; never use the client file name in a path.
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(content))).convert("RGB")
        dest = enrollment_dir(student_id) / f"{uuid.uuid4().hex}.jpg"
        img.save(dest, "JPEG", quality=90)

        db_emb = StudentEmbedding(
            student_id=student_id,
            embedding=res.embedding.astype(np.float32).tobytes(),
            source_image_path=relative_to_data(dest),
            det_score=res.det_score,
            face_px=res.face_px,
            blur_var=res.blur_var,
            model_version=getattr(det, "embedder_version", "arcface-buffalo_l"),
        )
        db.add(db_emb)
        db.flush()
        results.append(PhotoUploadResult(filename=fname, accepted=True, embedding_id=db_emb.id))
        accepted += 1

    db.flush()
    db.refresh(s)
    rebuild_cache(db)
    total = len(s.embeddings)
    return PhotoUploadResponse(
        results=results,
        embedding_count=total,
        ready=total >= settings.ENROLL_MIN_PHOTOS,
        warnings=list(dict.fromkeys(warnings)),
    )


@router.delete("/{student_id}/photos/{embedding_id}", status_code=204)
def delete_photo(
    student_id: int,
    embedding_id: int,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    emb = db.get(StudentEmbedding, embedding_id)
    if emb is None or emb.student_id != student_id:
        raise not_found("Photo")
    if emb.source_image_path:
        delete_file(absolute_from_data(emb.source_image_path))
    db.delete(emb)
    db.flush()
    rebuild_cache(db)


@router.delete("/{student_id}", status_code=204)
def delete_student(
    student_id: int,
    purge: bool = Query(False),
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    s = db.get(Student, student_id)
    if s is None:
        raise not_found("Student")

    if purge:
        # Hard delete: photos on disk, then the DB row (embeddings, enrollments and
        # attendance records cascade).
        delete_directory(settings.DATA_DIR / "enrollment" / str(student_id))
        db.delete(s)
    else:
        s.is_active = False

    db.flush()
    rebuild_cache(db)
