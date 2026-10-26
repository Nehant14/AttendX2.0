"""Shared ORM -> schema conversion helpers."""
from __future__ import annotations

from app.config import settings
from app.models import Student
from app.schemas import StudentOut


def student_out(s: Student) -> StudentOut:
    """Build a StudentOut including the embedding count and ready flag."""
    count = len(s.embeddings)
    return StudentOut(
        id=s.id, roll_no=s.roll_no, full_name=s.full_name, email=s.email,
        is_active=s.is_active, consent_recorded=s.consent_recorded,
        consent_date=s.consent_date,
        embedding_count=count, ready=count >= settings.ENROLL_MIN_PHOTOS,
    )
