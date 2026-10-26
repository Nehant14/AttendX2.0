"""Attendance history and summary reporting endpoints."""
from __future__ import annotations

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AttendanceRecord, AttendanceSession, Course, Student
from app.schemas import AttendanceRowOut, AttendanceSummaryOut
from app.security import get_current_user
from app.services.export import generate_csv

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def _build_history_query(
    course_id: Optional[int],
    student_id: Optional[int],
    from_date: Optional[datetime.date],
    to_date: Optional[datetime.date],
):
    stmt = (
        select(AttendanceRecord)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .join(Course, AttendanceSession.course_id == Course.id)
        .join(Student, AttendanceRecord.student_id == Student.id)
    )
    if course_id is not None:
        stmt = stmt.where(AttendanceSession.course_id == course_id)
    if student_id is not None:
        stmt = stmt.where(AttendanceRecord.student_id == student_id)
    if from_date is not None:
        stmt = stmt.where(AttendanceSession.session_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(AttendanceSession.session_date <= to_date)

    stmt = stmt.order_by(
        AttendanceSession.session_date.desc(),
        AttendanceSession.period.desc(),
        Student.roll_no.asc(),
    )
    return stmt


@router.get("", response_model=list[AttendanceRowOut])
def get_attendance_history(
    course_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    from_date: Optional[datetime.date] = Query(None, alias="from"),
    to_date: Optional[datetime.date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    stmt = _build_history_query(course_id, student_id, from_date, to_date)
    records = db.scalars(stmt).all()

    rows = []
    for r in records:
        rows.append(
            AttendanceRowOut(
                session_id=r.session_id,
                session_date=r.session.session_date,
                period=r.session.period,
                course_code=r.session.course.code,
                roll_no=r.student.roll_no,
                full_name=r.student.full_name,
                status=r.status,
                marked_by=r.marked_by,
            )
        )
    return rows


@router.get("/summary", response_model=list[AttendanceSummaryOut])
def get_attendance_summary(
    course_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    from_date: Optional[datetime.date] = Query(None, alias="from"),
    to_date: Optional[datetime.date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    stmt = _build_history_query(course_id, student_id, from_date, to_date)
    records = db.scalars(stmt).all()

    student_stats: dict[str, dict] = {}
    for r in records:
        roll = r.student.roll_no
        if roll not in student_stats:
            student_stats[roll] = {
                "roll_no": roll,
                "full_name": r.student.full_name,
                "sessions": 0,
                "present": 0,
                "absent": 0,
            }
        student_stats[roll]["sessions"] += 1
        if r.status == "present":
            student_stats[roll]["present"] += 1
        elif r.status in ("absent", "needs_review"):
            student_stats[roll]["absent"] += 1

    summaries = []
    for roll, stat in sorted(student_stats.items()):
        total = stat["sessions"]
        present = stat["present"]
        pct = (present / total * 100.0) if total > 0 else 0.0
        summaries.append(
            AttendanceSummaryOut(
                roll_no=stat["roll_no"],
                full_name=stat["full_name"],
                sessions=total,
                present=present,
                absent=stat["absent"],
                percent=round(pct, 1),
            )
        )
    return summaries


@router.get("/export.csv")
def export_attendance_history_csv(
    course_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    from_date: Optional[datetime.date] = Query(None, alias="from"),
    to_date: Optional[datetime.date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    stmt = _build_history_query(course_id, student_id, from_date, to_date)
    records = db.scalars(stmt).all()

    rows = []
    for r in records:
        rows.append(
            {
                "session_date": r.session.session_date,
                "period": r.session.period,
                "course_code": r.session.course.code,
                "roll_no": r.student.roll_no,
                "full_name": r.student.full_name,
                "status": r.status,
                "similarity": r.similarity,
                "marked_by": r.marked_by,
            }
        )

    csv_bytes = generate_csv(rows)
    filename = "attendance_history.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
