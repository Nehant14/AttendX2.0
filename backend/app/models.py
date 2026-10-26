"""SQLAlchemy ORM models (tables)."""
import datetime
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Integer, LargeBinary, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db import Base


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String, nullable=False, default="teacher")  # admin | teacher
    created_at = Column(DateTime, default=_now)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    roll_no = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    consent_recorded = Column(Boolean, default=False, nullable=False)
    consent_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=_now)

    embeddings = relationship(
        "StudentEmbedding", back_populates="student", cascade="all, delete-orphan"
    )
    course_enrollments = relationship(
        "CourseEnrollment", back_populates="student", cascade="all, delete-orphan"
    )
    attendance_records = relationship(
        "AttendanceRecord", back_populates="student", cascade="all, delete-orphan"
    )


class StudentEmbedding(Base):
    __tablename__ = "student_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = Column(LargeBinary, nullable=False)  # 512 float32 = 2048 bytes
    source_image_path = Column(Text, nullable=True)
    det_score = Column(Float, nullable=True)
    face_px = Column(Integer, nullable=True)
    blur_var = Column(Float, nullable=True)
    model_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)

    student = relationship("Student", back_populates="embeddings")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=_now)

    enrollments = relationship(
        "CourseEnrollment", back_populates="course", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "AttendanceSession", back_populates="course", cascade="all, delete-orphan"
    )


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)

    course = relationship("Course", back_populates="enrollments")
    student = relationship("Student", back_populates="course_enrollments")


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    session_date = Column(Date, nullable=False)
    period = Column(Integer, default=1, nullable=False)
    source_image_path = Column(Text, nullable=True)
    annotated_image_path = Column(Text, nullable=True)
    detector_version = Column(String, nullable=True)
    embedder_version = Column(String, nullable=True)
    faces_detected = Column(Integer, default=0)
    faces_unrecognizable = Column(Integer, default=0)
    faces_unknown = Column(Integer, default=0)
    status = Column(String, nullable=False, default="done")  # done | needs_review | failed
    error_message = Column(Text, nullable=True)
    processing_ms = Column(Integer, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=_now)

    __table_args__ = (UniqueConstraint("course_id", "session_date", "period"),)

    course = relationship("Course", back_populates="sessions")
    records = relationship(
        "AttendanceRecord", back_populates="session", cascade="all, delete-orphan"
    )
    detections = relationship(
        "Detection", back_populates="session", cascade="all, delete-orphan"
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False)  # present | absent | needs_review
    similarity = Column(Float, nullable=True)
    margin = Column(Float, nullable=True)
    bbox_json = Column(Text, nullable=True)   # "[x1,y1,x2,y2]"
    marked_by = Column(String, default="auto", nullable=False)  # auto | teacher
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (UniqueConstraint("session_id", "student_id"),)

    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student", back_populates="attendance_records")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    bbox_json = Column(Text, nullable=True)
    det_score = Column(Float, nullable=True)
    face_px = Column(Integer, nullable=True)
    label = Column(String, nullable=True)  # recognized | review | unknown | unrecognizable
    matched_student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    similarity = Column(Float, nullable=True)

    session = relationship("AttendanceSession", back_populates="detections")
