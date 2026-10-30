"""Admin: upload a class photo -> attendance session; view it; manually fix present/absent."""
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import AttendanceRecord, AttendanceSession, Student, StudentEmbedding
from app.routers.auth import admin_only
from app.schemas import RecordOut, SessionOut, StatusPatch
from app.services.imaging import decode_image
from app.services.locks import inference_lock
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/api/attendance", tags=["attendance"], dependencies=[Depends(admin_only)])


def _session_out(sess: AttendanceSession) -> SessionOut:
    records = sorted(sess.records, key=lambda r: r.student.roll_no)
    present = sum(1 for r in records if r.status == "present")
    sims = [r.similarity for r in records if r.status == "present" and r.similarity is not None]
    return SessionOut(
        id=sess.id,
        created_at=sess.created_at,
        total=len(records),
        present=present,
        absent=len(records) - present,
        avg_match=sum(sims) / len(sims) if sims else None,
        image_url=f"/files/{sess.image_path}" if sess.image_path else None,
        records=[
            RecordOut(student_id=r.student_id, roll_no=r.student.roll_no, full_name=r.student.full_name,
                      status=r.status, similarity=r.similarity)
            for r in records
        ],
    )


def _get(db: Session, session_id: int) -> AttendanceSession:
    sess = db.get(AttendanceSession, session_id)
    if sess is None:
        raise HTTPException(404, "Session not found.")
    return sess


@router.post("", response_model=SessionOut, status_code=201)
def create_session(file: UploadFile, request: Request, db: Session = Depends(get_db)):
    try:
        img = decode_image(file.file.read())
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    # Every student that has been added is part of the roster.
    students = db.scalars(select(Student).order_by(Student.roll_no)).all()
    if not students:
        raise HTTPException(400, "Add students first.")
    col_of = {s.id: i for i, s in enumerate(students)}
    rows = db.scalars(select(StudentEmbedding)).all()
    if not rows:
        raise HTTPException(400, "No face photos enrolled yet. Upload photos for the students first.")

    roster_embs = np.stack([np.frombuffer(r.embedding, dtype=np.float32) for r in rows])
    owner_cols = np.array([col_of[r.student_id] for r in rows])

    with inference_lock:
        matches, annotated = run_pipeline(
            img, request.app.state.detector, [s.full_name for s in students], roster_embs, owner_cols,
        )

    sess = AttendanceSession()
    db.add(sess)
    db.flush()  # get the id for the file path
    rel = f"sessions/{sess.id}/annotated.jpg"
    (settings.DATA_DIR / rel).parent.mkdir(parents=True, exist_ok=True)
    annotated.save(settings.DATA_DIR / rel, "JPEG", quality=88)
    sess.image_path = rel

    for i, s in enumerate(students):
        db.add(AttendanceRecord(
            session_id=sess.id, student_id=s.id,
            status="present" if i in matches else "absent",
            similarity=matches.get(i),
        ))
    db.flush()
    db.refresh(sess)
    return _session_out(sess)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    return _session_out(_get(db, session_id))


@router.patch("/{session_id}/records/{student_id}", response_model=SessionOut)
def set_status(session_id: int, student_id: int, body: StatusPatch, db: Session = Depends(get_db)):
    sess = _get(db, session_id)
    rec = db.scalar(select(AttendanceRecord).where(
        AttendanceRecord.session_id == session_id, AttendanceRecord.student_id == student_id))
    if rec is None:
        raise HTTPException(404, "Record not found.")
    rec.status = body.status
    db.flush()
    db.refresh(sess)
    return _session_out(sess)
