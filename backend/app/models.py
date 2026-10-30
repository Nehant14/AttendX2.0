"""Database tables: students, their face embeddings, attendance sessions and records."""
import datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db import Base


def _now() -> datetime.datetime:
    return datetime.datetime.now()


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    roll_no = Column(String, unique=True, nullable=False, index=True)  # also the student's login
    full_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=_now)

    embeddings = relationship("StudentEmbedding", back_populates="student", cascade="all, delete-orphan")
    records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")


class StudentEmbedding(Base):
    """One row per enrolled photo: (k, 512) float32 bytes - row 0 is the photo, the rest are low-res copies."""
    __tablename__ = "student_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = Column(LargeBinary, nullable=False)
    image_path = Column(Text, nullable=False)  # relative to DATA_DIR, e.g. enrollment/3/abc.jpg

    student = relationship("Student", back_populates="embeddings")


class AttendanceSession(Base):
    """One class (one or more class photos)."""
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=_now, nullable=False)
    images = Column(Text, nullable=False, default="[]")  # JSON list of annotated photos, relative to DATA_DIR

    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False)  # "present" | "absent"
    similarity = Column(Float, nullable=True)  # cosine similarity of the matched face (None if no match)

    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student", back_populates="records")
