"""Course endpoints: CRUD and roster assignment."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import duplicate, not_found, validation_error
from app.models import Course, CourseEnrollment, Student
from app.schemas import CourseCreate, CourseDetailOut, CourseOut, RosterUpdate
from app.security import get_current_user
from app.services.serializers import student_out

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _course_out(course: Course) -> CourseOut:
    return CourseOut(
        id=course.id, code=course.code, name=course.name,
        student_count=len(course.enrollments),
    )


def _course_detail(course: Course) -> CourseDetailOut:
    students = sorted(
        (e.student for e in course.enrollments if e.student is not None),
        key=lambda s: s.roll_no,
    )
    return CourseDetailOut(
        id=course.id, code=course.code, name=course.name,
        student_count=len(students),
        students=[student_out(s) for s in students],
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CourseOut)
def create_course(
    body: CourseCreate,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    if db.scalar(select(Course).where(Course.code == body.code)):
        raise duplicate(f"Course code '{body.code}' already exists.")
    course = Course(code=body.code, name=body.name)
    db.add(course)
    db.flush()
    return _course_out(course)


@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db), _auth=Depends(get_current_user)):
    return [_course_out(c) for c in db.scalars(select(Course).order_by(Course.code)).all()]


@router.get("/{course_id}", response_model=CourseDetailOut)
def get_course(course_id: int, db: Session = Depends(get_db), _auth=Depends(get_current_user)):
    course = db.get(Course, course_id)
    if course is None:
        raise not_found("Course")
    return _course_detail(course)


@router.put("/{course_id}/students", response_model=CourseDetailOut)
def update_course_roster(
    course_id: int,
    body: RosterUpdate,
    db: Session = Depends(get_db),
    _auth=Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if course is None:
        raise not_found("Course")

    wanted = list(dict.fromkeys(body.student_ids))
    found = set(db.scalars(select(Student.id).where(Student.id.in_(wanted))).all()) if wanted else set()
    missing = [i for i in wanted if i not in found]
    if missing:
        raise validation_error(f"Unknown student id(s): {missing}")

    # Replace the roster with a bulk delete + inserts, then expire the relationship so the
    # response reflects the new rows (a stale collection was returning an empty roster).
    db.execute(delete(CourseEnrollment).where(CourseEnrollment.course_id == course_id))
    for sid in wanted:
        db.add(CourseEnrollment(course_id=course_id, student_id=sid))
    db.flush()
    db.expire(course, ["enrollments"])
    return _course_detail(course)
