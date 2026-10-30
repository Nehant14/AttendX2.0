"""Admin: add students, upload their face photos (an embedding is saved for each)."""
import shutil
import uuid

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Student, StudentEmbedding
from app.routers.auth import admin_only
from app.schemas import (
    PhotoOut, PhotoUploadResponse, PhotoUploadResult,
    StudentCreate, StudentDetailOut, StudentOut,
)
from app.services.enrollment import embed_largest_face
from app.services.imaging import decode_image, save_jpeg
from app.services.locks import inference_lock

router = APIRouter(prefix="/api/students", tags=["students"], dependencies=[Depends(admin_only)])


def _out(s: Student) -> StudentOut:
    return StudentOut(id=s.id, roll_no=s.roll_no, full_name=s.full_name, photo_count=len(s.embeddings))


def _get(db: Session, student_id: int) -> Student:
    s = db.get(Student, student_id)
    if s is None:
        raise HTTPException(404, "Student not found.")
    return s


@router.post("", response_model=StudentOut, status_code=201)
def create_student(body: StudentCreate, db: Session = Depends(get_db)):
    roll_no = body.roll_no.strip()
    if db.scalar(select(Student).where(Student.roll_no == roll_no)):
        raise HTTPException(409, f"Roll number '{roll_no}' already exists.")
    s = Student(roll_no=roll_no, full_name=body.full_name.strip())
    db.add(s)
    db.flush()
    return _out(s)


@router.get("", response_model=list[StudentOut])
def list_students(db: Session = Depends(get_db)):
    return [_out(s) for s in db.scalars(select(Student).order_by(Student.roll_no)).all()]


@router.get("/{student_id}", response_model=StudentDetailOut)
def get_student(student_id: int, db: Session = Depends(get_db)):
    s = _get(db, student_id)
    photos = [PhotoOut(id=e.id, url=f"/files/{e.image_path}") for e in sorted(s.embeddings, key=lambda e: e.id)]
    return StudentDetailOut(**_out(s).model_dump(), photos=photos)


@router.post("/{student_id}/photos", response_model=PhotoUploadResponse)
def upload_photos(student_id: int, files: list[UploadFile], request: Request, db: Session = Depends(get_db)):
    s = _get(db, student_id)
    insight_app = request.app.state.detector.get_app()

    results = []
    for f in files:
        name = f.filename or "photo"
        try:
            img = decode_image(f.file.read())
        except ValueError as exc:
            results.append(PhotoUploadResult(filename=name, accepted=False, reason=str(exc)))
            continue

        with inference_lock:
            emb = embed_largest_face(insight_app, img)
        if emb is None:
            results.append(PhotoUploadResult(filename=name, accepted=False, reason="No face detected."))
            continue

        rel = f"enrollment/{s.id}/{uuid.uuid4().hex}.jpg"
        save_jpeg(settings.DATA_DIR / rel, img)
        db.add(StudentEmbedding(student_id=s.id, embedding=emb.astype(np.float32).tobytes(), image_path=rel))
        results.append(PhotoUploadResult(filename=name, accepted=True))

    return PhotoUploadResponse(results=results)


@router.delete("/{student_id}/photos/{photo_id}", status_code=204)
def delete_photo(student_id: int, photo_id: int, db: Session = Depends(get_db)):
    e = db.get(StudentEmbedding, photo_id)
    if e is None or e.student_id != student_id:
        raise HTTPException(404, "Photo not found.")
    (settings.DATA_DIR / e.image_path).unlink(missing_ok=True)
    db.delete(e)


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    s = _get(db, student_id)
    shutil.rmtree(settings.DATA_DIR / "enrollment" / str(s.id), ignore_errors=True)
    db.delete(s)
