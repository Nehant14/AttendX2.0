"""Admin: upload class photo(s) -> attendance; view it; manually fix present/absent; retake."""
import json
import uuid

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
        image_urls=[f"/files/{p}" for p in json.loads(sess.images)],
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


def _mark(db: Session, request: Request, files: list[UploadFile], sess: AttendanceSession | None) -> SessionOut:
    """Run every class photo and (re)write the attendance. Present = matched in ANY of the photos.

    sess=None creates a new session; otherwise that session is redone (retake).
    """
    try:
        imgs = [decode_image(f.file.read()) for f in files]
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if not imgs:
        raise HTTPException(400, "Upload at least one class photo.")

    # Every student that has been added is part of the roster.
    students = db.scalars(select(Student).order_by(Student.roll_no)).all()
    if not students:
        raise HTTPException(400, "Add students first.")
    col_of = {s.id: i for i, s in enumerate(students)}
    rows = db.scalars(select(StudentEmbedding)).all()
    if not rows:
        raise HTTPException(400, "No face photos enrolled yet. Upload photos for the students first.")

    chunks = [np.frombuffer(r.embedding, dtype=np.float32).reshape(-1, 512) for r in rows]
    roster_embs = np.concatenate(chunks)
    owner_cols = np.concatenate([np.full(len(c), col_of[r.student_id]) for c, r in zip(chunks, rows)])

    best: dict[int, float] = {}   # student column -> best similarity over all photos
    annotated = []
    with inference_lock:
        for img in imgs:
            matches, ann = run_pipeline(
                img, request.app.state.detector, [s.full_name for s in students], roster_embs, owner_cols)
            for col, sim in matches.items():
                best[col] = max(best.get(col, -1.0), sim)
            annotated.append(ann)

    if sess is None:
        sess = AttendanceSession(images="[]")
        db.add(sess)
        db.flush()  # get the id for the file paths

    # Save the new annotated photos (new names, so browsers never show a cached old one), drop the old ones.
    old = json.loads(sess.images)
    paths = []
    for ann in annotated:
        rel = f"sessions/{sess.id}/{uuid.uuid4().hex}.jpg"
        (settings.DATA_DIR / rel).parent.mkdir(parents=True, exist_ok=True)
        ann.save(settings.DATA_DIR / rel, "JPEG", quality=88)
        paths.append(rel)
    for rel in old:
        (settings.DATA_DIR / rel).unlink(missing_ok=True)
    sess.images = json.dumps(paths)

    existing = {r.student_id: r for r in sess.records}
    for i, s in enumerate(students):
        status = "present" if i in best else "absent"
        rec = existing.get(s.id)
        if rec is None:
            db.add(AttendanceRecord(session_id=sess.id, student_id=s.id, status=status, similarity=best.get(i)))
        else:
            rec.status, rec.similarity = status, best.get(i)
    db.flush()
    db.refresh(sess)
    return _session_out(sess)


@router.post("", response_model=SessionOut, status_code=201)
def create_session(files: list[UploadFile], request: Request, db: Session = Depends(get_db)):
    return _mark(db, request, files, None)


@router.put("/{session_id}", response_model=SessionOut)
def retake_session(session_id: int, files: list[UploadFile], request: Request, db: Session = Depends(get_db)):
    """Retake: redo this class from new photos (replaces the old result, manual changes included)."""
    return _mark(db, request, files, _get(db, session_id))


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
