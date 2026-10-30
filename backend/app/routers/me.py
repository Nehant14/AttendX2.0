"""Student: see my own attendance."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AttendanceRecord, AttendanceSession, Student
from app.routers.auth import student_only
from app.schemas import MyAttendanceOut, MyRecordOut

router = APIRouter(prefix="/api/me", tags=["student"])


@router.get("/attendance", response_model=MyAttendanceOut)
def my_attendance(user: dict = Depends(student_only), db: Session = Depends(get_db)):
    s = db.get(Student, user["student_id"])
    if s is None:
        raise HTTPException(404, "Student not found.")

    rows = db.execute(
        select(AttendanceRecord, AttendanceSession)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .where(AttendanceRecord.student_id == s.id)
        .order_by(AttendanceSession.created_at.desc())
    ).all()

    records = [MyRecordOut(session_id=sess.id, date=sess.created_at, status=rec.status) for rec, sess in rows]
    present = sum(1 for r in records if r.status == "present")
    total = len(records)
    return MyAttendanceOut(
        name=s.full_name, roll_no=s.roll_no,
        total=total, present=present, absent=total - present,
        percentage=round(present / total * 100, 1) if total else 0.0,
        records=records,
    )
