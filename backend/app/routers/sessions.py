"""Session endpoints: attendance runs, retrieval, overrides, deletion, and CSV export."""
from __future__ import annotations

import datetime
import json
import shutil
import uuid
from pathlib import Path
from typing import Optional

import numpy as np

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.errors import AppError, not_found
from app.models import (
    AttendanceRecord, AttendanceSession, Course, CourseEnrollment, Detection,
    Student, StudentEmbedding, User,
)
from app.schemas import (
    AttendanceRecordOut, CountsOut, CourseOut, RecordPatch,
    SessionOut, SessionSummaryOut, UnmatchedFaceOut,
)
from app.security import get_current_user
from app.services import enrollment as enroll_svc
from app.services.export import generate_csv
from app.services.locks import inference_lock
from app.services.pipeline import decode_image, run_pipeline
from app.services.storage import (
    data_url, delete_directory, relative_to_data, session_dir,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _build_session_out(sess: AttendanceSession, db: Session) -> SessionOut:
    course = sess.course
    course_out = CourseOut(
        id=course.id,
        code=course.code,
        name=course.name,
        student_count=len(course.enrollments),
    )

    records_out = []
    present_count = 0
    needs_review_count = 0
    absent_count = 0

    for r in sess.records:
        if r.status == "present":
            present_count += 1
        elif r.status == "needs_review":
            needs_review_count += 1
        elif r.status == "absent":
            absent_count += 1

        bbox = json.loads(r.bbox_json) if r.bbox_json else None
        records_out.append(
            AttendanceRecordOut(
                student_id=r.student_id,
                roll_no=r.student.roll_no if r.student else "",
                full_name=r.student.full_name if r.student else "",
                status=r.status,
                similarity=r.similarity,
                margin=r.margin,
                bbox=bbox,
                marked_by=r.marked_by,
            )
        )

    # Sort records: needs_review first, then by roll_no
    records_out.sort(key=lambda x: (0 if x.status == "needs_review" else 1, x.roll_no))

    unmatched_out = []
    for d in sess.detections:
        if d.label in ("unknown", "unrecognizable"):
            bbox = json.loads(d.bbox_json) if d.bbox_json else [0.0, 0.0, 0.0, 0.0]
            unmatched_out.append(
                UnmatchedFaceOut(
                    bbox=bbox,
                    label=d.label,
                    det_score=d.det_score or 0.0,
                )
            )

    banner = None
    if sess.status == "needs_review":
        if sess.faces_unknown > 3 or (
            sess.faces_detected > 0 and (sess.faces_unknown / max(sess.faces_detected, 1) > 0.20)
        ):
            banner = "Many faces were not matched; please review."
        elif needs_review_count > 0:
            banner = "Some students require manual review."

    orig_rel = relative_to_data(sess.source_image_path) if sess.source_image_path else ""
    ann_rel = relative_to_data(sess.annotated_image_path) if sess.annotated_image_path else ""

    return SessionOut(
        id=sess.id,
        course=course_out,
        session_date=sess.session_date,
        period=sess.period,
        status=sess.status,
        detector_version=sess.detector_version,
        embedder_version=sess.embedder_version,
        counts=CountsOut(
            enrolled=len(records_out),
            faces_detected=sess.faces_detected,
            present=present_count,
            needs_review=needs_review_count,
            absent=absent_count,
            unknown_faces=sess.faces_unknown,
            unrecognizable_faces=sess.faces_unrecognizable,
        ),
        banner=banner,
        original_url=data_url(orig_rel) if orig_rel else None,
        annotated_url=data_url(ann_rel) if ann_rel else None,
        records=records_out,
        unmatched_faces=unmatched_out,
        processing_ms=sess.processing_ms,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SessionOut)
async def create_session(
    course_id: int = Form(...),
    session_date: datetime.date = Form(...),
    period: int = Form(1),
    replace: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth=Depends(get_current_user),
):
    from app.routers.health import _detector_ref

    course = db.get(Course, course_id)
    if course is None:
        raise not_found("Course")
    if period < 1:
        raise AppError(422, "period must be 1 or greater.", "VALIDATION_ERROR")

    # ── Validate the upload first (cheap), before touching any existing data ──────────
    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise AppError(413, f"Upload exceeds maximum allowed size of {settings.MAX_UPLOAD_MB} MB.",
                       "FILE_TOO_LARGE")
    try:
        await run_in_threadpool(decode_image, file_bytes)   # type/format check by decoding
    except ValueError as exc:
        raise AppError(415, str(exc), "UNSUPPORTED_MEDIA")

    existing = db.scalar(
        select(AttendanceSession).where(
            AttendanceSession.course_id == course_id,
            AttendanceSession.session_date == session_date,
            AttendanceSession.period == period,
        )
    )
    if existing and not replace:
        raise AppError(
            409,
            f"Session already exists for {session_date} period {period}. Pass replace=true to overwrite.",
            "SESSION_EXISTS",
        )

    # ── Roster: active students enrolled in the course ───────────────────────────────
    enrolled_students = db.scalars(
        select(Student)
        .join(CourseEnrollment, CourseEnrollment.student_id == Student.id)
        .where(CourseEnrollment.course_id == course_id, Student.is_active.is_(True))
        .order_by(Student.roll_no)
    ).all()
    enrolled_sids = [s.id for s in enrolled_students]
    if not enrolled_sids:
        raise AppError(422, "No enrolled active students in this course.", "NO_ENROLLED_EMBEDDINGS")

    roster_embs, s_of_e, unique_sids = enroll_svc.roster_cache.get_course_subset(enrolled_sids)
    if len(roster_embs) == 0:
        # Cache may be cold (e.g. embeddings written by another process): rebuild once.
        enroll_svc.roster_cache.rebuild([
            {"student_id": r.student_id, "embedding_id": r.id,
             "embedding": np.frombuffer(r.embedding, dtype=np.float32).copy()}
            for r in db.scalars(select(StudentEmbedding)).all()
        ])
        roster_embs, s_of_e, unique_sids = enroll_svc.roster_cache.get_course_subset(enrolled_sids)
    if len(roster_embs) == 0:
        raise AppError(422, "No face embeddings found for the enrolled students. Enroll photos first.",
                       "NO_ENROLLED_EMBEDDINGS")

    det = _detector_ref[0] if _detector_ref else None
    if det is None or not det.is_loaded:
        raise AppError(503, "Face detection models are loading. Please try again shortly.",
                       "SERVICE_UNAVAILABLE")

    student_id_to_info = {
        s.id: {"roll_no": s.roll_no, "full_name": s.full_name} for s in enrolled_students
    }

    # ── Run the pipeline into a temp dir; swap into place only when everything worked ─
    tmp_dir = settings.DATA_DIR / "tmp" / uuid.uuid4().hex
    tmp_dir.mkdir(parents=True, exist_ok=True)

    def _execute():
        with inference_lock:
            return run_pipeline(
                image_bytes=file_bytes,
                detector=det,
                roster_embeddings=roster_embs,
                student_of_embedding=s_of_e,
                unique_student_ids=unique_sids,
                student_id_to_info=student_id_to_info,
                session_dir_path=tmp_dir,
            )

    try:
        pipe_res = await run_in_threadpool(_execute)
        if pipe_res.status == "failed":
            raise AppError(415, pipe_res.error or "Could not process the image.", "UNSUPPORTED_MEDIA")

        if existing:
            delete_directory(settings.DATA_DIR / "sessions" / str(existing.id))
            db.delete(existing)
            db.flush()

        created_by = None
        if auth and "sub" in auth and db.get(User, int(auth["sub"])) is not None:
            created_by = int(auth["sub"])

        sess = AttendanceSession(
            course_id=course_id, session_date=session_date, period=period,
            detector_version=pipe_res.detector_version,
            embedder_version=pipe_res.embedder_version,
            faces_detected=pipe_res.faces_detected,
            faces_unrecognizable=pipe_res.faces_unrecognizable,
            faces_unknown=pipe_res.faces_unknown,
            status=pipe_res.status, processing_ms=pipe_res.processing_ms,
            created_by=created_by,
        )
        db.add(sess)
        db.flush()

        final_dir = session_dir(sess.id)
        for name in ("original.jpg", "annotated.jpg"):
            src = tmp_dir / name
            if src.exists():
                shutil.move(str(src), str(final_dir / name))
        sess.source_image_path = relative_to_data(final_dir / "original.jpg")
        sess.annotated_image_path = relative_to_data(final_dir / "annotated.jpg")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    for sr in pipe_res.student_results:
        db.add(AttendanceRecord(
            session_id=sess.id, student_id=sr["student_id"], status=sr["status"],
            similarity=sr["similarity"], margin=sr["margin"],
            bbox_json=json.dumps(sr["bbox"]) if sr["bbox"] else None,
            marked_by=sr["marked_by"],
        ))
    for d in pipe_res.detections:
        db.add(Detection(
            session_id=sess.id, bbox_json=json.dumps(d["bbox"]), det_score=d["det_score"],
            face_px=d["face_px"], label=d["label"], matched_student_id=d["student_id"],
            similarity=d["similarity"],
        ))

    db.flush()
    db.refresh(sess)
    return _build_session_out(sess, db)


@router.get("", response_model=list[SessionSummaryOut])
def list_sessions(
    course_id: Optional[int] = Query(None),
    from_date: Optional[datetime.date] = Query(None, alias="from"),
    to_date: Optional[datetime.date] = Query(None, alias="to"),
    student_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    stmt = select(AttendanceSession)
    if student_id is not None:
        stmt = stmt.where(
            AttendanceSession.id.in_(
                select(AttendanceRecord.session_id).where(AttendanceRecord.student_id == student_id)
            )
        )
    if course_id is not None:
        stmt = stmt.where(AttendanceSession.course_id == course_id)
    if from_date is not None:
        stmt = stmt.where(AttendanceSession.session_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(AttendanceSession.session_date <= to_date)
    stmt = stmt.order_by(AttendanceSession.session_date.desc(), AttendanceSession.period.desc())

    sessions = db.scalars(stmt).all()
    summaries = []
    for s in sessions:
        present = sum(1 for r in s.records if r.status == "present")
        absent = sum(1 for r in s.records if r.status == "absent")
        needs_review = sum(1 for r in s.records if r.status == "needs_review")
        summaries.append(
            SessionSummaryOut(
                id=s.id,
                course_id=s.course_id,
                course_code=s.course.code if s.course else "",
                session_date=s.session_date,
                period=s.period,
                status=s.status,
                faces_detected=s.faces_detected,
                present=present,
                absent=absent,
                needs_review=needs_review,
            )
        )
    return summaries


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    sess = db.get(AttendanceSession, session_id)
    if sess is None:
        raise not_found("Session")
    return _build_session_out(sess, db)


@router.patch("/{session_id}/records/{student_id}", response_model=SessionOut)
def update_record_status(
    session_id: int,
    student_id: int,
    body: RecordPatch,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    sess = db.get(AttendanceSession, session_id)
    if sess is None:
        raise not_found("Session")

    rec = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
    )
    if rec is None:
        raise not_found("AttendanceRecord")

    rec.status = body.status
    rec.marked_by = "teacher"
    db.flush()

    # Recompute session status
    remaining_review = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.status == "needs_review",
        )
    )

    high_unknown = (
        sess.faces_unknown > 3
        or (sess.faces_detected > 0 and (sess.faces_unknown / max(sess.faces_detected, 1) > 0.20))
    )

    if not remaining_review and not high_unknown:
        sess.status = "done"
    else:
        sess.status = "needs_review"

    db.flush()
    db.refresh(sess)
    return _build_session_out(sess, db)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    sess = db.get(AttendanceSession, session_id)
    if sess is None:
        raise not_found("Session")

    delete_directory(settings.DATA_DIR / "sessions" / str(session_id))
    db.delete(sess)
    db.flush()


@router.get("/{session_id}/export.csv")
def export_session_csv(
    session_id: int,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    sess = db.get(AttendanceSession, session_id)
    if sess is None:
        raise not_found("Session")

    rows = []
    course_code = sess.course.code if sess.course else ""
    for r in sess.records:
        rows.append(
            {
                "session_date": sess.session_date,
                "period": sess.period,
                "course_code": course_code,
                "roll_no": r.student.roll_no if r.student else "",
                "full_name": r.student.full_name if r.student else "",
                "status": r.status,
                "similarity": r.similarity,
                "marked_by": r.marked_by,
            }
        )

    csv_bytes = generate_csv(rows)
    filename = f"attendance_session_{session_id}_{sess.session_date}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
